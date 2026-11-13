
import logging
import threading

from ultralytics import YOLO


logger = logging.getLogger(__name__)


class InferenceEngine:
    """
    Shared YOLO inference engine.

    Loads object detection and pose models once.
    All camera workers share the same model instances.

    A single lock prevents simultaneous model inference
    from multiple camera threads.
    """

    def __init__(
        self,
        object_model_path="yolo11n.pt",
        pose_model_path="yolo11n-pose.pt",
        device="cpu",
        phone_confidence=0.20,
        pose_confidence=0.35,
        image_size=416
    ):

        self.object_model_path = object_model_path
        self.pose_model_path = pose_model_path

        self.device = device
        self.phone_confidence = phone_confidence
        self.pose_confidence = pose_confidence
        self.image_size = image_size

        self.object_model = None
        self.pose_model = None

        # One shared lock for loading and both model predictions.
        self.model_lock = threading.RLock()

        self.loaded = False

    # -----------------------------------------
    # LOAD YOLO MODELS
    # -----------------------------------------

    def load_models(self):

        with self.model_lock:

            if self.loaded:
                return True

            try:

                logger.info("Loading object detection model...")

                self.object_model = YOLO(
                    self.object_model_path
                )

                logger.info("Loading pose detection model...")

                self.pose_model = YOLO(
                    self.pose_model_path
                )

                self.loaded = True

                logger.info(
                    "Both YOLO models loaded successfully."
                )

                return True

            except Exception:

                self.object_model = None
                self.pose_model = None
                self.loaded = False

                logger.exception(
                    "YOLO model loading failed."
                )

                raise

    # -----------------------------------------
    # OBJECT DETECTION
    # -----------------------------------------

    def predict_objects(self, frame):

        with self.model_lock:

            if not self.loaded or self.object_model is None:
                raise RuntimeError(
                    "Object detection model is not loaded."
                )

            results = self.object_model.predict(
                source=frame,
                conf=self.phone_confidence,
                imgsz=self.image_size,
                device=self.device,
                verbose=False
            )

            return results

    # -----------------------------------------
    # POSE DETECTION
    # -----------------------------------------

    def predict_pose(self, frame):

        with self.model_lock:

            if not self.loaded or self.pose_model is None:
                raise RuntimeError(
                    "Pose detection model is not loaded."
                )

            results = self.pose_model.predict(
                source=frame,
                conf=self.pose_confidence,
                imgsz=self.image_size,
                device=self.device,
                verbose=False
            )

            return results

    # -----------------------------------------
    # CHECK MODEL STATUS
    # -----------------------------------------

    def is_loaded(self):

        with self.model_lock:

            return (
                self.loaded
                and self.object_model is not None
                and self.pose_model is not None
            )

    # -----------------------------------------
    # GET MODEL INFORMATION
    # -----------------------------------------

    def get_status(self):

        with self.model_lock:

            return {
                "loaded": (
                    self.loaded
                    and self.object_model is not None
                    and self.pose_model is not None
                ),
                "object_model": self.object_model_path,
                "pose_model": self.pose_model_path,
                "device": self.device,
                "image_size": self.image_size,
                "phone_confidence": self.phone_confidence,
                "pose_confidence": self.pose_confidence
            }
