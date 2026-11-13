
import cv2
import time
import sys
from pathlib import Path

# Ensure backend folder is available for imports
BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

from services.phone_usage_recognizer import PhoneUsageRecognizer


def main():
    print("=" * 50)
    print("CLASSROOM PHONE USAGE - LIVE TEST")
    print("=" * 50)

    recognizer = PhoneUsageRecognizer(
        phone_confidence=0.25,
        pose_confidence=0.30,
        required_frames=5,
        image_size=416,
    )

    print("\nLoading YOLO models...")
    print("Opening webcam...")

    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    if not camera.isOpened():
        print("ERROR: Webcam could not be opened.")
        print("Close other camera applications and try again.")
        return

    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    print("\nWebcam started successfully.")
    print("Press Q or ESC to exit.")

    previous_status = ""
    previous_time = time.time()
    fps = 0

    try:
        while True:
            success, frame = camera.read()

            if not success:
                print("ERROR: Unable to read webcam frame.")
                break

            try:
                result = recognizer.process_frame(frame)
            except Exception as error:
                print("Recognition error:", error)
                break

            output_frame = result["frame"]

            # Calculate FPS
            current_time = time.time()
            elapsed = current_time - previous_time

            if elapsed > 0:
                fps = 1 / elapsed

            previous_time = current_time

            cv2.putText(
                output_frame,
                f"FPS: {fps:.1f}",
                (15, 90),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 255, 255),
                2,
            )

            # Print only when status changes
            if result["status"] != previous_status:
                print(
                    f"Status: {result['status']} | "
                    f"Phones: {result['phone_count']}"
                )
                previous_status = result["status"]

            cv2.imshow(
                "Classroom Phone Usage Recognition",
                output_frame,
            )

            key = cv2.waitKey(1) & 0xFF

            if key == ord("q") or key == 27:
                print("\nStopping webcam test...")
                break

    finally:
        camera.release()
        cv2.destroyAllWindows()
        print("Webcam released successfully.")


if __name__ == "__main__":
    main()
