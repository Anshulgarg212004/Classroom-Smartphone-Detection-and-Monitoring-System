
import os
import logging

from dotenv import load_dotenv

# Load backend/.env before importing application modules.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

load_dotenv(
    os.path.join(BASE_DIR, ".env")
)

from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from database.db import get_db_connection

from routes.monitoring_routes import monitoring_bp
from routes.auth_routes import auth_bp
from routes.classroom_routes import classroom_bp
from routes.detection_routes import detection_bp
from routes.dashboard_routes import dashboard_bp


# ---------------------------------------------
# LOGGING CONFIGURATION
# ---------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)


# ---------------------------------------------
# FLASK APPLICATION
# ---------------------------------------------

app = Flask(__name__)


# ---------------------------------------------
# JWT CONFIGURATION
# ---------------------------------------------

app.config["JWT_SECRET_KEY"] = os.getenv(
    "JWT_SECRET_KEY"
)

if not app.config["JWT_SECRET_KEY"]:

    raise RuntimeError(
        "JWT_SECRET_KEY is missing from backend/.env"
    )

jwt = JWTManager(app)


# ---------------------------------------------
# CORS CONFIGURATION
# ---------------------------------------------

CORS(
    app,
    resources={
        r"/api/*": {
            "origins": [
                "http://localhost:5173",
                "http://127.0.0.1:5173"
            ]
        }
    }
)


# ---------------------------------------------
# REGISTER API BLUEPRINTS
# ---------------------------------------------

app.register_blueprint(
    auth_bp,
    url_prefix="/api/auth"
)

app.register_blueprint(
    classroom_bp,
    url_prefix="/api/classrooms"
)

app.register_blueprint(
    detection_bp,
    url_prefix="/api/detections"
)

app.register_blueprint(
    dashboard_bp,
    url_prefix="/api"
)

app.register_blueprint(
    monitoring_bp,
    url_prefix="/api/monitoring"
)


# ---------------------------------------------
# HOME ROUTE
# ---------------------------------------------

@app.route("/")
def home():

    return jsonify({
        "project": (
            "AI-Based Classroom Smartphone Detection "
            "and Monitoring System"
        ),
        "status": "running"
    })


# ---------------------------------------------
# API HEALTH CHECK
# ---------------------------------------------

@app.route("/api/health")
def health():

    return jsonify({
        "status": "success",
        "message": "Flask API is working"
    })


# ---------------------------------------------
# DATABASE HEALTH CHECK
# ---------------------------------------------

@app.route("/api/db-health")
def database_health():

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            "SELECT DATABASE()"
        )

        result = cursor.fetchone()

        database_name = (
            result[0]
            if result
            else None
        )

        return jsonify({
            "status": "success",
            "database": database_name
        })

    except Exception:

        app.logger.exception(
            "Database connection failed"
        )

        return jsonify({
            "status": "error",
            "message": "Database connection failed"
        }), 500

    finally:

        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()


# ---------------------------------------------
# APPLICATION START
# ---------------------------------------------

if __name__ == "__main__":

    app.logger.info(
        "Starting AI Classroom Monitoring Backend..."
    )

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
        use_reloader=False,
        threaded=True
    )
