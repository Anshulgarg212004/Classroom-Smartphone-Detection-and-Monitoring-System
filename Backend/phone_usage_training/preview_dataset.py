
from pathlib import Path
from PIL import Image, ImageDraw
import math

BASE_DIR = Path(__file__).parent / "Active-phone-usage-main"
TRAIN_DIR = BASE_DIR / "training_dataset" / "train"

CLASSES = ["phone", "pos_machine"]
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

THUMB_WIDTH = 250
THUMB_HEIGHT = 180
LABEL_HEIGHT = 35
COLUMNS = 3

all_items = []

for class_name in CLASSES:
    folder = TRAIN_DIR / class_name

    if not folder.exists():
        print(f"Folder missing: {folder}")
        continue

    images = sorted(
        p for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    )

    for path in images:
        all_items.append((path, class_name))

if not all_items:
    print("No images found!")
    raise SystemExit

rows = math.ceil(len(all_items) / COLUMNS)

sheet = Image.new(
    "RGB",
    (COLUMNS * THUMB_WIDTH, rows * (THUMB_HEIGHT + LABEL_HEIGHT)),
    "white"
)

draw = ImageDraw.Draw(sheet)

for index, (path, class_name) in enumerate(all_items):
    try:
        image = Image.open(path).convert("RGB")
        image.thumbnail((THUMB_WIDTH - 10, THUMB_HEIGHT - 10))

        x = (index % COLUMNS) * THUMB_WIDTH
        y = (index // COLUMNS) * (THUMB_HEIGHT + LABEL_HEIGHT)

        image_x = x + (THUMB_WIDTH - image.width) // 2
        image_y = y + (THUMB_HEIGHT - image.height) // 2

        sheet.paste(image, (image_x, image_y))
        draw.text(
            (x + 5, y + THUMB_HEIGHT + 5),
            f"{class_name}: {path.name[:28]}",
            fill="black"
        )

    except Exception as error:
        print(f"Could not read {path.name}: {error}")

output = Path(__file__).parent / "dataset_preview.jpg"
sheet.save(output, quality=85)

print(f"\nPreview created: {output}")
print(f"Images included: {len(all_items)}")
