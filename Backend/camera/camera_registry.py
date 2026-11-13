
import logging
import threading

from camera.camera_worker import CameraWorker


logger = logging.getLogger(__name__)


class CameraRegistry:
    """
    Central registry for all classroom cameras.

    Each camera has an independent worker.
    All workers share one InferenceEngine.
    """

    def __init__(
        self,
        inference_engine,
        event_callback=None
    ):

        self.inference_engine = inference_engine
        self.event_callback = event_callback

        self.cameras = {}
        self.worker_options = {}

        self.lock = threading.RLock()

    # -----------------------------------------
    # REGISTER CAMERA
    # -----------------------------------------

    def register_camera(self, camera_source, **options):

        camera_id = str(camera_source.camera_id)

        with self.lock:

            if camera_id in self.cameras:

                return {
                    "success": False,
                    "message": f"Camera already registered: {camera_id}",
                    "camera_id": camera_id
                }

            worker = CameraWorker(
                camera_source=camera_source,
                inference_engine=self.inference_engine,
                event_callback=self.event_callback,
                **options
            )

            self.cameras[camera_id] = worker
            self.worker_options[camera_id] = options

        logger.info(
            "Camera registered: %s",
            camera_id
        )

        return {
            "success": True,
            "message": "Camera registered successfully",
            "camera_id": camera_id
        }

    # -----------------------------------------
    # UNREGISTER CAMERA
    # -----------------------------------------

    def unregister_camera(self, camera_id):

        camera_id = str(camera_id)

        with self.lock:

            worker = self.cameras.get(camera_id)

            if worker is None:

                return {
                    "success": False,
                    "message": "Camera not found"
                }

            result = worker.stop()

            if not result.get("success"):
                return result

            if self.cameras.get(camera_id) is worker:

                del self.cameras[camera_id]

                self.worker_options.pop(
                    camera_id,
                    None
                )

        logger.info(
            "Camera unregistered: %s",
            camera_id
        )

        return {
            "success": True,
            "message": "Camera unregistered successfully"
        }

    # -----------------------------------------
    # START CAMERA
    # -----------------------------------------

    def start_camera(self, camera_id):

        camera_id = str(camera_id)

        with self.lock:

            worker = self.cameras.get(camera_id)

            if worker is None:

                return {
                    "success": False,
                    "message": "Camera not registered"
                }

            result = worker.start()

        return result

    # -----------------------------------------
    # STOP CAMERA
    # -----------------------------------------

    def stop_camera(self, camera_id):

        camera_id = str(camera_id)

        with self.lock:

            worker = self.cameras.get(camera_id)

            if worker is None:

                return {
                    "success": False,
                    "message": "Camera not registered"
                }

            result = worker.stop()

        return result

    # -----------------------------------------
    # START ALL CAMERAS
    # -----------------------------------------

    def start_all(self):

        with self.lock:
            camera_ids = list(self.cameras.keys())

        results = {}

        for camera_id in camera_ids:

            results[camera_id] = self.start_camera(
                camera_id
            )

        success = all(
            result.get("success", False)
            for result in results.values()
        )

        return {
            "success": success,
            "cameras": results
        }

    # -----------------------------------------
    # STOP ALL CAMERAS
    # -----------------------------------------

    def stop_all(self):

        with self.lock:
            camera_ids = list(self.cameras.keys())

        results = {}

        for camera_id in camera_ids:

            results[camera_id] = self.stop_camera(
                camera_id
            )

        success = all(
            result.get("success", False)
            for result in results.values()
        )

        return {
            "success": success,
            "cameras": results
        }

    # -----------------------------------------
    # GET ONE CAMERA STATUS
    # -----------------------------------------

    def get_camera_status(self, camera_id):

        camera_id = str(camera_id)

        with self.lock:

            worker = self.cameras.get(camera_id)

            if worker is None:
                return None

            status = worker.status()

        status["running"] = status.get("running", False)

        status["is_running"] = status["running"]

        return status

    # -----------------------------------------
    # GET ALL CAMERA STATUS
    # -----------------------------------------

    def get_all_status(self):

        with self.lock:

            workers = list(
                self.cameras.items()
            )

        statuses = {}

        for camera_id, worker in workers:

            status = worker.status()

            status["running"] = status.get(
                "running",
                False
            )

            status["is_running"] = status["running"]

            statuses[camera_id] = status

        return statuses

    # -----------------------------------------
    # GET CAMERA FRAME
    # -----------------------------------------

    def get_camera_frame(self, camera_id):

        camera_id = str(camera_id)

        with self.lock:

            worker = self.cameras.get(camera_id)

            if worker is None:
                return None

            frame = worker.get_jpeg_frame()

        if frame is None:
            return None

        # Return encoded JPEG bytes.
        return frame

    # -----------------------------------------
    # GET REGISTERED CAMERA IDS
    # -----------------------------------------

    def get_registered_cameras(self):

        with self.lock:

            return list(
                self.cameras.keys()
            )

    # -----------------------------------------
    # GET CAMERA INFORMATION
    # -----------------------------------------

    def get_camera_information(self):

        with self.lock:

            workers = list(
                self.cameras.values()
            )

        return [
            worker.camera_source.get_camera_info()
            for worker in workers
        ]

    # -----------------------------------------
    # GET RUNNING CAMERA COUNT
    # -----------------------------------------

    def get_running_count(self):

        statuses = self.get_all_status()

        return sum(
            1
            for status in statuses.values()
            if status.get("is_running", False)
        )

    # -----------------------------------------
    # GET TOTAL CAMERA COUNT
    # -----------------------------------------

    def get_total_count(self):

        with self.lock:

            return len(self.cameras)
