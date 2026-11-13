
from pathlib import Path

DATASET = (
    Path(__file__).parent
    / "Active-phone-usage-main"
    / "training_dataset"
    / "train"
)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

print("\nACTUAL CLASS INSPECTION")
print("=" * 45)

if not DATASET.exists():
    print("Train folder not found!")
else:
    for folder in sorted(DATASET.iterdir()):
        if folder.is_dir():
            images = [
                f for f in folder.rglob("*")
                if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
            ]

            print(f"\nFolder: {folder.name}")
            print(f"Image count: {len(images)}")

            for image in images[:5]:
                print(f"  {image.name}")

    # Also show images directly inside train
    direct_images = [
        f for f in DATASET.iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
    ]

    print(f"\nImages directly inside train: {len(direct_images)}")

print("\nInspection completed.")
