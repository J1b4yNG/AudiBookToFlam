# AudiBookToFlam

Génère un pack "histoire" (compatible [STUdio](https://github.com/marian-m12l/studio)) à partir
d'un dossier contenant un audiobook chapitré (mp3 ou mka) et une image par chapitre.

Le résultat est un dossier `story.json` + `thumbnail.png` + `assets/` — le même format que celui
utilisé par la bibliothèque de STUdio (ou son export/import en `.zip`). L'export final vers ta
boîte à histoires (Lunii, etc.) se fait ensuite depuis l'app STUdio elle-même, qui gère le format
binaire propre à chaque device.

## Structure générée

- Écran de couverture → menu de sélection des chapitres, navigable à la molette (`wheel`)
- Chaque chapitre : une "carte" avec son image, puis OK lance la lecture complète de l'audio
- À la fin d'un chapitre : enchaînement automatique sur la carte du chapitre suivant (bouclage sur
  le premier chapitre après le dernier)
- Bouton Home : retour à la carte du chapitre en cours depuis la lecture, ou à l'écran d'intro
  depuis le menu

## Prérequis

- Python 3.10+
- [ffmpeg / ffprobe](https://ffmpeg.org/download.html) installés et dans le `PATH`
  (nécessaires pour convertir/ré-encoder l'audio en `.mp3`, mesurer la durée des pistes, et générer
  les courts silences utilisés comme audio de remplissage)
- `pip install -r requirements.txt`

## Organisation du dossier d'entrée

Un fichier audio par chapitre, avec si possible une image de même nom :

```
MonLivre/
  01 - Chapitre 1.mp3
  01 - Chapitre 1.jpg
  02 - Chapitre 2.mp3
  02 - Chapitre 2.jpg
  ...
```

- Les fichiers sont triés dans l'ordre naturel des noms (`01`, `02`, ... `10`, `11`).
- Le titre du chapitre est déduit du nom de fichier (préfixe numérique retiré).
- Si une image ne correspond pas par son nom, l'appariement se fait par position (n-ième audio ↔
  n-ième image).
- Formats audio acceptés : `.mp3`, `.mka`, `.m4a`, `.ogg`, `.wav`, `.flac`, `.aac` (tout ce qui
  n'est pas déjà `.mp3` est converti via ffmpeg).
- Formats image acceptés : `.jpg`, `.jpeg`, `.png`, `.bmp`, `.webp` (converties en `.png`).
- Les images sont optionnelles : les chapitres sans image peuvent être générés automatiquement
  (voir *Génération automatique des images de chapitre* ci-dessous).

## Utilisation en ligne de commande

```bash
python build_story_pack.py \
  --input "D:\Livres\MonLivre" \
  --output "out\MonLivre" \
  --title "Mon Livre - Titre" \
  --zip
```

Options utiles :

- `--cover chemin/vers/image.jpg` : image de couverture spécifique (sinon l'image du 1er chapitre est réutilisée)
- `--resize 320x240` : redimensionne toutes les images (utile pour réduire la taille du pack)
- `--preview full` : joue l'audio complet du chapitre dès la carte menu au lieu d'un silence
- `--night-mode` : active le mode nuit sur le pack
- `--zip` : produit en plus `out/MonLivre.zip`, prêt à importer directement dans STUdio
  (menu *Ma bibliothèque* → *Importer un pack depuis un dossier/zip*)

## Génération automatique des images de chapitre

Si un chapitre n'a pas d'image associée (ou pour uniformiser tout le pack), une image "Chapitre N"
(ou le titre du chapitre) peut être incrustée automatiquement sur une image de fond commune —
texte centré, ombre portée, retour à la ligne et réduction de police automatiques si le texte est
trop long pour tenir dans le cadre. C'est repris de l'outil `Chapitre/main.py`, intégré ici dans
[storypack/chapter_images.py](storypack/chapter_images.py).

Deux assets d'exemple sont fournis dans `assets/chapter_template/` (`bg.png` + `CloisterBlack.ttf`),
utilisés par défaut par la GUI — libre à toi de les remplacer par tes propres fond/police.

En CLI :

```bash
python build_story_pack.py \
  --input "D:\Livres\MonLivre" --output "out\MonLivre" --title "Mon titre" \
  --chapter-bg "assets\chapter_template\bg.png" \
  --chapter-font "assets\chapter_template\CloisterBlack.ttf" \
  --chapter-label-mode title
```

- `--chapter-bg` : active la génération auto et fixe l'image de fond à utiliser
- `--chapter-font` : police `.ttf`/`.otf` (optionnel, sinon Georgia ou police système par défaut)
- `--chapter-font-size` : taille de police de départ (défaut : 40, réduite automatiquement si besoin)
- `--chapter-label-mode` : `number` → "Chapitre N" (défaut), `title` → titre du chapitre
- `--force-chapter-images` : régénère aussi les images des chapitres qui en ont déjà une

Dans la GUI, ces mêmes options sont regroupées dans le cadre *Génération automatique des images de
chapitre*.

## Interface graphique

Une alternative avec fenêtre (Tkinter, inclus avec Python — aucune dépendance en plus) :

```bash
python gui.py
```

Renseigne le dossier d'entrée, le dossier de sortie, le titre, puis clique sur *Générer le pack*.
La génération tourne dans un thread séparé (la fenêtre ne se fige pas) et le journal de
progression s'affiche en direct dans la zone de log en bas de la fenêtre.

## Limites connues

- L'histoire générée est un simple menu de chapitres avec molette, sans embranchements narratifs.
- Le pack `.zip` produit est au format "projet STUdio" (assets en `.mp3`/`.png`) ; c'est STUdio (ou
  un outil compatible, ex: [Lunii.QT](https://github.com/o-daneel/Lunii.QT)) qui se charge de le
  convertir au format binaire spécifique du device au moment de l'export/flash.

## Nettoyage systématique des tags audio

Chaque fichier audio est **toujours** ré-encodé via ffmpeg (même les `.mp3` déjà valides), tags
ID3 et pochette embarquée retirés. Certains outils d'import (ex: Lunii.QT) relisent chaque mp3 du
pack avec `mutagen` pour nettoyer ses tags avant l'envoi sur le device ; un ID3v2 mal formé dans le
fichier source (fréquent sur des mp3 issus de rippers d'audiobooks avec pochette embarquée) fait
alors échouer l'import entier avec `mutagen.mp3.HeaderNotFoundError: can't sync to MPEG frame`.
Repartir d'un flux MPEG propre à chaque fois évite ce problème, au prix d'un temps de génération un
peu plus long sur de gros audiobooks déjà en mp3.
