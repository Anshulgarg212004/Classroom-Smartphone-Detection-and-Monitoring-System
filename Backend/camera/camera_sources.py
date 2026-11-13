
import logging
import cv2

logger = logging.getLogger(__name__)


class CameraSource:

    def __init__(
        self,
        camera_id,
        classroom_id,
        name="Laptop Webcam",
        source_type="webcam",
        source=0
    ):
        self.camera_id = str(camera_id)
        self.classroom_id = classroom_id
        self.name = name
        self.source_type = "webcam"
        self.source = 0

        self.validate()

    def validate(self):
        if self.source != 0:
            raise ValueError("Only laptop webcam (Camera 0) is supported.")

        if self.source_type != "webcam":
            raise ValueError("Only laptop webcam is supported.")

        return True

    def get_opencv_source(self):
        return 0

    def get_camera_info(self):
        return {
            "camera_id": self.camera_id,
            "classroom_id": self.classroom_id,
            "name": self.name,
            "source_type": "webcam"
        }


def create_camera_capture(camera_source):

    logger.info("Opening laptop webcam (Camera 0)...")

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    if not cap.isOpened():
        cap.release()
        logger.warning("DirectShow failed. Trying default backend.")
        cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        cap.release()
        raise RuntimeError("Unable to open laptop webcam (Camera 0).")

    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    logger.info("Laptop webcam connected successfully.")

    return cap
