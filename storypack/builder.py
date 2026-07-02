from __future__ import annotations

import json
import re
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Tuple

from . import audio, images
from .assets import AssetStore
from .chapter_images import generate_chapter_images

AUDIO_EXTS = {".mp3", ".mka", ".m4a", ".ogg", ".oga", ".wav", ".flac", ".aac"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

# Noms d'entrées que build_pack() est seul à créer dans output_dir : c'est tout ce qu'il est
# autorisé à effacer avant de régénérer un pack, jamais le reste du contenu du dossier.
_PACK_OWNED_ENTRIES = {"assets", "story.json", "thumbnail.png", "_tmp"}


def _is_within_or_equal(path: Path, other: Path) -> bool:
    return path == other or other in path.parents


def _prepare_output_dir(output_dir: Path, input_dir: Path) -> None:
    """Prépare `output_dir` en n'effaçant que ce que cet outil a lui-même généré lors d'un
    précédent passage, jamais un dossier existant arbitraire (cf. les dangers de shutil.rmtree
    sur un chemin fourni par l'utilisateur)."""
    output_resolved = output_dir.resolve()
    input_resolved = input_dir.resolve()

    if _is_within_or_equal(output_resolved, input_resolved) or _is_within_or_equal(input_resolved, output_resolved):
        raise RuntimeError(
            "Le dossier de sortie ne peut pas être le dossier d'entrée, ni un dossier "
            "parent/enfant de celui-ci (cela risquerait d'effacer tes fichiers sources)."
        )

    home = Path.home().resolve()
    if output_resolved == home or output_resolved.parent == output_resolved:
        raise RuntimeError(
            f"{output_resolved} ressemble à ton dossier utilisateur ou à une racine de disque : "
            "choisis un sous-dossier dédié pour éviter d'effacer des données par erreur."
        )

    if not output_dir.exists():
        output_dir.mkdir(parents=True)
        return

    if not output_dir.is_dir():
        raise RuntimeError(f"{output_dir} existe déjà et n'est pas un dossier.")

    existing_entries = {p.name for p in output_dir.iterdir()}
    unexpected = existing_entries - _PACK_OWNED_ENTRIES
    if unexpected:
        raise RuntimeError(
            f"{output_dir} existe déjà et contient des fichiers qui ne semblent pas provenir "
            f"d'un pack généré par cet outil ({', '.join(sorted(unexpected))}). "
            "Choisis un dossier vide ou inexistant pour éviter d'écraser des données par erreur."
        )

    for name in _PACK_OWNED_ENTRIES:
        target = output_dir / name
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()


@dataclass
class Chapter:
    title: str
    audio_path: Path
    image_path: Optional[Path]


def _natural_key(path: Path):
    parts = re.split(r"(\d+)", path.stem)
    return [int(p) if p.isdigit() else p.lower() for p in parts]


def _clean_title(stem: str) -> str:
    title = re.sub(r"^[\d_\-.\s]+", "", stem)
    title = title.replace("_", " ").strip()
    return title or stem


def discover_chapters(input_dir: Path) -> list[Chapter]:
    entries = list(input_dir.iterdir())

    audio_files = sorted(
        (p for p in entries if p.is_file() and p.suffix.lower() in AUDIO_EXTS),
        key=_natural_key,
    )
    if not audio_files:
        raise RuntimeError(f"Aucun fichier audio (.mp3/.mka/...) trouvé dans {input_dir}")

    image_files = sorted(
        (p for p in entries if p.is_file() and p.suffix.lower() in IMAGE_EXTS),
        key=_natural_key,
    )
    image_by_stem = {p.stem.lower(): p for p in image_files}

    chapters = []
    for i, a in enumerate(audio_files):
        img = image_by_stem.get(a.stem.lower())
        if img is None and i < len(image_files):
            img = image_files[i]
        chapters.append(Chapter(title=_clean_title(a.stem), audio_path=a, image_path=img))
    return chapters


def build_pack(
    input_dir: Path,
    output_dir: Path,
    title: str,
    description: str = "",
    cover_image: Optional[Path] = None,
    night_mode: bool = False,
    resize: Optional[Tuple[int, int]] = None,
    preview_mode: str = "silence",
    auto_chapter_bg: Optional[Path] = None,
    auto_chapter_font: Optional[Path] = None,
    auto_chapter_font_size: int = 40,
    auto_chapter_label_mode: str = "number",
    force_chapter_images: bool = False,
    progress: Optional[Callable[[str], None]] = None,
) -> Path:
    """Construit un dossier de pack STUdio (story.json + thumbnail.png + assets/) à partir
    d'un dossier contenant les fichiers audio chapitrés (mp3/mka) et leurs images.

    Si `auto_chapter_bg` est fourni, une image de chapitre ("Chapitre N" ou le titre du
    chapitre, selon `auto_chapter_label_mode`) est générée à la volée sur cette image de fond
    pour chaque chapitre sans image associée (ou pour tous si `force_chapter_images=True`)."""

    def report(message: str) -> None:
        if progress is not None:
            progress(message)

    if preview_mode not in ("silence", "full"):
        raise ValueError("preview_mode doit être 'silence' ou 'full'")
    if auto_chapter_label_mode not in ("number", "title"):
        raise ValueError("auto_chapter_label_mode doit être 'number' ou 'title'")

    report(f"Analyse du dossier d'entrée : {input_dir}")
    chapters = discover_chapters(input_dir)
    n = len(chapters)
    report(f"{n} chapitre(s) détecté(s).")

    _prepare_output_dir(output_dir, input_dir)
    assets_dir = output_dir / "assets"
    assets_dir.mkdir(parents=True)
    tmp_dir = output_dir / "_tmp"

    if auto_chapter_bg is not None:
        targets = [i for i, ch in enumerate(chapters) if force_chapter_images or ch.image_path is None]
        if targets:
            report("Génération automatique des images de chapitre...")
            if auto_chapter_label_mode == "title":
                labels = [chapters[i].title for i in targets]
            else:
                labels = [f"Chapitre {i + 1}" for i in targets]
            generated = generate_chapter_images(
                background=auto_chapter_bg,
                labels=labels,
                output_dir=tmp_dir / "chapter_images",
                font_path=auto_chapter_font,
                font_size=auto_chapter_font_size,
                progress=report,
            )
            for idx, path in zip(targets, generated):
                chapters[idx].image_path = path

    store = AssetStore(assets_dir)

    cover_src = cover_image or chapters[0].image_path
    if cover_src is None:
        raise RuntimeError(
            "Aucune image de couverture fournie (--cover) et aucun chapitre n'a d'image associée."
        )
    report("Préparation de l'image de couverture...")
    cover_png = images.ensure_png(cover_src, tmp_dir, resize)
    cover_asset = store.add_file(cover_png)

    report("Génération de l'audio de remplissage...")
    silence_path = audio.generate_silence(tmp_dir, 1.0)
    silence_asset = store.add_file(silence_path)

    def new_id() -> str:
        return str(uuid.uuid4())

    action_nodes: list[dict] = []
    stage_nodes: list[dict] = []

    cover_uuid = new_id()
    intro_action_id = new_id()
    intro_stage_uuid = new_id()
    selector_action_id = new_id()

    # Écran de couverture : appui OK -> écran d'intro du menu de sélection.
    stage_nodes.append({
        "audio": silence_asset,
        "controlSettings": {"autoplay": False, "home": False, "ok": True, "pause": False, "wheel": False},
        "homeTransition": None,
        "image": cover_asset,
        "name": "Cover node",
        "okTransition": {"actionNode": intro_action_id, "optionIndex": 0},
        "position": {"x": 0, "y": 0},
        "squareOne": True,
        "type": "stage",
        "uuid": cover_uuid,
    })
    action_nodes.append({
        "id": intro_action_id,
        "name": "Action node",
        "options": [intro_stage_uuid],
        "position": {"x": 0, "y": 0},
    })

    # Écran d'intro du menu : appui OK -> premier chapitre du sélecteur.
    stage_nodes.append({
        "audio": silence_asset,
        "controlSettings": {"autoplay": True, "home": True, "ok": True, "pause": False, "wheel": False},
        "homeTransition": None,
        "image": cover_asset,
        "name": "Quel chapitre",
        "okTransition": {"actionNode": selector_action_id, "optionIndex": 0},
        "position": {"x": 0, "y": 0},
        "squareOne": False,
        "type": "stage",
        "uuid": intro_stage_uuid,
    })

    menu_uuids = [new_id() for _ in chapters]
    full_uuids = [new_id() for _ in chapters]

    selector_action = {
        "id": selector_action_id,
        "name": "Quel chapitre",
        "options": menu_uuids,
        "position": {"x": 0, "y": 0},
    }
    action_nodes.append(selector_action)

    for i, chapter in enumerate(chapters):
        report(f"[{i + 1}/{n}] {chapter.title}")

        if chapter.image_path is not None:
            chapter_png = images.ensure_png(chapter.image_path, tmp_dir, resize)
            chapter_image_asset = store.add_file(chapter_png)
        else:
            chapter_image_asset = cover_asset

        report("  -> ré-encodage audio (nettoyage des tags ID3)...")
        chapter_mp3 = audio.ensure_mp3(chapter.audio_path, tmp_dir)
        chapter_audio_asset = store.add_file(chapter_mp3)
        duration = audio.duration_ms(chapter_mp3)

        preview_asset = chapter_audio_asset if preview_mode == "full" else silence_asset
        chapter_action_id = new_id()

        # Carte menu du chapitre : image + molette pour naviguer, OK pour lancer le chapitre.
        stage_nodes.append({
            "audio": preview_asset,
            "controlSettings": {"autoplay": False, "home": True, "ok": True, "pause": False, "wheel": True},
            "homeTransition": {"actionNode": intro_action_id, "optionIndex": 0},
            "image": chapter_image_asset,
            "name": chapter.title,
            "okTransition": {"actionNode": chapter_action_id, "optionIndex": 0},
            "position": {"x": 0, "y": 0},
            "squareOne": False,
            "type": "stage",
            "uuid": menu_uuids[i],
        })

        action_nodes.append({
            "id": chapter_action_id,
            "name": "Action node",
            "options": [full_uuids[i]],
            "position": {"x": 0, "y": 0},
        })

        # Lecture complète du chapitre : à la fin, enchaîne sur le chapitre suivant du menu.
        stage_nodes.append({
            "audio": chapter_audio_asset,
            "controlSettings": {"autoplay": True, "home": True, "ok": False, "pause": True, "wheel": False},
            "homeTransition": {"actionNode": selector_action_id, "optionIndex": i},
            "image": None,
            "name": chapter.title,
            "okTransition": {"actionNode": selector_action_id, "optionIndex": (i + 1) % n},
            "position": {"x": 0, "y": 0},
            "squareOne": False,
            "type": "stage",
            "uuid": full_uuids[i],
            "duration": duration,
        })

    story = {
        "title": title,
        "version": 1,
        "description": description,
        "format": "v1",
        "nightModeAvailable": night_mode,
        "actionNodes": action_nodes,
        "stageNodes": stage_nodes,
    }

    report("Écriture de story.json...")
    (output_dir / "story.json").write_text(
        json.dumps(story, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    shutil.copyfile(cover_png, output_dir / "thumbnail.png")

    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)

    return output_dir
