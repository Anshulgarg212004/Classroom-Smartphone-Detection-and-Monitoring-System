
from pathlib import Path
from collections import Counter

# Dataset location
BASE_DIR = Path(__file__).parent / "Active-phone-usage-main"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}

def get_size_mb(path):
    return sum(
        file.stat().st_size
        for file in path.rglob("*")
        if file.is_file()
    ) / (1024 * 1024)

def inspect_folder(folder):
    if not folder.exists():
        print(f"\nFolder not found: {folder}")
        return

    files = [p for p in folder.rglob("*") if p.is_file()]

    images = [p for p in files if p.suffix.lower() in IMAGE_EXTENSIONS]
    videos = [p for p in files if p.suffix.lower() in VIDEO_EXTENSIONS]

    print(f"\n{'=' * 55}")
    print(f"FOLDER: {folder.name}")
    print(f"{'=' * 55}")

    print(f"Total files : {len(files)}")
    print(f"Images      : {len(images)}")
    print(f"Videos      : {len(videos)}")
    print(f"Total size  : {get_size_mb(folder):.2f} MB")

    print("\nSubfolders and image counts:")

    subfolders = sorted(
        [p for p in folder.iterdir() if p.is_dir()]
    )

    if not subfolders:
        print("No direct subfolders found.")

    for subfolder in subfolders:
        image_count = sum(
            1 for p in subfolder.rglob("*")
            if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
        )
        print(f"  {subfolder.name}: {image_count} images")

    print("\nFile extensions:")
    extensions = Counter(p.suffix.lower() for p in files)
    for ext, count in extensions.most_common():
        print(f"  {ext or '[no extension]'}: {count}")

    print("\nSample files:")
    for file in files[:10]:
        print(f"  {file.relative_to(folder)}")


def main():
    print("ACTIVE PHONE USAGE DATASET INSPECTION")
    print(f"Dataset path: {BASE_DIR}")

    if not BASE_DIR.exists():
        print("\nERROR: Dataset folder not found.")
        print("Check the folder name and location.")
        return

    print(f"Complete dataset size: {get_size_mb(BASE_DIR):.2f} MB")

    inspect_folder(BASE_DIR / "training_dataset")
    inspect_folder(BASE_DIR / "video_dataset")

    print("\nInspection completed.")
    print("No dataset files were modified.")


if __name__ == "__main__":
    main()
