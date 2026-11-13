
import cv2
import logging
import threading
import time

from camera.camera_sources import create_camera_capture


logger = logging.getLogger(__name__)


class CameraWorker:

    def __init__(
        self,
        camera_source,
        inference_engine,
        event_callback=None,
        camera_fps=3,
        required_frames=8,
        no_usage_frames=20,
        hand_distance_ratio=0.12
    ):

        self.camera_source = camera_source
        self.inference_engine = inference_engine
        self.event_callback = event_callback

        self.camera_fps = max(1, camera_fps)
        self.required_frames = required_frames
        self.no_usage_frames = no_usage_frames
        self.hand_distance_ratio = hand_distance_ratio

        self.camera = None
        self.thread = None

        self.lock = threading.RLock()
        self.stop_event = threading.Event()

        self.running = False
        self.error = None

        self.latest_frame = None
        self.frame_number = 0

        self.phone_count = 0
        self.people_count = 0

        self.qualifying_frames = 0
        self.no_usage_counter = 0

        self.event_saved_for_episode = False
        self.last_debug = {}

    # -----------------------------------------
    # START CAMERA
    # -----------------------------------------

    def start(self):

        with self.lock:

            if self.running:
                return {
                    "success": True,
                    "message": "Camera already running"
                }

            if self.thread and self.thread.is_alive():
                return {
                    "success": False,
                    "message": "Previous camera worker is still stopping"
                }

            if not self.inference_engine.is_loaded():
                return {
                    "success": False,
                    "message": "YOLO models are not loaded"
                }

            try:

                self.camera = create_camera_capture(
                    self.camera_source
                )

                self.camera.set(
                    cv2.CAP_PROP_FRAME_WIDTH,
                    640
                )

                self.camera.set(
                    cv2.CAP_PROP_FRAME_HEIGHT,
                    480
                )

                self.stop_event.clear()

                self.running = True
                self.error = None

                self.frame_number = 0

                self.phone_count = 0
                self.people_count = 0

                self.qualifying_frames = 0
                self.no_usage_counter = 0

                self.event_saved_for_episode = False

                self.latest_frame = None
                self.last_debug = {}

                self.thread = threading.Thread(
                    target=self._camera_loop,
                    daemon=True,
                    name=f"Camera-{self.camera_source.camera_id}"
                )

                self.thread.start()

                logger.info(
                    "Camera started: %s",
                    self.camera_source.camera_id
                )

                return {
                    "success": True,
                    "message": "Camera started successfully"
                }

            except Exception as exc:

                self.running = False
                self.error = str(exc)

                if self.camera is not None:
                    self.camera.release()
                    self.camera = None

                logger.exception(
                    "Camera start failed: %s",
                    self.camera_source.camera_id
                )

                return {
                    "success": False,
                    "message": self.error
                }

    # -----------------------------------------
    # STOP CAMERA
    # -----------------------------------------

    def stop(self):

        with self.lock:

            self.running = False
            self.stop_event.set()

            worker = self.thread
            camera = self.camera

            self.camera = None

        # Release camera to interrupt a blocked read where possible.
        if camera is not None:

            try:
                camera.release()

            except Exception:
                logger.exception("Camera release failed")

        # Wait for worker thread to exit.
        if (
            worker is not None
            and worker is not threading.current_thread()
        ):

            worker.join(timeout=10)

        still_running = (
            worker is not None
            and worker.is_alive()
        )

        with self.lock:

            if not still_running:

                self.thread = None
                self.latest_frame = None

                self.qualifying_frames = 0
                self.no_usage_counter = 0

                self.event_saved_for_episode = False

                self.error = None

        if still_running:

            with self.lock:
                self.error = "Camera worker is still stopping"

            return {
                "success": False,
                "message": "Camera worker is still stopping"
            }

        logger.info(
            "Camera stopped: %s",
            self.camera_source.camera_id
        )

        return {
            "success": True,
            "message": "Camera stopped successfully"
        }

    # -----------------------------------------
    # CAMERA STATUS
    # -----------------------------------------

    def status(self):

        with self.lock:

            return {
                **self.camera_source.get_camera_info(),

                "running": self.running,

                "phones": self.phone_count,

                "people": self.people_count,

                "qualifying_frames": self.qualifying_frames,

                "error": self.error,

                "debug": dict(self.last_debug)
            }

    # -----------------------------------------
    # GET LATEST JPEG FRAME
    # -----------------------------------------

    def get_jpeg_frame(self):

        with self.lock:

            if self.latest_frame is None:
                return None

            success, buffer = cv2.imencode(
                ".jpg",
                self.latest_frame,
                [
                    int(cv2.IMWRITE_JPEG_QUALITY),
                    75
                ]
            )

            if not success:
                return None

            return buffer.tobytes()

    # -----------------------------------------
    # CAMERA PROCESSING THREAD
    # -----------------------------------------

    def _camera_loop(self):

        with self.lock:
            camera = self.camera

        frame_interval = 1.0 / self.camera_fps

        consecutive_read_failures = 0
        max_read_failures = 30

        try:

            while not self.stop_event.is_set():

                with self.lock:

                    if not self.running:
                        break

                started = time.monotonic()

                if camera is None or not camera.isOpened():

                    if not self.stop_event.is_set():
                        raise RuntimeError(
                            "Camera disconnected"
                        )

                    break

                success, frame = camera.read()

                if self.stop_event.is_set():
                    break

                if not success or frame is None:

                    consecutive_read_failures += 1

                    if consecutive_read_failures >= max_read_failures:

                        raise RuntimeError(
                            "Camera is not providing frames"
                        )

                    self.stop_event.wait(0.1)
                    continue

                consecutive_read_failures = 0

                self.frame_number += 1

                try:

                    annotated, info = self._process_frame(frame)

                    with self.lock:

                        self.phone_count = info["phones"]
                        self.people_count = info["people"]

                        self.qualifying_frames = info["qualifying"]

                        self.last_debug = info

                        if (
                            self.running
                            and not self.stop_event.is_set()
                        ):

                            self.latest_frame = annotated

                except Exception as exc:

                    with self.lock:
                        self.error = str(exc)

                    logger.exception(
                        "Detection error in camera %s",
                        self.camera_source.camera_id
                    )

                elapsed = time.monotonic() - started

                self.stop_event.wait(
                    max(0, frame_interval - elapsed)
                )

        except Exception as exc:

            if not self.stop_event.is_set():

                with self.lock:
                    self.error = str(exc)

                logger.exception(
                    "Camera worker crashed: %s",
                    self.camera_source.camera_id
                )

        finally:

            if camera is not None:

                try:
                    camera.release()

                except Exception:
                    logger.exception(
                        "Camera cleanup failed"
                    )

            with self.lock:

                if self.camera is camera:
                    self.camera = None

                self.running = False

                if self.thread is threading.current_thread():
                    self.thread = None

            logger.info(
                "Camera worker exited: %s",
                self.camera_source.camera_id
            )

    # -----------------------------------------
    # GET BOUNDING BOX CENTER
    # -----------------------------------------

    @staticmethod
    def _center(box):

        x1, y1, x2, y2 = box

        return (
            (x1 + x2) / 2,
            (y1 + y2) / 2
        )

    # -----------------------------------------
    # PROCESS FRAME
    # -----------------------------------------

    def _process_frame(self, frame):

        display = frame.copy()

        height, width = display.shape[:2]

        phone_boxes = []
        max_confidence = 0.0

        # -------------------------------------
        # PHONE DETECTION
        # -------------------------------------

        phone_results = (
            self.inference_engine.predict_objects(frame)
        )

        for result in phone_results:

            if result.boxes is None:
                continue

            for box in result.boxes:

                class_id = int(box.cls[0].item())

                label = str(
                    result.names[class_id]
                ).lower().strip()

                normalized = (
                    label.replace("_", " ")
                    .replace("-", " ")
                    .replace(" ", "")
                )

                if "phone" not in normalized:
                    continue

                confidence = float(
                    box.conf[0].item()
                )

                x1, y1, x2, y2 = map(
                    int,
                    box.xyxy[0].tolist()
                )

                x1 = max(0, min(x1, width - 1))
                x2 = max(0, min(x2, width - 1))

                y1 = max(0, min(y1, height - 1))
                y2 = max(0, min(y2, height - 1))

                if x2 <= x1 or y2 <= y1:
                    continue

                phone_boxes.append(
                    (x1, y1, x2, y2, confidence)
                )

                max_confidence = max(
                    max_confidence,
                    confidence
                )

                cv2.rectangle(
                    display,
                    (x1, y1),
                    (x2, y2),
                    (0, 200, 255),
                    2
                )

                cv2.putText(
                    display,
                    f"Phone {confidence:.2f}",
                    (x1, max(20, y1 - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 200, 255),
                    2
                )

        # -------------------------------------
        # HUMAN POSE DETECTION
        # -------------------------------------

        pose_results = (
            self.inference_engine.predict_pose(frame)
        )

        people = []
        usage_match = False

        diagonal = max(
            1.0,
            (width ** 2 + height ** 2) ** 0.5
        )

        for result in pose_results:

            if (
                result.boxes is None
                or result.keypoints is None
            ):
                continue

            keypoints = (
                result.keypoints.xy.cpu().numpy()
            )

            person_boxes = (
                result.boxes.xyxy.cpu().numpy()
            )

            for index, person_box in enumerate(person_boxes):

                px1, py1, px2, py2 = map(
                    int,
                    person_box.tolist()
                )

                people.append(person_box)

                points = keypoints[index]

                if len(points) < 11:
                    continue

                body_height = max(1, py2 - py1)
                body_width = max(1, px2 - px1)

                # COCO keypoint indices:
                # Left shoulder = 5, right shoulder = 6
                # Left wrist = 9, right wrist = 10

                for wrist_index, wrist_pose_index in enumerate(
                    (9, 10)
                ):

                    wrist = points[wrist_pose_index]

                    shoulder = points[
                        5 + wrist_index
                    ]

                    wx, wy = map(float, wrist)
                    sx, sy = map(float, shoulder)

                    # Ignore missing keypoints.
                    if (
                        (wx <= 0 and wy <= 0)
                        or (sx <= 0 and sy <= 0)
                    ):
                        continue

                    wrist_below = (
                        wy > sy + (0.04 * body_height)
                    )

                    wrist_near_body = (
                        px1 - 0.15 * body_width
                        <= wx
                        <= px2 + 0.15 * body_width
                    )

                    for phone in phone_boxes:

                        fx1, fy1, fx2, fy2, confidence = phone

                        cx, cy = self._center(
                            (fx1, fy1, fx2, fy2)
                        )

                        distance = (
                            (wx - cx) ** 2
                            + (wy - cy) ** 2
                        ) ** 0.5 / diagonal

                        phone_near_person = (
                            px1 - 0.20 * body_width
                            <= cx
                            <= px2 + 0.20 * body_width
                        )

                        if (
                            distance <= self.hand_distance_ratio
                            and wrist_below
                            and wrist_near_body
                            and phone_near_person
                        ):

                            usage_match = True

                            cv2.line(
                                display,
                                (int(wx), int(wy)),
                                (int(cx), int(cy)),
                                (0, 255, 0),
                                2
                            )

        # -------------------------------------
        # PHONE USAGE EPISODE TRACKING
        # -------------------------------------

        if usage_match:

            self.qualifying_frames += 1
            self.no_usage_counter = 0

        else:

            self.qualifying_frames = 0
            self.no_usage_counter += 1

            if self.no_usage_counter >= self.no_usage_frames:

                self.event_saved_for_episode = False

        saved_now = False

        if (
            self.qualifying_frames >= self.required_frames
            and not self.event_saved_for_episode
        ):

            saved_now = self._save_detection(
                max_confidence
            )

            if saved_now:
                self.event_saved_for_episode = True

        # -------------------------------------
        # DEBUG INFORMATION
        # -------------------------------------

        info = {

            "frame": self.frame_number,

            "phones": len(phone_boxes),

            "people": len(people),

            "qualifying": self.qualifying_frames,

            "required_frames": self.required_frames,

            "usage_match": usage_match,

            "reason": (
                "PHONE_HAND_INTERACTION"
                if usage_match
                else "PHONE_VISIBLE_BUT_USE_NOT_CONFIRMED"
                if phone_boxes
                else "NO_PHONE"
            ),

            "saved": self.event_saved_for_episode,

            "saved_now": saved_now,

            "confidence": max_confidence
        }

        # -------------------------------------
        # FRAME STATUS LABEL
        # -------------------------------------

        if usage_match:

            message = (
                f"PHONE USE "
                f"{self.qualifying_frames}/"
                f"{self.required_frames}"
            )

            color = (0, 255, 0)

        elif phone_boxes:

            message = "PHONE VISIBLE - USE NOT CONFIRMED"

            color = (0, 200, 255)

        else:

            message = "NO PHONE"

            color = (255, 255, 255)

        cv2.putText(
            display,
            message,
            (12, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2
        )

        return display, info

    # -----------------------------------------
    # SAVE DETECTION EVENT
    # -----------------------------------------

    def _save_detection(self, confidence):

        if self.event_callback is None:

            logger.error(
                "No event callback configured for camera %s",
                self.camera_source.camera_id
            )

            return False

        try:

            result = self.event_callback(
                classroom_id=self.camera_source.classroom_id,
                camera_id=self.camera_source.camera_id,
                confidence=float(confidence)
            )

            return result is not False

        except Exception:

            logger.exception(
                "Detection event callback failed: %s",
                self.camera_source.camera_id
            )

            return False
