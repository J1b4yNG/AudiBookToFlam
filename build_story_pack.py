#!/usr/bin/env python3
"""Génère un pack d'histoire (format STUdio v1) à partir d'un dossier d'audiobook chapitré.

Exemple :
    python build_story_pack.py --input "D:\\Livres\\HarryPotter1" --output "out\\HarryPotter1" \
        --title "Harry Potter à l'école des sorciers" --zip
"""
from __future__ import annotations

import argparse
from pathlib import Path

from storypack.builder import build_pack
from storypack.packaging import zip_pack


def parse_size(value: str) -> tuple[int, int]:
    try:
        w, h = value.lower().split("x")
        return int(w), int(h)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Format attendu: LARGEURxHAUTEUR, ex: 320x240") from exc


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", required=True, type=Path, help="Dossier contenant les fichiers audio (mp3/mka) et images des chapitres")
    parser.add_argument("--output", required=True, type=Path, help="Dossier de sortie du pack")
    parser.add_argument("--title", required=True, help="Titre de l'histoire")
    parser.add_argument("--description", default="", help="Description (optionnelle)")
    parser.add_argument("--cover", type=Path, default=None, help="Image de couverture (sinon: image du 1er chapitre)")
    parser.add_argument("--night-mode", action="store_true", help="Active le mode nuit sur le pack")
    parser.add_argument("--resize", type=parse_size, default=None, help="Redimensionne les images, ex: 320x240")
    parser.add_argument(
        "--preview", choices=["silence", "full"], default="silence",
        help="Audio joué sur la carte menu de chaque chapitre avant validation OK : "
             "'silence' (défaut, 1s) ou 'full' (réutilise l'audio complet du chapitre)",
    )
    parser.add_argument("--zip", action="store_true", help="Produit aussi un .zip du pack, prêt à importer dans STUdio")

    parser.add_argument(
        "--chapter-bg", type=Path, default=None,
        help="Image de fond utilisée pour générer automatiquement les images de chapitre manquantes "
             "(texte 'Chapitre N' ou titre incrusté dessus, cf storypack/chapter_images.py)",
    )
    parser.add_argument("--chapter-font", type=Path, default=None, help="Police (.ttf/.otf) pour le texte des images de chapitre générées")
    parser.add_argument("--chapter-font-size", type=int, default=40, help="Taille de police pour les images de chapitre générées (défaut: 40)")
    parser.add_argument(
        "--chapter-label-mode", choices=["number", "title"], default="number",
        help="Texte incrusté sur les images de chapitre générées : 'number' -> 'Chapitre N' (défaut), 'title' -> titre du chapitre",
    )
    parser.add_argument(
        "--force-chapter-images", action="store_true",
        help="Régénère l'image de tous les chapitres avec --chapter-bg, même ceux qui ont déjà une image",
    )

    args = parser.parse_args()

    if not args.input.is_dir():
        raise SystemExit(f"Dossier d'entrée introuvable : {args.input}")

    try:
        pack_dir = build_pack(
            input_dir=args.input,
            output_dir=args.output,
            title=args.title,
            description=args.description,
            cover_image=args.cover,
            night_mode=args.night_mode,
            resize=args.resize,
            preview_mode=args.preview,
            auto_chapter_bg=args.chapter_bg,
            auto_chapter_font=args.chapter_font,
            auto_chapter_font_size=args.chapter_font_size,
            auto_chapter_label_mode=args.chapter_label_mode,
            force_chapter_images=args.force_chapter_images,
            progress=print,
        )
    except RuntimeError as exc:
        raise SystemExit(f"Erreur : {exc}") from exc
    print(f"Pack généré : {pack_dir}")

    if args.zip:
        zip_path = zip_pack(pack_dir)
        print(f"Archive prête à importer dans STUdio : {zip_path}")


if __name__ == "__main__":
    main()
