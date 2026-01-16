from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from SubjectiveLocalFolderDataSource import IMAGE_EXTS, _ocr_image


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    images_dir = base_dir / "images"
    output_dir = base_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not images_dir.exists():
        print(f"Missing images folder: {images_dir}")
        return

    image_paths = sorted(
        p for p in images_dir.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    )
    if not image_paths:
        print(f"No images found in: {images_dir}")
        return

    for image_path in image_paths:
        text = _ocr_image(str(image_path), use_gpu=None) or ""
        rel_path = image_path.relative_to(images_dir).with_suffix(".txt")
        out_path = output_dir / rel_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
        print(f"{image_path} -> {out_path} ({len(text)} chars)")


if __name__ == "__main__":
    main()
