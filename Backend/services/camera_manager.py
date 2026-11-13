import logging
import threading
import time

import cv2
from ultralytics import YOLO

from database.db import get_db_connection

logger = logging.getLogger(__name__)


class CameraManager:
    """
    Phone-usage prototype for a side-mounted classroom camera.

    It detects a phone and a person's pose. A possible usage event is counted
    when a phone is close to one of that person's wrists and the wrist is below
    the corresponding shoulder for several consecutive frames.

    This is a heuristic, not a guaranteed phone-use classifier. A phone fully
    hidden behind a desk cannot be detected by a single camera.
    """

    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.camera = None
        self.model = None
        self.pose_model = None
        self.thread = None

        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.running = False
        self.is_running = False
        self.classroom_id = None
        self.error = None

        self.latest_frame = None
        self.frame_number = 0
        self.phone_count = 0
        self.qualifying_frames = 0

        # Tuning values. Adjust after testing on actual classroom videos.
        self.required_frames = 8
        self.no_usage_frames = 20
        self.no_usage_counter = 0
        self.phone_confidence = 0.20
        self.pose_confidence = 0.35
        self.hand_distance_ratio = 0.12
        self.event_saved_for_episode = False

        self.last_debug = {
            "phones": 0,
            "people": 0,
            "qualifying": 0,
            "reason": "CAMERA_NOT_STARTED",
            "saved": False,
        }

    def start(self, classroom_id=None):
        """Load models and start the camera worker."""
        with self.lock:
            if self.running:
                if classroom_id is not None:
                    self.classroom_id = classroom_id
                return {"success": True, "message": "Camera is already running"}

            if self.thread is not None and self.thread.is_alive():
                return {
                    "success": False,
                    "message": "Camera is still stopping. Wait a few seconds and retry.",
                }

            try:
                self.error = None
                if classroom_id is not None:
                    self.classroom_id = classroom_id

                logger.info("Loading YOLO11n object model...")
                self.model = YOLO("yolo11n.pt")

                logger.info("Loading YOLO11n pose model...")
                # First run may download this official Ultralytics weight.
                self.pose_model = YOLO("yolo11n-pose.pt")

                self.camera = cv2.VideoCapture(self.camera_index)
                if not self.camera.isOpened():
                    self.camera.release()
                    self.camera = None
                    raise RuntimeError(
                        "Camera could not be opened. Close other camera apps "
                        "and check Windows camera permissions."
                    )

                # Lower resolution to reduce CPU/RAM load on an 8 GB laptop.
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                self.stop_event.clear()
                self.latest_frame = None
                self.frame_number = 0
                self.phone_count = 0
                self.qualifying_frames = 0
                self.no_usage_counter = 0
                self.event_saved_for_episode = False
                self.last_debug = {}

                self.running = True
                self.is_running = True
                self.thread = threading.Thread(
                    target=self._camera_loop, daemon=True
                )
                self.thread.start()

                logger.info("Phone usage monitoring started: classroom_id=%s",
                            self.classroom_id)
                return {
                    "success": True,
                    "message": "Phone usage monitoring started successfully",
                }

            except Exception as exc:
                self.error = str(exc)
                self.running = False
                self.is_running = False
                logger.exception("Camera start failed")
                self._release_camera()
                return {"success": False, "message": self.error}

    def stop(self):
        """Stop worker and release camera."""
        with self.lock:
            self.running = False
            self.is_running = False
            self.stop_event.set()
            worker = self.thread
            camera = self.camera
            self.camera = None

        if camera is not None:
            try:
                camera.release()
            except Exception:
                logger.exception("Could not release camera during stop")

        if worker is not None and worker is not threading.current_thread():
            try:
                if worker.is_alive():
                    worker.join(timeout=10.0)
            except RuntimeError:
                logger.exception("Could not wait for camera worker")

        still_running = (
            worker is not None
            and worker is not threading.current_thread()
            and worker.is_alive()
        )

        with self.lock:
            self.qualifying_frames = 0
            self.no_usage_counter = 0
            self.event_saved_for_episode = False
            self.latest_frame = None
            if not still_running:
                self.thread = None

        if still_running:
            self.error = (
                "Stop requested, but camera worker is still finishing. "
                "Wait a few seconds and check status again."
            )
            return {"success": False, "message": self.error}

        self.error = None
        logger.info("Camera stopped successfully")
        return {"success": True, "message": "Camera stopped successfully"}

    def status(self):
        return {
            "running": self.running,
            "is_running": self.running,
            "classroom_id": self.classroom_id,
            "phones": self.phone_count,
            "qualifying_frames": self.qualifying_frames,
            "error": self.error,
            "debug": dict(self.last_debug),
        }

    def get_jpeg_frame(self):
        with self.lock:
            if self.latest_frame is None:
                return None
            ok, buffer = cv2.imencode(
                ".jpg", self.latest_frame,
                [int(cv2.IMWRITE_JPEG_QUALITY), 80]
            )
            return buffer.tobytes() if ok else None

    def _camera_loop(self):
        camera = self.camera
        try:
            while self.running and not self.stop_event.is_set():
                if camera is None or not camera.isOpened():
                    if not self.stop_event.is_set():
                        self.error = "Camera is not available"
                    break

                ok, frame = camera.read()
                if self.stop_event.is_set() or not self.running:
                    break
                if not ok or frame is None:
                    time.sleep(0.1)
                    continue

                self.frame_number += 1
                try:
                    annotated, info = self._process_frame(frame)
                    self.phone_count = info["phones"]
                    self.last_debug = info
                    if self.running and not self.stop_event.is_set():
                        self.error = None
                        with self.lock:
                            self.latest_frame = annotated
                except Exception as exc:
                    if not self.stop_event.is_set():
                        self.error = str(exc)
                        logger.exception("Phone usage detection failed")

                if self.stop_event.wait(0.01):
                    break

        except Exception:
            if not self.stop_event.is_set():
                logger.exception("Camera loop crashed")
        finally:
            try:
                if camera is not None:
                    camera.release()
            except Exception:
                logger.exception("Could not release worker camera")

            with self.lock:
                if self.camera is camera:
                    self.camera = None
                self.running = False
                self.is_running = False
                if self.thread is threading.current_thread():
                    self.thread = None
            logger.info("Camera worker exited")

    @staticmethod
    def _center(box):
        x1, y1, x2, y2 = box
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    def _process_frame(self, frame):
        """Detect phone/person poses and verify repeated hand-phone proximity."""
        display = frame.copy()
        height, width = display.shape[:2]

        phone_boxes = []
        max_phone_confidence = 0.0

        phone_results = self.model.predict(
            source=frame,
            conf=self.phone_confidence,
            imgsz=640,
            verbose=False,
            device="cpu",
        )

        for result in phone_results:
            names = result.names
            if result.boxes is None:
                continue

            for box in result.boxes:
                class_id = int(box.cls[0].item())
                label = str(names[class_id]).lower().strip()
                normalized = label.replace("_", " ").replace("-", " ")
                if "phone" not in normalized.replace(" ", ""):
                    continue

                confidence = float(box.conf[0].item())
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                x1 = max(0, min(x1, width - 1))
                x2 = max(0, min(x2, width - 1))
                y1 = max(0, min(y1, height - 1))
                y2 = max(0, min(y2, height - 1))
                if x2 <= x1 or y2 <= y1:
                    continue

                phone_boxes.append((x1, y1, x2, y2, confidence))
                max_phone_confidence = max(max_phone_confidence, confidence)
                cv2.rectangle(display, (x1, y1), (x2, y2), (0, 200, 255), 2)
                cv2.putText(
                    display, f"PHONE {confidence:.2f}",
                    (x1, max(20, y1 - 7)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 2
                )

        pose_results = self.pose_model.predict(
            source=frame,
            conf=self.pose_confidence,
            imgsz=640,
            verbose=False,
            device="cpu",
        )

        people = []
        usage_match = False
        match_details = []

        for result in pose_results:
            if result.boxes is None or result.keypoints is None:
                continue

            keypoints = result.keypoints.xy.cpu().numpy()
            person_boxes = result.boxes.xyxy.cpu().numpy()

            for person_index, person_box in enumerate(person_boxes):
                px1, py1, px2, py2 = map(int, person_box.tolist())
                people.append((px1, py1, px2, py2))
                cv2.rectangle(display, (px1, py1), (px2, py2), (255, 180, 0), 1)

                points = keypoints[person_index]
                if len(points) < 11:
                    continue

                # COCO pose indices: shoulders 5/6; wrists 9/10.
                for wrist_index, wrist_index_in_pose in enumerate((9, 10)):
                    wrist = points[wrist_index_in_pose]
                    shoulder = points[5 + wrist_index]

                    wx, wy = float(wrist[0]), float(wrist[1])
                    sx, sy = float(shoulder[0]), float(shoulder[1])

                    if (wx <= 0 and wy <= 0) or (sx <= 0 and sy <= 0):
                        continue

                    person_height = max(1.0, float(py2 - py1))
                    wrist_below_shoulder = wy > sy + (0.04 * person_height)
                    cv2.circle(display, (int(wx), int(wy)), 4, (255, 0, 255), -1)

                    body_width = max(1.0, float(px2 - px1))
                    wrist_near_body = (
                        px1 - 0.15 * body_width <= wx <= px2 + 0.15 * body_width
                    )

                    for phone in phone_boxes:
                        fx1, fy1, fx2, fy2, phone_conf = phone
                        phone_cx, phone_cy = self._center((fx1, fy1, fx2, fy2))

                        diagonal = max(1.0, (width ** 2 + height ** 2) ** 0.5)
                        distance = (
                            ((wx - phone_cx) ** 2 + (wy - phone_cy) ** 2) ** 0.5
                        ) / diagonal

                        phone_near_person = (
                            px1 - 0.20 * body_width <= phone_cx
                            <= px2 + 0.20 * body_width
                        )

                        if (
                            distance <= self.hand_distance_ratio
                            and wrist_below_shoulder
                            and wrist_near_body
                            and phone_near_person
                        ):
                            usage_match = True
                            match_details.append({
                                "distance": round(distance, 3),
                                "phone_confidence": round(phone_conf, 3),
                            })
                            cv2.line(
                                display, (int(wx), int(wy)),
                                (int(phone_cx), int(phone_cy)), (0, 255, 0), 2
                            )

        if usage_match:
            self.qualifying_frames += 1
            self.no_usage_counter = 0
            reason = "PHONE_HAND_INTERACTION"
        else:
            self.qualifying_frames = 0
            self.no_usage_counter += 1
            reason = (
                "PHONE_VISIBLE_BUT_NO_USAGE_EVIDENCE"
                if phone_boxes else "NO_PHONE"
            )
            if self.no_usage_counter >= self.no_usage_frames:
                self.event_saved_for_episode = False

        saved_now = False
        if (
            self.qualifying_frames >= self.required_frames
            and not self.event_saved_for_episode
        ):
            if self._save_detection(max_phone_confidence):
                self.event_saved_for_episode = True
                saved_now = True
                logger.info("PHONE USAGE EVENT SAVED")

        info = {
            "frame": self.frame_number,
            "phones": len(phone_boxes),
            "people": len(people),
            "qualifying": self.qualifying_frames,
            "required_frames": self.required_frames,
            "reason": reason,
            "saved": self.event_saved_for_episode,
            "saved_now": saved_now,
            "confidence": max_phone_confidence,
            "usage_match": usage_match,
            "matches": match_details[:5],
        }
        self.last_debug = info

        if usage_match:
            status_text = (
                f"PHONE USE CHECK {self.qualifying_frames}/{self.required_frames}"
            )
            status_color = (0, 255, 0)
        elif phone_boxes:
            status_text = "PHONE VISIBLE - USE NOT CONFIRMED"
            status_color = (0, 200, 255)
        else:
            status_text = "NO PHONE"
            status_color = (255, 255, 255)

        cv2.putText(
            display, status_text, (12, 28),
            cv2.FONT_HERSHEY_SIMPLEX, 0.55, status_color, 2
        )
        cv2.putText(
            display, f"Phones: {len(phone_boxes)}  Students/people: {len(people)}",
            (12, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1
        )
        return display, info

    def _save_detection(self, confidence):
        """Save a confirmed phone-use event using the existing DB schema."""
        if self.classroom_id is None:
            logger.error("Detection not saved: classroom_id is missing")
            return False

        connection = None
        cursor = None
        try:
            connection = get_db_connection()
            if connection is None:
                raise RuntimeError("get_db_connection() returned None")

            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO detections
                    (classroom_id, object_name, confidence, detected_at, snapshot_path)
                VALUES (%s, %s, %s, NOW(), NULL)
                """,
                (
                    self.classroom_id,
                    "phone usage",
                    float(max(0.0, min(confidence, 1.0))),
                ),
            )
            connection.commit()
            logger.info(
                "PHONE USAGE INSERT SUCCESS: classroom_id=%s confidence=%.2f",
                self.classroom_id, confidence
            )
            return True

        except Exception as exc:
            self.error = f"Database insert failed: {exc}"
            logger.exception("Could not save phone usage event")
            if connection is not None:
                try:
                    connection.rollback()
                except Exception:
                    logger.exception("Database rollback failed")
            return False

        finally:
            if cursor is not None:
                try:
                    cursor.close()
                except Exception:
                    pass
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass

    def _release_camera(self):
        with self.lock:
            camera = self.camera
            self.camera = None
        if camera is not None:
            try:
                camera.release()
            except Exception:
                logger.exception("Could not release camera")


# Keep the same singleton import used by your existing Flask routes.
camera_manager = CameraManager()
