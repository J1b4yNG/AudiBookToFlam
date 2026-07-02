from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def _require_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise RuntimeError(
            "ffmpeg et ffprobe sont requis mais introuvables dans le PATH. "
            "Installe ffmpeg (https://ffmpeg.org/download.html) et réessaie."
        )


def duration_ms(path: Path) -> int:
    """Durée du fichier audio en millisecondes, via ffprobe."""
    _require_ffmpeg()
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True, text=True, check=True,
    )
    return round(float(result.stdout.strip()) * 1000)


def ensure_mp3(path: Path, tmp_dir: Path) -> Path:
    """Retourne un fichier .mp3 "propre" équivalent à `path` : toujours ré-encodé via ffmpeg
    (même si `path` est déjà un .mp3) avec tous les tags/métadonnées (ID3v2, pochette embarquée...)
    retirés.

    Certains outils d'import (ex: Lunii.QT) relisent chaque mp3 du pack avec mutagen pour en
    nettoyer les tags ; un ID3v2 mal formé ou une pochette embarquée par le ripper d'origine peut
    alors faire échouer l'import entier (`HeaderNotFoundError: can't sync to MPEG frame`). Repartir
    d'un flux MPEG audio propre, sans conteneur de tags, évite ce genre de plantage en aval.
    """
    _require_ffmpeg()
    tmp_dir.mkdir(parents=True, exist_ok=True)
    dest = tmp_dir / f"{path.stem}.mp3"
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(path),
            "-vn", "-map_metadata", "-1", "-id3v2_version", "0",
            "-codec:a", "libmp3lame", "-qscale:a", "4",
            str(dest),
        ],
        capture_output=True, check=True,
    )
    return dest


def generate_silence(tmp_dir: Path, seconds: float = 1.0) -> Path:
    """Génère (et met en cache) un court silence mp3 utilisé comme audio de remplissage."""
    _require_ffmpeg()
    tmp_dir.mkdir(parents=True, exist_ok=True)
    dest = tmp_dir / f"_silence_{seconds}.mp3"
    if not dest.exists():
        subprocess.run(
            [
                "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                "-t", str(seconds), "-map_metadata", "-1", "-id3v2_version", "0", "-q:a", "9",
                str(dest),
            ],
            capture_output=True, check=True,
        )
    return dest
