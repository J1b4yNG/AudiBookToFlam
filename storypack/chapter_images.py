from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Optional, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont

DEFAULT_SIZE = (320, 240)
DEFAULT_FONT_SIZE = 40
DEFAULT_TEXT_COLOR = "#2C1A04"
DEFAULT_SHADOW_COLOR = "#150E05"


def _load_font(font_path: Optional[Path], font_size: int) -> ImageFont.FreeTypeFont:
    candidates: list = [font_path] if font_path else []
    candidates.append("Georgia.ttf")
    for candidate in candidates:
        try:
            return ImageFont.truetype(str(candidate), font_size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def _wrap_to_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
    words = text.split()
    if not words:
        return [text]
    lines: List[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _fit_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font_path: Optional[Path],
    max_font_size: int,
    max_width: int,
    max_height: int,
    line_spacing: int,
    min_font_size: int = 14,
):
    """Cherche la plus grande taille de police (<= max_font_size) permettant à `text`,
    une fois retourné à la ligne, de tenir dans max_width x max_height."""
    font_size = max_font_size
    while True:
        font = _load_font(font_path, font_size)
        lines = _wrap_to_width(draw, text, font, max_width)
        boxes = [draw.textbbox((0, 0), line, font=font) for line in lines]
        widths = [b[2] - b[0] for b in boxes]
        heights = [b[3] - b[1] for b in boxes]
        total_height = sum(heights) + line_spacing * (len(lines) - 1)
        fits = (not widths or max(widths) <= max_width) and total_height <= max_height
        if fits or font_size <= min_font_size:
            return font, lines, boxes, heights
        font_size -= 2


def generate_chapter_images(
    background: Path,
    labels: Sequence[str],
    output_dir: Path,
    font_path: Optional[Path] = None,
    font_size: int = DEFAULT_FONT_SIZE,
    size: Tuple[int, int] = DEFAULT_SIZE,
    text_color: str = DEFAULT_TEXT_COLOR,
    shadow_color: str = DEFAULT_SHADOW_COLOR,
    text_area_ratio: float = 0.55,
    progress: Optional[Callable[[str], None]] = None,
) -> List[Path]:
    """Génère une image par étiquette (ex: "Chapitre 1", "Chapitre 2", ...) en superposant
    le texte, centré et avec ombre portée, sur une image de fond commune.

    Le texte est automatiquement retourné à la ligne puis la taille de police réduite si besoin
    pour tenir dans une zone centrale de `text_area_ratio` x la taille de l'image (pour rester
    dans le cadre visible d'un fond illustré, ex: bg.png)."""

    def report(message: str) -> None:
        if progress is not None:
            progress(message)

    if not background.exists():
        raise RuntimeError(f"Image de fond introuvable : {background}")

    output_dir.mkdir(parents=True, exist_ok=True)

    with Image.open(background) as bg:
        base = bg.convert("RGB")
        if base.size != size:
            base = base.resize(size)

    max_width = int(size[0] * text_area_ratio)
    max_height = int(size[1] * text_area_ratio)
    line_spacing = 4
    paths: List[Path] = []

    for i, label in enumerate(labels, start=1):
        img = base.copy()
        draw = ImageDraw.Draw(img)

        font, lines, boxes, heights = _fit_text(
            draw, label, font_path, font_size, max_width, max_height, line_spacing
        )
        total_height = sum(heights) + line_spacing * (len(lines) - 1)
        y = (size[1] - total_height) // 2

        for line, box, height in zip(lines, boxes, heights):
            width = box[2] - box[0]
            x = (size[0] - width) // 2
            draw.text((x + 1, y + 1), line, fill=shadow_color, font=font)
            draw.text((x, y), line, fill=text_color, font=font)
            y += height + line_spacing

        dest = output_dir / f"chapitre_{i}.png"
        img.save(dest, "PNG")
        paths.append(dest)
        report(f"Image générée : {dest.name} ({label})")

    return paths
