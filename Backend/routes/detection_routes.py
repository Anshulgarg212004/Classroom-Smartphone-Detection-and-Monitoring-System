
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from mysql.connector import Error
from database.db import get_db_connection

detection_bp = Blueprint("detections", __name__)


def serialize_detection(row):
    """Convert database values into JSON-friendly values."""
    if not row:
        return row

    row["confidence"] = (
        float(row["confidence"])
        if row["confidence"] is not None
        else None
    )

    if row.get("detected_at"):
        row["detected_at"] = row["detected_at"].isoformat(
            sep=" "
        )

    return row


def valid_confidence(value):
    try:
        number = float(value)
        return 0 <= number <= 1
    except (TypeError, ValueError):
        return False


# 1. CREATE: Save a detection record
@detection_bp.route("/", methods=["POST"])
@jwt_required()
def create_detection():
    data = request.get_json(silent=True) or {}

    classroom_id = data.get("classroom_id")
    object_name = data.get("object_name", "cell phone")
    confidence = data.get("confidence")
    snapshot_path = data.get("snapshot_path")

    try:
        classroom_id = int(classroom_id)
        if classroom_id <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({
            "success": False,
            "message": "A valid classroom_id is required."
        }), 400

    if not isinstance(object_name, str) or not object_name.strip():
        return jsonify({
            "success": False,
            "message": "object_name must be a non-empty string."
        }), 400

    if not valid_confidence(confidence):
        return jsonify({
            "success": False,
            "message": "confidence must be between 0 and 1."
        }), 400

    if snapshot_path is not None and not isinstance(snapshot_path, str):
        return jsonify({
            "success": False,
            "message": "snapshot_path must be a string or null."
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO detections
                (classroom_id, object_name, confidence,
                 detected_at, snapshot_path)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP, %s)
            """,
            (
                classroom_id,
                object_name.strip(),
                float(confidence),
                snapshot_path
            )
        )

        connection.commit()
        detection_id = cursor.lastrowid

        return jsonify({
            "success": True,
            "message": "Detection record created successfully.",
            "id": detection_id
        }), 201

    except Error:
        if connection and connection.is_connected():
            connection.rollback()

        return jsonify({
            "success": False,
            "message": (
                "Could not create detection. Check that the "
                "classroom exists and the database is available."
            )
        }), 400

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


# 2. READ: Get all records, optionally filter by classroom
@detection_bp.route("/", methods=["GET"])
@jwt_required()
def get_detections():
    classroom_id = request.args.get("classroom_id")
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        if classroom_id is not None:
            try:
                classroom_id = int(classroom_id)
                if classroom_id <= 0:
                    raise ValueError
            except ValueError:
                return jsonify({
                    "success": False,
                    "message": "Invalid classroom_id."
                }), 400

            cursor.execute(
                """
                SELECT id, classroom_id, object_name, confidence,
                       detected_at, snapshot_path
                FROM detections
                WHERE classroom_id = %s
                ORDER BY detected_at DESC, id DESC
                """,
                (classroom_id,)
            )
        else:
            cursor.execute(
                """
                SELECT id, classroom_id, object_name, confidence,
                       detected_at, snapshot_path
                FROM detections
                ORDER BY detected_at DESC, id DESC
                """
            )

        records = [
            serialize_detection(row)
            for row in cursor.fetchall()
        ]

        return jsonify({
            "success": True,
            "count": len(records),
            "detections": records
        }), 200

    except Error:
        return jsonify({
            "success": False,
            "message": "Could not retrieve detection records."
        }), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


# 3. READ: Get one record by ID
@detection_bp.route("/<int:detection_id>", methods=["GET"])
@jwt_required()
def get_detection(detection_id):
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id, classroom_id, object_name, confidence,
                   detected_at, snapshot_path
            FROM detections
            WHERE id = %s
            """,
            (detection_id,)
        )

        record = cursor.fetchone()

        if not record:
            return jsonify({
                "success": False,
                "message": "Detection record not found."
            }), 404

        return jsonify({
            "success": True,
            "detection": serialize_detection(record)
        }), 200

    except Error:
        return jsonify({
            "success": False,
            "message": "Could not retrieve the detection record."
        }), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


# 4. UPDATE: Update selected fields of a record
@detection_bp.route("/<int:detection_id>", methods=["PUT"])
@jwt_required()
def update_detection(detection_id):
    data = request.get_json(silent=True) or {}

    allowed_fields = {
        "classroom_id",
        "object_name",
        "confidence",
        "snapshot_path"
    }

    updates = {}

    for field in allowed_fields:
        if field in data:
            updates[field] = data[field]

    if not updates:
        return jsonify({
            "success": False,
            "message": "Provide at least one field to update."
        }), 400

    if "classroom_id" in updates:
        try:
            updates["classroom_id"] = int(updates["classroom_id"])
            if updates["classroom_id"] <= 0:
                raise ValueError
        except (TypeError, ValueError):
            return jsonify({
                "success": False,
                "message": "Invalid classroom_id."
            }), 400

    if "object_name" in updates:
        if (
            not isinstance(updates["object_name"], str)
            or not updates["object_name"].strip()
        ):
            return jsonify({
                "success": False,
                "message": "object_name must be a non-empty string."
            }), 400
        updates["object_name"] = updates["object_name"].strip()

    if "confidence" in updates:
        if not valid_confidence(updates["confidence"]):
            return jsonify({
                "success": False,
                "message": "confidence must be between 0 and 1."
            }), 400
        updates["confidence"] = float(updates["confidence"])

    if (
        "snapshot_path" in updates
        and updates["snapshot_path"] is not None
        and not isinstance(updates["snapshot_path"], str)
    ):
        return jsonify({
            "success": False,
            "message": "snapshot_path must be a string or null."
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            "SELECT id FROM detections WHERE id = %s",
            (detection_id,)
        )

        if not cursor.fetchone():
            return jsonify({
                "success": False,
                "message": "Detection record not found."
            }), 404

        # Field names come only from the allowlist above.
        set_clause = ", ".join(
            f"{field} = %s" for field in updates
        )
        values = list(updates.values()) + [detection_id]

        cursor.execute(
            f"UPDATE detections SET {set_clause} WHERE id = %s",
            values
        )
        connection.commit()

        return jsonify({
            "success": True,
            "message": "Detection record updated successfully."
        }), 200

    except Error:
        if connection and connection.is_connected():
            connection.rollback()

        return jsonify({
            "success": False,
            "message": (
                "Could not update the record. Check that the "
                "classroom exists and the database is available."
            )
        }), 400

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


# 5. DELETE: Delete one record
@detection_bp.route("/<int:detection_id>", methods=["DELETE"])
@jwt_required()
def delete_detection(detection_id):
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            "DELETE FROM detections WHERE id = %s",
            (detection_id,)
        )

        if cursor.rowcount == 0:
            return jsonify({
                "success": False,
                "message": "Detection record not found."
            }), 404

        connection.commit()

        return jsonify({
            "success": True,
            "message": "Detection record deleted successfully."
        }), 200

    except Error:
        if connection and connection.is_connected():
            connection.rollback()

        return jsonify({
            "success": False,
            "message": "Could not delete the detection record."
        }), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()