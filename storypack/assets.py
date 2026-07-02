from __future__ import annotations

import hashlib
from pathlib import Path


class AssetStore:
    """Copie des fichiers dans un dossier assets/, nommés par le hash de leur contenu.

    Le même contenu (ex: le silence de remplissage réutilisé plusieurs fois) n'est
    écrit qu'une seule fois sur le disque.
    """

    def __init__(self, assets_dir: Path):
        self.assets_dir = assets_dir
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self._known_hashes: set[str] = set()

    def add_file(self, src: Path) -> str:
        data = src.read_bytes()
        digest = hashlib.sha1(data).hexdigest()
        filename = f"{digest}{src.suffix.lower()}"

        if digest not in self._known_hashes:
            (self.assets_dir / filename).write_bytes(data)
            self._known_hashes.add(digest)

        return filename
