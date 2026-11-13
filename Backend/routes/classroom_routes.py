import time
from flask import Response, stream_with_context
from services.camera_manager import camera_manager
from flask import Blueprint, request, jsonify
from database.db import get_db_connection
from services.camera_manager import camera_manager

classroom_bp = Blueprint("classrooms", __name__)


def classroom_exists(classroom_id):
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "SELECT id FROM classrooms WHERE id = %s",
            (classroom_id,),
        )
        return cursor.fetchone() is not None
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def update_monitoring_status(classroom_id, enabled):
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE classrooms
            SET is_monitoring = %s
            WHERE id = %s
            """,
            (enabled, classroom_id),
        )
        connection.commit()
    except Exception:
        if connection:
            connection.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


# CREATE: Add classroom
@classroom_bp.route("/", methods=["POST"])
def create_classroom():
    data = request.get_json(silent=True) or {}

    name = data.get("name")
    location = data.get("location")
    description = data.get("description")

    if not isinstance(name, str) or not name.strip():
        return jsonify({
            "status": "error",
            "message": "Classroom name is required",
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO classrooms (name, location, description)
            VALUES (%s, %s, %s)
            """,
            (name.strip(), location, description),
        )
        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Classroom created successfully",
            "classroom_id": cursor.lastrowid,
        }), 201

    except Exception:
        if connection:
            connection.rollback()
        return jsonify({
            "status": "error",
            "message": "Could not create classroom",
        }), 500

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


# READ: Get all classrooms
@classroom_bp.route("/", methods=["GET"])
def get_classrooms():
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id, name, location, description, is_monitoring
            FROM classrooms
            ORDER BY id DESC
            """
        )
        classrooms = cursor.fetchall()

        for classroom in classrooms:
            classroom["is_monitoring"] = bool(
                classroom["is_monitoring"]
            )

        return jsonify({
            "status": "success",
            "classrooms": classrooms,
        }), 200

    except Exception:
        return jsonify({
            "status": "error",
            "message": "Could not fetch classrooms",
        }), 500

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


# READ: Get one classroom
@classroom_bp.route("/<int:classroom_id>", methods=["GET"])
def get_classroom(classroom_id):
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id, name, location, description, is_monitoring
            FROM classrooms
            WHERE id = %s
            """,
            (classroom_id,),
        )
        classroom = cursor.fetchone()

        if classroom is None:
            return jsonify({
                "status": "error",
                "message": "Classroom not found",
            }), 404

        classroom["is_monitoring"] = bool(
            classroom["is_monitoring"]
        )

        return jsonify({
            "status": "success",
            "classroom": classroom,
        }), 200

    except Exception:
        return jsonify({
            "status": "error",
            "message": "Could not fetch classroom",
        }), 500

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


# UPDATE: Update classroom details
@classroom_bp.route("/<int:classroom_id>", methods=["PUT"])
def update_classroom(classroom_id):
    data = request.get_json(silent=True) or {}

    name = data.get("name")
    location = data.get("location")
    description = data.get("description")

    if not isinstance(name, str) or not name.strip():
        return jsonify({
            "status": "error",
            "message": "Classroom name is required",
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE classrooms
            SET name = %s, location = %s, description = %s
            WHERE id = %s
            """,
            (name.strip(), location, description, classroom_id),
        )

        if cursor.rowcount == 0:
            cursor.execute(
                "SELECT id FROM classrooms WHERE id = %s",
                (classroom_id,),
            )
            if cursor.fetchone() is None:
                return jsonify({
                    "status": "error",
                    "message": "Classroom not found",
                }), 404

        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Classroom updated successfully",
        }), 200

    except Exception:
        if connection:
            connection.rollback()
        return jsonify({
            "status": "error",
            "message": "Could not update classroom",
        }), 500

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


# DELETE: Delete a classroom
@classroom_bp.route("/<int:classroom_id>", methods=["DELETE"])
def delete_classroom(classroom_id):
    connection = None
    cursor = None

    try:
        # Do not delete a classroom while its camera is active.
        camera_status = camera_manager.status()
        if (
            camera_status["is_running"]
            and camera_status["classroom_id"] == classroom_id
        ):
            return jsonify({
                "status": "error",
                "message": "Stop monitoring before deleting this classroom",
            }), 409

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            "DELETE FROM classrooms WHERE id = %s",
            (classroom_id,),
        )

        if cursor.rowcount == 0:
            return jsonify({
                "status": "error",
                "message": "Classroom not found",
            }), 404

        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Classroom deleted successfully",
        }), 200

    except Exception:
        if connection:
            connection.rollback()
        return jsonify({
            "status": "error",
            "message": (
                "Could not delete classroom. "
                "It may have existing detection records."
            ),
        }), 409

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


# START: Start actual camera monitoring
@classroom_bp.route("/<int:classroom_id>/start", methods=["POST"])
def start_classroom_monitoring(classroom_id):
    try:
        if not classroom_exists(classroom_id):
            return jsonify({
                "status": "error",
                "message": "Classroom not found",
            }), 404

        started, message = camera_manager.start(classroom_id)

        if not started:
            return jsonify({
                "status": "error",
                "message": message,
            }), 409

        try:
            update_monitoring_status(classroom_id, True)
        except Exception:
            # Avoid leaving the camera running if DB update fails.
            camera_manager.stop(classroom_id)
            raise

        return jsonify({
            "status": "success",
            "message": message,
            "classroom_id": classroom_id,
            "is_monitoring": True,
        }), 200

    except Exception:
        return jsonify({
            "status": "error",
            "message": "Could not start classroom monitoring",
        }), 500


# STOP: Stop actual camera monitoring
@classroom_bp.route("/<int:classroom_id>/stop", methods=["POST"])
def stop_classroom_monitoring(classroom_id):
    try:
        if not classroom_exists(classroom_id):
            return jsonify({
                "status": "error",
                "message": "Classroom not found",
            }), 404

        stopped, message = camera_manager.stop(classroom_id)

        if not stopped:
            return jsonify({
                "status": "error",
                "message": message,
            }), 409

        update_monitoring_status(classroom_id, False)

        return jsonify({
            "status": "success",
            "message": message,
            "classroom_id": classroom_id,
            "is_monitoring": False,
        }), 200

    except Exception:
        return jsonify({
            "status": "error",
            "message": "Could not stop classroom monitoring",
        }), 500


# Check the real camera manager status
@classroom_bp.route("/monitoring-status", methods=["GET"])
def get_monitoring_status():
    return jsonify({
        "status": "success",
        "monitoring": camera_manager.status(),
    }), 200


@classroom_bp.route("/video-feed", methods=["GET"])
def classroom_video_feed():

    def generate_frames():
        while True:
            status = camera_manager.status()

            if not status["is_running"]:
                break

            frame = camera_manager.get_jpeg_frame()

            if frame is None:
                time.sleep(0.05)
                continue

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + frame
                + b"\r\n"
            )

            time.sleep(0.03)

    return Response(
        stream_with_context(generate_frames()),
        mimetype="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
        },
    )