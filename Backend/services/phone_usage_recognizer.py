
from pathlib import Path
import cv2
import numpy as np
from ultralytics import YOLO


class PhoneUsageRecognizer:
    """
    Prototype phone-use recognizer.

    Uses:
      - YOLO object detector for cell phones
      - YOLO pose model for person wrist keypoints

    A possible phone-use event is reported when a phone is
    sufficiently close to a detected person's wrist for
    consecutive frames.

    This is a proximity heuristic, not a trained behaviour classifier.
    """

    PHONE_CLASS_NAMES = {"cell phone", "mobile phone", "phone"}

    # COCO human pose keypoint indices
    LEFT_WRIST = 9
    RIGHT_WRIST = 10

    def __init__(
        self,
        phone_model_path=None,
        pose_model_path=None,
        phone_confidence=0.25,
        pose_confidence=0.30,
        wrist_distance_ratio=0.18,
        required_frames=5,
        image_size=416,
    ):
        backend_dir = Path(__file__).resolve().parents[1]

        self.phone_model_path = Path(
            phone_model_path or backend_dir / "yolo11n.pt"
        )
        self.pose_model_path = Path(
            pose_model_path or backend_dir / "yolo11n-pose.pt"
        )

        if not self.phone_model_path.exists():
            raise FileNotFoundError(
                f"Phone model not found: {self.phone_model_path}"
            )

        if not self.pose_model_path.exists():
            raise FileNotFoundError(
                f"Pose model not found: {self.pose_model_path}"
            )

        self.phone_model = YOLO(str(self.phone_model_path))
        self.pose_model = YOLO(str(self.pose_model_path))

        self.phone_confidence = phone_confidence
        self.pose_confidence = pose_confidence
        self.wrist_distance_ratio = wrist_distance_ratio
        self.required_frames = required_frames
        self.image_size = image_size

        self.usage_streak = 0

    def reset(self):
        """Reset consecutive-frame tracking."""
        self.usage_streak = 0

    def _get_phone_class_id(self):
        names = self.phone_model.names

        for class_id, name in names.items():
            if str(name).lower() in self.PHONE_CLASS_NAMES:
                return int(class_id)

        raise ValueError(
            "Cell phone class was not found in the object model."
        )

    @staticmethod
    def _distance(point_a, point_b):
        return float(
            np.sqrt(
                (point_a[0] - point_b[0]) ** 2
                + (point_a[1] - point_b[1]) ** 2
            )
        )

    def _get_phone_boxes(self, frame):
        result = self.phone_model.predict(
            source=frame,
            conf=self.phone_confidence,
            imgsz=self.image_size,
            verbose=False,
            device="cpu",
        )[0]

        phone_class_id = self._get_phone_class_id()
        phones = []

        if result.boxes is None:
            return phones

        for box in result.boxes:
            class_id = int(box.cls[0].item())

            if class_id != phone_class_id:
                continue

            x1, y1, x2, y2 = map(
                int, box.xyxy[0].tolist()
            )

            confidence = float(box.conf[0].item())

            phones.append({
                "box": (x1, y1, x2, y2),
                "center": (
                    (x1 + x2) / 2,
                    (y1 + y2) / 2,
                ),
                "confidence": confidence,
            })

        return phones

    def _get_person_wrists(self, frame):
        result = self.pose_model.predict(
            source=frame,
            conf=self.pose_confidence,
            imgsz=self.image_size,
            verbose=False,
            device="cpu",
        )[0]

        people = []

        if result.keypoints is None or result.boxes is None:
            return people

        keypoints = result.keypoints.data.cpu().numpy()
        person_boxes = result.boxes.xyxy.cpu().numpy()

        for index, points in enumerate(keypoints):
            person_x1, person_y1, person_x2, person_y2 = (
                person_boxes[index]
            )

            person_width = max(1.0, person_x2 - person_x1)
            person_height = max(1.0, person_y2 - person_y1)

            wrists = []

            for wrist_index in (
                self.LEFT_WRIST,
                self.RIGHT_WRIST,
            ):
                if wrist_index >= len(points):
                    continue

                x, y, confidence = points[wrist_index]

                if confidence < 0.25:
                    continue

                if x <= 0 or y <= 0:
                    continue

                wrists.append((float(x), float(y)))

            people.append({
                "box": (
                    int(person_x1),
                    int(person_y1),
                    int(person_x2),
                    int(person_y2),
                ),
                "wrists": wrists,
                "scale": float(
                    np.sqrt(person_width ** 2 + person_height ** 2)
                ),
            })

        return people

    def process_frame(self, frame):
        """
        Process one webcam frame.

        Returns:
            {
                "frame": annotated frame,
                "status": status string,
                "possible_phone_use": bool,
                "phone_count": int,
                "matched_count": int,
                "usage_streak": int
            }
        """

        if frame is None or frame.size == 0:
            raise ValueError("Invalid camera frame received.")

        annotated = frame.copy()

        phones = self._get_phone_boxes(frame)
        people = self._get_person_wrists(frame)

        matched_phones = 0

        for phone in phones:
            phone_center = phone["center"]
            phone_box = phone["box"]

            best_match = False

            for person in people:
                for wrist in person["wrists"]:
                    distance = self._distance(
                        phone_center, wrist
                    )

                    allowed_distance = (
                        person["scale"] * self.wrist_distance_ratio
                    )

                    if distance <= allowed_distance:
                        best_match = True
                        break

                if best_match:
                    break

            x1, y1, x2, y2 = phone_box

            if best_match:
                matched_phones += 1
                box_color = (0, 165, 255)
                label = "Phone near hand"
            else:
                box_color = (255, 150, 0)
                label = "Phone detected"

            cv2.rectangle(
                annotated,
                (x1, y1),
                (x2, y2),
                box_color,
                2,
            )

            cv2.putText(
                annotated,
                f"{label} {phone['confidence']:.2f}",
                (x1, max(20, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                box_color,
                2,
            )

        if matched_phones > 0:
            self.usage_streak += 1
        else:
            self.usage_streak = 0

        possible_phone_use = (
            self.usage_streak >= self.required_frames
        )

        if possible_phone_use:
            status = "POSSIBLE PHONE USE"
            status_color = (0, 0, 255)
        elif matched_phones > 0:
            status = "PHONE NEAR HAND"
            status_color = (0, 165, 255)
        elif phones:
            status = "PHONE DETECTED"
            status_color = (255, 150, 0)
        else:
            status = "NO PHONE DETECTED"
            status_color = (0, 200, 0)

        cv2.putText(
            annotated,
            status,
            (15, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            status_color,
            2,
        )

        cv2.putText(
            annotated,
            f"Phones: {len(phones)} | "
            f"Matched: {matched_phones} | "
            f"Frames: {self.usage_streak}",
            (15, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            2,
        )

        return {
            "frame": annotated,
            "status": status,
            "possible_phone_use": possible_phone_use,
            "phone_count": len(phones),
            "matched_count": matched_phones,
            "usage_streak": self.usage_streak,
        }
