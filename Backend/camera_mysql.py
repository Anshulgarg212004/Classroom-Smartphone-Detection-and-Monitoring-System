
import os
import time
import getpass

import cv2
import requests
from dotenv import load_dotenv
from ultralytics import YOLO


load_dotenv()

API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "http://127.0.0.1:5000"
).rstrip("/")

MODEL_PATH = "yolo11n.pt"
CONFIDENCE_THRESHOLD = 0.35

# Save at most one record every 5 seconds while a phone is visible.
SAVE_INTERVAL_SECONDS = 5


def login_to_api(session):
    """Login using the existing Flask authentication API."""

    email = input("Enter your registered email: ").strip()
    password = getpass.getpass("Enter your password: ")

    try:
        response = session.post(
            f"{API_BASE_URL}/api/auth/login",
            json={
                "email": email,
                "password": password
            },
            timeout=10
        )

        if response.status_code != 200:
            print("Login failed:", response.text)
            return False

        data = response.json()
        token = data.get("access_token")

        if not token:
            print("Login response did not contain an access token.")
            return False

        session.headers.update({
            "Authorization": f"Bearer {token}"
        })

        print("Login successful.")
        return True

    except requests.RequestException as error:
        print("Cannot connect to Flask API:", error)
        print("Check that your Flask server is running.")
        return False


def save_detection(session, classroom_id, confidence):
    """Send a smartphone detection to the Flask API."""

    payload = {
        "classroom_id": classroom_id,
        "object_name": "cell phone",
        "confidence": round(confidence, 4),
        "snapshot_path": None
    }

    try:
        response = session.post(
            f"{API_BASE_URL}/api/detections/",
            json=payload,
            timeout=10
        )

        if response.status_code == 201:
            data = response.json()
            print(
                f"Saved to MySQL | "
                f"Detection ID: {data.get('id')} | "
                f"Confidence: {confidence:.2f}"
            )
            return True

        print(
            f"Detection save failed "
            f"(HTTP {response.status_code}): {response.text}"
        )
        return False

    except requests.RequestException as error:
        print("Could not send detection to API:", error)
        return False


def main():
    session = requests.Session()

    # Authenticate before starting the camera.
    if not login_to_api(session):
        session.close()
        return

    try:
        classroom_id = int(
            input("Enter an existing classroom ID: ").strip()
        )
        if classroom_id <= 0:
            raise ValueError
    except ValueError:
        print("Please enter a valid positive classroom ID.")
        session.close()
        return

    print("Loading YOLO model...")
    model = YOLO(MODEL_PATH)

    camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        print("ERROR: Could not open webcam.")
        session.close()
        return

    print("Camera + YOLO + Flask + MySQL started.")
    print("Press Q in the camera window to exit.")

    last_saved_time = 0.0

    try:
        while True:
            success, frame = camera.read()

            if not success:
                print("Could not read a camera frame.")
                break

            results = model.predict(
                source=frame,
                imgsz=416,
                conf=CONFIDENCE_THRESHOLD,
                verbose=False
            )

            phone_detections = []

            for result in results:
                for box in result.boxes:
                    class_id = int(box.cls[0].item())
                    class_name = model.names[class_id]
                    confidence = float(box.conf[0].item())

                    if class_name != "cell phone":
                        continue

                    x1, y1, x2, y2 = map(
                        int, box.xyxy[0].tolist()
                    )

                    phone_detections.append(confidence)

                    cv2.rectangle(
                        frame,
                        (x1, y1),
                        (x2, y2),
                        (0, 255, 0),
                        2
                    )

                    cv2.putText(
                        frame,
                        f"Smartphone {confidence:.2f}",
                        (x1, max(y1 - 10, 20)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 255, 0),
                        2
                    )

            now = time.monotonic()

            # Save only the highest-confidence phone detection
            # per interval, even if multiple phones are visible.
            if phone_detections:
                best_confidence = max(phone_detections)

                if now - last_saved_time >= SAVE_INTERVAL_SECONDS:
                    save_detection(
                        session,
                        classroom_id,
                        best_confidence
                    )

                    # Avoid flooding the database if the API fails.
                    last_saved_time = now

            status = (
                "SMARTPHONE DETECTED"
                if phone_detections
                else "No smartphone detected"
            )

            cv2.putText(
                frame,
                status,
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0) if phone_detections else (255, 255, 255),
                2
            )

            cv2.imshow(
                "Classroom Monitoring - YOLO + MySQL",
                frame
            )

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:
        camera.release()
        cv2.destroyAllWindows()
        session.close()
        print("Camera monitoring stopped.")


if __name__ == "__main__":
    main()
