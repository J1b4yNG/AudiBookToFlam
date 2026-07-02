from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Optional


def zip_pack(pack_dir: Path, zip_path: Optional[Path] = None) -> Path:
    """Zippe le contenu du dossier de pack (story.json, thumbnail.png, assets/) à sa racine,
    prêt à être importé dans STUdio."""
    if zip_path is None:
        zip_path = pack_dir.with_suffix(".zip")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in pack_dir.rglob("*"):
            if file.is_file():
                zf.write(file, file.relative_to(pack_dir))

    return zip_path
