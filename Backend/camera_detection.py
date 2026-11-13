
import cv2
import time
from ultralytics import YOLO



def main():
    # Lightweight pretrained YOLO model
    model = YOLO("yolo11n.pt")

    # Open default webcam
    camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        print("ERROR: Camera open nahi ho raha.")
        print("Camera permission aur camera index check karein.")
        return

    print("Camera started.")
    print("Exit karne ke liye Q press karein.")

    # Snapshot cooldown: save at most one image every 5 seconds
    last_snapshot_time = 0
    snapshot_cooldown = 5

    try:
        while True:
            success, frame = camera.read()

            if not success:
                print("Camera frame read nahi ho raha.")
                break

            # Run YOLO detection
            results = model.predict(
                source=frame,
                imgsz=416,
                conf=0.35,
                verbose=False
            )

            phone_detected = False

            for result in results:
                for box in result.boxes:
                    class_id = int(box.cls[0].item())
                    class_name = model.names[class_id]
                    confidence = float(box.conf[0].item())

                    # Detect smartphones
                    if class_name == "cell phone":
                        phone_detected = True

                        x1, y1, x2, y2 = map(
                            int,
                            box.xyxy[0].tolist()
                        )

                        # Draw bounding box
                        cv2.rectangle(
                            frame,
                            (x1, y1),
                            (x2, y2),
                            (0, 255, 0),
                            2
                        )

                        label = f"Smartphone {confidence:.2f}"

                        cv2.putText(
                            frame,
                            label,
                            (x1, max(y1 - 10, 20)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.65,
                            (0, 255, 0),
                            2
                        )

                        print(
                            f"Smartphone detected: "
                            f"confidence={confidence:.2f}"
                        )

            # Save an annotated snapshot, with a cooldown
            current_time = time.time()

            if (
                phone_detected
                and current_time - last_snapshot_time >= snapshot_cooldown
            ):
                snapshot_path = save_detection_snapshot(frame)

                if snapshot_path:
                    print(f"Snapshot saved: {snapshot_path}")
                    last_snapshot_time = current_time
                else:
                    print("Snapshot save nahi ho saka.")

            # Show live camera feed
            cv2.imshow(
                "Classroom Smartphone Detection",
                frame
            )

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
