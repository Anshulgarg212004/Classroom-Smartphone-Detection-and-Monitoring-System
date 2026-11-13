
import threading
import time
import os

from dotenv import load_dotenv
from werkzeug.serving import make_server


load_dotenv()

# Import your existing Flask application
from app import app
import camera_mysql


def run_flask():
    server = make_server("127.0.0.1", 5000, app)
    server.serve_forever()


if __name__ == "__main__":
    flask_thread = threading.Thread(
        target=run_flask,
        daemon=True
    )
    flask_thread.start()

    # Give Flask a moment to start
    time.sleep(1)

    print("Flask server started on http://127.0.0.1:5000")
    print("Starting camera monitoring...")

    camera_mysql.main()
