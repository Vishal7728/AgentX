"""Optional, non-destructive local enhancement for captured PNG/JPEG files."""
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter

def enhance_image(source: str, destination: str, *, brightness: float = 1.04,
                  contrast: float = 1.05, color: float = 1.03,
                  sharpness: float = 1.08) -> str:
    if not 0.5 <= brightness <= 1.5 or not 0.5 <= contrast <= 1.5:
        raise ValueError("Brightness and contrast must be between 0.5 and 1.5.")
    if not 0.5 <= color <= 1.5 or not 0.5 <= sharpness <= 1.5:
        raise ValueError("Color and sharpness must be between 0.5 and 1.5.")
    src, dst = Path(source), Path(destination)
    if src.resolve() == dst.resolve():
        raise ValueError("Enhanced output must never overwrite the original.")
    dst.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        image = im.convert("RGB")
        image = ImageEnhance.Brightness(image).enhance(brightness)
        image = ImageEnhance.Contrast(image).enhance(contrast)
        image = ImageEnhance.Color(image).enhance(color)
        image = ImageEnhance.Sharpness(image).enhance(sharpness)
        image.save(dst, quality=95, optimize=True)
    return str(dst)
