
from flask import Blueprint, jsonify
from database.db import get_db_connection

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard", methods=["GET"])
def get_dashboard_stats():
    connection = None
    cursor = None

    try:
        # Connect to MySQL
        connection = get_db_connection()

        if connection is None:
            return jsonify({
                "success": False,
                "message": "Database connection failed"
            }), 500

        cursor = connection.cursor(dictionary=True)

        # 1. Total detections
        cursor.execute("""
            SELECT COUNT(*) AS total_detections
            FROM detections
        """)
        total_result = cursor.fetchone()

        # 2. Today's detections
        cursor.execute("""
            SELECT COUNT(*) AS today_detections
            FROM detections
            WHERE detected_at >= CURDATE()
              AND detected_at < CURDATE() + INTERVAL 1 DAY
        """)
        today_result = cursor.fetchone()

        # 3. Total classrooms
        cursor.execute("""
            SELECT COUNT(*) AS total_classrooms
            FROM classrooms
        """)
        classroom_result = cursor.fetchone()

        # 4. Latest five detections
        cursor.execute("""
            SELECT
                d.id,
                d.classroom_id,
                c.name AS classroom_name,
                d.object_name,
                d.confidence,
                d.detected_at,
                d.snapshot_path
            FROM detections AS d
            LEFT JOIN classrooms AS c
                ON d.classroom_id = c.id
            ORDER BY d.detected_at DESC, d.id DESC
            LIMIT 5
        """)
        recent_detections = cursor.fetchall()

        # Convert date/time and other values to JSON-safe values
        for detection in recent_detections:
            if detection.get("detected_at") is not None:
                detection["detected_at"] = (
                    detection["detected_at"].isoformat()
                )

            if detection.get("confidence") is not None:
                detection["confidence"] = float(
                    detection["confidence"]
                )

        # Send response to frontend
        return jsonify({
            "success": True,
            "stats": {
                "total_detections":
                    total_result["total_detections"],
                "today_detections":
                    today_result["today_detections"],
                "total_classrooms":
                    classroom_result["total_classrooms"]
            },
            "recent_detections": recent_detections
        }), 200

    except Exception as error:
        print("Dashboard API Error:", error)

        return jsonify({
            "success": False,
            "message": "Unable to fetch dashboard statistics"
        }), 500

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()
