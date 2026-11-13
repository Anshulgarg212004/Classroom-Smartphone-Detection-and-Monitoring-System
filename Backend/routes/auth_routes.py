
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity,
    get_jwt
)
from werkzeug.security import generate_password_hash, check_password_hash
from mysql.connector import IntegrityError, Error

from database.db import get_db_connection


auth_bp = Blueprint("auth", __name__)


# 1. User Registration
@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}

    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not name or not email or not password:
        return jsonify({
            "success": False,
            "message": "Name, email and password are required."
        }), 400

    if len(password) < 8:
        return jsonify({
            "success": False,
            "message": "Password must contain at least 8 characters."
        }), 400

    # Public registration always creates a staff account.
    # Users must not be allowed to assign themselves admin role.
    password_hash = generate_password_hash(password)

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        query = """
            INSERT INTO users (name, email, password_hash, role)
            VALUES (%s, %s, %s, %s)
        """

        cursor.execute(
            query,
            (name, email, password_hash, "staff")
        )
        connection.commit()

        user_id = cursor.lastrowid

        return jsonify({
            "success": True,
            "message": "Registration successful.",
            "user": {
                "id": user_id,
                "name": name,
                "email": email,
                "role": "staff"
            }
        }), 201

    except IntegrityError:
        if connection and connection.is_connected():
            connection.rollback()

        return jsonify({
            "success": False,
            "message": "This email is already registered."
        }), 409

    except Error:
        if connection and connection.is_connected():
            connection.rollback()

        return jsonify({
            "success": False,
            "message": "Database operation failed."
        }), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


# 2. User Login
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({
            "success": False,
            "message": "Email and password are required."
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id, name, email, password_hash, role
            FROM users
            WHERE email = %s
            """,
            (email,)
        )

        user = cursor.fetchone()

        if not user or not check_password_hash(
            user["password_hash"], password
        ):
            return jsonify({
                "success": False,
                "message": "Invalid email or password."
            }), 401

        access_token = create_access_token(
            identity=str(user["id"]),
            additional_claims={
                "role": user["role"],
                "email": user["email"]
            }
        )

        return jsonify({
            "success": True,
            "message": "Login successful.",
            "access_token": access_token,
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "role": user["role"]
            }
        }), 200

    except Error:
        return jsonify({
            "success": False,
            "message": "Database operation failed."
        }), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


# 3. Protected Profile API
@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    user_id = get_jwt_identity()
    claims = get_jwt()

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id, name, email, role, created_at
            FROM users
            WHERE id = %s
            """,
            (int(user_id),)
        )

        user = cursor.fetchone()

        if not user:
            return jsonify({
                "success": False,
                "message": "User not found."
            }), 404

        return jsonify({
            "success": True,
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "role": user["role"],
                "created_at": (
                    user["created_at"].isoformat()
                    if user["created_at"] else None
                )
            },
            "token_role": claims.get("role")
        }), 200

    except (Error, ValueError):
        return jsonify({
            "success": False,
            "message": "Could not retrieve profile."
        }), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()