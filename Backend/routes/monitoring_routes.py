
import logging

from flask import Blueprint, jsonify, request, Response
from flask_jwt_extended import jwt_required

from database.db import get_db_connection

from camera.camera_sources import CameraSource
from camera.inference_engine import InferenceEngine
from camera.camera_registry import CameraRegistry


logger = logging.getLogger(__name__)

monitoring_bp = Blueprint("monitoring", __name__)


# =====================================================
# SHARED INFERENCE ENGINE
# =====================================================

inference_engine = InferenceEngine(
    object_model_path="yolo11n.pt",
    pose_model_path="yolo11n-pose.pt",
    device="cpu",
    phone_confidence=0.20,
    pose_confidence=0.35,
    image_size=416
)


# =====================================================
# SAVE PHONE USAGE EVENT IN MYSQL
# =====================================================

def save_detection(classroom_id, camera_id, confidence):

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        query = """
            INSERT INTO detections
            (
                classroom_id,
                object_name,
                confidence,
                detected_at,
                snapshot_path
            )
            VALUES (%s, %s, %s, NOW(), %s)
        """

        cursor.execute(
            query,
            (
                classroom_id,
                "phone usage",
                float(confidence),
                None
            )
        )

        connection.commit()

        logger.info(
            "Phone usage event saved | Classroom: %s | Camera: %s",
            classroom_id,
            camera_id
        )

        return True

    except Exception:
        if connection is not None:
            connection.rollback()

        logger.exception("Unable to save phone usage event")
        return False

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()


# =====================================================
# CAMERA REGISTRY
# =====================================================

camera_registry = CameraRegistry(
    inference_engine=inference_engine,
    event_callback=save_detection
)


# =====================================================
# CAMERA STATUS HELPER
# =====================================================

def get_camera_status_list():

    cameras = camera_registry.get_all_status() or {}

    # Registry returns:
    # {
    #     "camera-id": {camera status},
    #     "another-id": {camera status}
    # }

    if isinstance(cameras, dict):
        return list(cameras.values())

    if isinstance(cameras, list):
        return cameras

    return []


# =====================================================
# CHECK CLASSROOM EXISTS
# =====================================================

def classroom_exists(classroom_id):

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            "SELECT id FROM classrooms WHERE id = %s",
            (classroom_id,)
        )

        return cursor.fetchone() is not None

    except Exception:
        logger.exception("Classroom validation failed")
        return False

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()


# =====================================================
# MONITORING SUMMARY
# =====================================================

def get_monitoring_summary():

    cameras = camera_registry.get_all_status() or {}
    camera_list = get_camera_status_list()

    running_cameras = [
        camera
        for camera in camera_list
        if isinstance(camera, dict)
        and camera.get("running", camera.get("is_running", False))
    ]

    classroom_ids = list(
        dict.fromkeys(
            camera.get("classroom_id")
            for camera in running_cameras
            if camera.get("classroom_id") is not None
        )
    )

    return {
        "is_running": len(running_cameras) > 0,
        "classroom_id": (
            classroom_ids[0]
            if len(classroom_ids) == 1
            else None
        ),
        "running_count": len(running_cameras),
        "total_count": len(camera_list),
        "cameras": cameras
    }


# =====================================================
# START CAMERA MONITORING
# =====================================================

@monitoring_bp.route("/start", methods=["POST"])
@jwt_required()
def start_monitoring():

    try:
        data = request.get_json(silent=True) or {}

        cameras = data.get("cameras", [])

        # Backward compatibility for laptop webcam.

        if not cameras and data.get("classroom_id"):

            cameras = [
                {
                    "camera_id": f"webcam-{data['classroom_id']}",
                    "classroom_id": data["classroom_id"],
                    "name": "Laptop Webcam",
                    "source_type": "webcam",
                    "source": 0
                }
            ]

        if not isinstance(cameras, list) or not cameras:
            return jsonify({
                "success": False,
                "message": "At least one camera is required."
            }), 400

        # Load shared YOLO models once.

        if not inference_engine.is_loaded():

            logger.info("Loading YOLO object and pose models...")
            inference_engine.load_models()

        started = []
        failed = []

        for camera_data in cameras:

            try:
                if not isinstance(camera_data, dict):
                    raise ValueError("Invalid camera configuration.")

                camera_id = camera_data.get("camera_id")
                classroom_id = camera_data.get("classroom_id")
                name = camera_data.get("name", "Classroom Camera")
                source_type = camera_data.get("source_type")
                source = camera_data.get("source")

                if camera_id is None:
                    raise ValueError("camera_id is required.")

                if classroom_id is None:
                    raise ValueError("classroom_id is required.")

                if source_type is None:
                    raise ValueError("source_type is required.")

                if source is None:
                    raise ValueError("Camera source is required.")

                if not classroom_exists(classroom_id):
                    raise ValueError(
                        f"Classroom {classroom_id} does not exist."
                    )

                camera_source = CameraSource(
                    camera_id=camera_id,
                    classroom_id=classroom_id,
                    name=name,
                    source_type=source_type,
                    source=source
                )

                camera_source.validate()

                registration = camera_registry.register_camera(
                    camera_source
                )

                # Registry returns a result dictionary.

                if isinstance(registration, dict):
                    if not registration.get("success", False):
                        raise ValueError(
                            registration.get(
                                "message",
                                f"Camera ID {camera_id} registration failed."
                            )
                        )

                elif not registration:
                    raise ValueError(
                        f"Camera ID {camera_id} registration failed."
                    )

                success = camera_registry.start_camera(
                    str(camera_id)
                )

                if not success:
                    camera_registry.unregister_camera(
                        str(camera_id)
                    )

                    raise RuntimeError(
                        f"Unable to start camera {camera_id}."
                    )

                started.append(str(camera_id))

                logger.info("Camera started: %s", camera_id)

            except Exception as camera_error:

                logger.exception("Camera startup failed")

                failed.append({
                    "camera_id": (
                        camera_data.get("camera_id")
                        if isinstance(camera_data, dict)
                        else None
                    ),
                    "message": str(camera_error)
                })

        return jsonify({
            "success": len(started) > 0,
            "message": (
                "Camera monitoring started."
                if started
                else "No camera could be started."
            ),
            "started_cameras": started,
            "failed_cameras": failed,
            "monitoring": get_monitoring_summary()
        }), (200 if started else 400)

    except Exception:
        logger.exception("Start monitoring request failed")

        return jsonify({
            "success": False,
            "message": "Unable to start camera monitoring."
        }), 500


