from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

from PIL import Image


def ensure_png(path: Path, tmp_dir: Path, max_size: Optional[Tuple[int, int]] = None) -> Path:
    """Retourne une image .png équivalente à `path` (convertie/redimensionnée si besoin)."""
    if path.suffix.lower() == ".png" and max_size is None:
        return path

    tmp_dir.mkdir(parents=True, exist_ok=True)
    dest = tmp_dir / f"{path.stem}.png"

    with Image.open(path) as img:
        img = img.convert("RGB")
        if max_size:
            img.thumbnail(max_size, Image.LANCZOS)
        img.save(dest, "PNG")

    return dest