# =====================================================
# STOP CAMERA MONITORING
# =====================================================

@monitoring_bp.route("/stop", methods=["POST"])
@jwt_required()
def stop_monitoring():

    try:
        data = request.get_json(silent=True) or {}

        camera_id = data.get("camera_id")
        classroom_id = data.get("classroom_id")

        stopped = []

        if camera_id is not None:

            success = camera_registry.stop_camera(
                str(camera_id)
            )

            if success:
                stopped.append(str(camera_id))

        elif classroom_id is not None:

            cameras = get_camera_status_list()

            for camera in cameras:

                if not isinstance(camera, dict):
                    continue

                if str(camera.get("classroom_id")) == str(classroom_id):

                    current_id = camera.get("camera_id")

                    if current_id is not None:
                        current_id = str(current_id)

                        if camera_registry.stop_camera(current_id):
                            stopped.append(current_id)

        else:
            stopped = camera_registry.stop_all()

        return jsonify({
            "success": True,
            "message": "Monitoring stop request completed.",
            "stopped_cameras": stopped,
            "monitoring": get_monitoring_summary()
        }), 200

    except Exception:
        logger.exception("Stop monitoring request failed")

        return jsonify({
            "success": False,
            "message": "Unable to stop monitoring."
        }), 500


# =====================================================
# GET MONITORING STATUS
# =====================================================

@monitoring_bp.route("/status", methods=["GET"])
@jwt_required()
def monitoring_status():

    try:
        return jsonify({
            "success": True,
            "monitoring": get_monitoring_summary(),
            "inference": inference_engine.get_status()
        }), 200

    except Exception:
        logger.exception("Unable to fetch monitoring status")

        return jsonify({
            "success": False,
            "message": "Unable to fetch monitoring status."
        }), 500


# =====================================================
# GET ALL REGISTERED CAMERAS
# =====================================================

@monitoring_bp.route("/cameras", methods=["GET"])
@jwt_required()
def get_cameras():

    try:
        cameras = camera_registry.get_all_status() or {}

        return jsonify({
            "success": True,
            "total_cameras": len(cameras),
            "cameras": cameras
        }), 200

    except Exception:
        logger.exception("Unable to fetch camera list")

        return jsonify({
            "success": False,
            "message": "Unable to fetch cameras."
        }), 500


# =====================================================
# LIVE CAMERA FRAME
# =====================================================

@monitoring_bp.route("/frame", methods=["GET"])
@jwt_required()
def get_camera_frame():

    try:
        camera_id = request.args.get("camera_id")

        if not camera_id:
            return jsonify({
                "success": False,
                "message": "camera_id is required."
            }), 400

        frame = camera_registry.get_camera_frame(
            str(camera_id)
        )

        if frame is None:
            return jsonify({
                "success": False,
                "message": "No frame available for this camera."
            }), 404

        return Response(
            frame,
            mimetype="image/jpeg",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )

    except Exception:
        logger.exception("Unable to fetch camera frame")

        return jsonify({
            "success": False,
            "message": "Unable to fetch camera frame."
        }), 500


# =====================================================
# MONITORING HEALTH
# =====================================================

@monitoring_bp.route("/health", methods=["GET"])
@jwt_required()
def monitoring_health():

    return jsonify({
        "success": True,
        "message": "Laptop webcam monitoring service is working.",
        "inference": inference_engine.get_status(),
        "monitoring": get_monitoring_summary()
    }), 200
