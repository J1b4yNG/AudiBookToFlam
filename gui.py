#!/usr/bin/env python3
"""Interface graphique (Tkinter) pour générer un pack d'histoire (format STUdio v1)
à partir d'un dossier d'audiobook chapitré."""
from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Optional, Tuple

from storypack.builder import build_pack
from storypack.packaging import zip_pack

DEFAULT_CHAPTER_BG = Path(__file__).resolve().parent / "assets" / "chapter_template" / "bg.png"
DEFAULT_CHAPTER_FONT = Path(__file__).resolve().parent / "assets" / "chapter_template" / "CloisterBlack.ttf"


class StoryPackGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("AudiBookToFlam — Générateur de pack histoire")
        self.resizable(False, False)

        self.log_queue: "queue.Queue[str]" = queue.Queue()
        self.worker: Optional[threading.Thread] = None

        self._build_widgets()
        self.after(100, self._poll_log_queue)

    def _build_widgets(self) -> None:
        pad = {"padx": 8, "pady": 4}
        frm = ttk.Frame(self)
        frm.pack(fill="both", expand=True, padx=10, pady=10)

        row = 0
        ttk.Label(frm, text="Dossier d'entrée (audio + images) :").grid(row=row, column=0, sticky="w", **pad)
        self.input_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.input_var, width=55).grid(row=row, column=1, **pad)
        ttk.Button(frm, text="Parcourir…", command=self._pick_input).grid(row=row, column=2, **pad)
        row += 1

        ttk.Label(frm, text="Dossier de sortie :").grid(row=row, column=0, sticky="w", **pad)
        self.output_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.output_var, width=55).grid(row=row, column=1, **pad)
        ttk.Button(frm, text="Parcourir…", command=self._pick_output).grid(row=row, column=2, **pad)
        row += 1

        ttk.Label(frm, text="Titre de l'histoire :").grid(row=row, column=0, sticky="w", **pad)
        self.title_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.title_var, width=55).grid(row=row, column=1, columnspan=2, sticky="w", **pad)
        row += 1

        ttk.Label(frm, text="Description :").grid(row=row, column=0, sticky="w", **pad)
        self.description_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.description_var, width=55).grid(row=row, column=1, columnspan=2, sticky="w", **pad)
        row += 1

        ttk.Label(frm, text="Image de couverture (optionnel) :").grid(row=row, column=0, sticky="w", **pad)
        self.cover_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.cover_var, width=55).grid(row=row, column=1, **pad)
        ttk.Button(frm, text="Parcourir…", command=self._pick_cover).grid(row=row, column=2, **pad)
        row += 1

        ttk.Label(frm, text="Redimensionner images (ex: 320x240, optionnel) :").grid(row=row, column=0, sticky="w", **pad)
        self.resize_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.resize_var, width=20).grid(row=row, column=1, sticky="w", **pad)
        row += 1

        chapter_gen_frame = ttk.LabelFrame(frm, text="Génération automatique des images de chapitre")
        chapter_gen_frame.grid(row=row, column=0, columnspan=3, sticky="ew", padx=8, pady=6)
        row += 1
        self._build_chapter_gen_widgets(chapter_gen_frame)

        ttk.Label(frm, text="Aperçu audio sur la carte menu :").grid(row=row, column=0, sticky="w", **pad)
        self.preview_var = tk.StringVar(value="silence")
        preview_frame = ttk.Frame(frm)
        preview_frame.grid(row=row, column=1, sticky="w", **pad)
        ttk.Radiobutton(preview_frame, text="Silence (1s)", variable=self.preview_var, value="silence").pack(side="left")
        ttk.Radiobutton(preview_frame, text="Audio complet", variable=self.preview_var, value="full").pack(side="left")
        row += 1

        self.night_mode_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(frm, text="Activer le mode nuit", variable=self.night_mode_var).grid(row=row, column=1, sticky="w", **pad)
        row += 1

        self.zip_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frm, text="Créer aussi un .zip (import direct dans STUdio)", variable=self.zip_var).grid(
            row=row, column=1, sticky="w", **pad
        )
        row += 1

        self.generate_btn = ttk.Button(frm, text="Générer le pack", command=self._on_generate)
        self.generate_btn.grid(row=row, column=0, columnspan=3, pady=10)
        row += 1

        self.progress = ttk.Progressbar(frm, mode="indeterminate")
        self.progress.grid(row=row, column=0, columnspan=3, sticky="ew", **pad)
        row += 1

        self.log_text = tk.Text(frm, height=14, width=76, state="disabled")
        self.log_text.grid(row=row, column=0, columnspan=3, **pad)

    def _build_chapter_gen_widgets(self, frame: ttk.Frame) -> None:
        pad = {"padx": 8, "pady": 3}

        self.auto_chapter_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame, text="Générer les images de chapitre manquantes (texte sur fond)",
            variable=self.auto_chapter_var,
        ).grid(row=0, column=0, columnspan=3, sticky="w", **pad)

        ttk.Label(frame, text="Image de fond :").grid(row=1, column=0, sticky="w", **pad)
        self.chapter_bg_var = tk.StringVar(value=str(DEFAULT_CHAPTER_BG) if DEFAULT_CHAPTER_BG.exists() else "")
        ttk.Entry(frame, textvariable=self.chapter_bg_var, width=45).grid(row=1, column=1, **pad)
        ttk.Button(frame, text="Parcourir…", command=self._pick_chapter_bg).grid(row=1, column=2, **pad)

        ttk.Label(frame, text="Police (.ttf/.otf, optionnel) :").grid(row=2, column=0, sticky="w", **pad)
        self.chapter_font_var = tk.StringVar(value=str(DEFAULT_CHAPTER_FONT) if DEFAULT_CHAPTER_FONT.exists() else "")
        ttk.Entry(frame, textvariable=self.chapter_font_var, width=45).grid(row=2, column=1, **pad)
        ttk.Button(frame, text="Parcourir…", command=self._pick_chapter_font).grid(row=2, column=2, **pad)

        ttk.Label(frame, text="Taille de police :").grid(row=3, column=0, sticky="w", **pad)
        self.chapter_font_size_var = tk.IntVar(value=40)
        ttk.Spinbox(frame, from_=10, to=200, textvariable=self.chapter_font_size_var, width=6).grid(
            row=3, column=1, sticky="w", **pad
        )

        ttk.Label(frame, text="Texte incrusté :").grid(row=4, column=0, sticky="w", **pad)
        self.chapter_label_mode_var = tk.StringVar(value="number")
        label_mode_frame = ttk.Frame(frame)
        label_mode_frame.grid(row=4, column=1, sticky="w", **pad)
        ttk.Radiobutton(label_mode_frame, text="Chapitre N", variable=self.chapter_label_mode_var, value="number").pack(side="left")
        ttk.Radiobutton(label_mode_frame, text="Titre du chapitre", variable=self.chapter_label_mode_var, value="title").pack(side="left")

        self.force_chapter_images_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame, text="Remplacer aussi les images déjà présentes",
            variable=self.force_chapter_images_var,
        ).grid(row=5, column=0, columnspan=3, sticky="w", **pad)

    # -- sélecteurs de fichiers ------------------------------------------------

    def _pick_input(self) -> None:
        path = filedialog.askdirectory(title="Choisir le dossier contenant l'audiobook chapitré")
        if not path:
            return
        self.input_var.set(path)
        if not self.output_var.get():
            self.output_var.set(str(Path(path).parent / f"{Path(path).name}_pack"))
        if not self.title_var.get():
            self.title_var.set(Path(path).name)

    def _pick_output(self) -> None:
        path = filedialog.askdirectory(title="Choisir le dossier de sortie")
        if path:
            self.output_var.set(path)

    def _pick_cover(self) -> None:
        path = filedialog.askopenfilename(
            title="Choisir une image de couverture",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp *.webp")],
        )
        if path:
            self.cover_var.set(path)

    def _pick_chapter_bg(self) -> None:
        path = filedialog.askopenfilename(
            title="Choisir l'image de fond pour les chapitres",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp *.webp")],
        )
        if path:
            self.chapter_bg_var.set(path)

    def _pick_chapter_font(self) -> None:
        path = filedialog.askopenfilename(
            title="Choisir une police",
            filetypes=[("Polices", "*.ttf *.otf")],
        )
        if path:
            self.chapter_font_var.set(path)

    # -- log / progression ------------------------------------------------------

    def _log(self, message: str) -> None:
        self.log_queue.put(message)

    def _poll_log_queue(self) -> None:
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.log_text.configure(state="normal")
                self.log_text.insert("end", message + "\n")
                self.log_text.see("end")
                self.log_text.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(100, self._poll_log_queue)

    def _parse_resize(self) -> Optional[Tuple[int, int]]:
        value = self.resize_var.get().strip()
        if not value:
            return None
        try:
            w, h = value.lower().split("x")
            return int(w), int(h)
        except ValueError as exc:
            raise ValueError("Format de redimensionnement invalide, attendu LARGEURxHAUTEUR (ex: 320x240)") from exc

    # -- génération ---------------------------------------------------------------

    def _on_generate(self) -> None:
        if self.worker and self.worker.is_alive():
            return

        input_dir = self.input_var.get().strip()
        output_dir = self.output_var.get().strip()
        title = self.title_var.get().strip()

        if not input_dir or not Path(input_dir).is_dir():
            messagebox.showerror("Erreur", "Choisis un dossier d'entrée valide.")
            return
        if not output_dir:
            messagebox.showerror("Erreur", "Choisis un dossier de sortie.")
            return
        if not title:
            messagebox.showerror("Erreur", "Indique un titre pour l'histoire.")
            return

        try:
            resize = self._parse_resize()
        except ValueError as exc:
            messagebox.showerror("Erreur", str(exc))
            return

        cover = self.cover_var.get().strip()
        cover_path = Path(cover) if cover else None

        auto_chapter_bg: Optional[Path] = None
        if self.auto_chapter_var.get():
            chapter_bg = self.chapter_bg_var.get().strip()
            if not chapter_bg or not Path(chapter_bg).is_file():
                messagebox.showerror("Erreur", "Choisis une image de fond valide pour la génération des images de chapitre.")
                return
            auto_chapter_bg = Path(chapter_bg)

        chapter_font = self.chapter_font_var.get().strip()
        auto_chapter_font = Path(chapter_font) if chapter_font else None

        self.generate_btn.configure(state="disabled")
        self.progress.start(12)
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

        self.worker = threading.Thread(
            target=self._run_build,
            args=(
                Path(input_dir), Path(output_dir), title,
                self.description_var.get().strip(), cover_path,
                self.night_mode_var.get(), resize, self.preview_var.get(),
                self.zip_var.get(),
                auto_chapter_bg, auto_chapter_font, self.chapter_font_size_var.get(),
                self.chapter_label_mode_var.get(), self.force_chapter_images_var.get(),
            ),
            daemon=True,
        )
        self.worker.start()

    def _run_build(
        self,
        input_dir: Path,
        output_dir: Path,
        title: str,
        description: str,
        cover: Optional[Path],
        night_mode: bool,
        resize: Optional[Tuple[int, int]],
        preview_mode: str,
        make_zip: bool,
        auto_chapter_bg: Optional[Path],
        auto_chapter_font: Optional[Path],
        auto_chapter_font_size: int,
        auto_chapter_label_mode: str,
        force_chapter_images: bool,
    ) -> None:
        try:
            pack_dir = build_pack(
                input_dir=input_dir,
                output_dir=output_dir,
                title=title,
                description=description,
                cover_image=cover,
                night_mode=night_mode,
                resize=resize,
                preview_mode=preview_mode,
                auto_chapter_bg=auto_chapter_bg,
                auto_chapter_font=auto_chapter_font,
                auto_chapter_font_size=auto_chapter_font_size,
                auto_chapter_label_mode=auto_chapter_label_mode,
                force_chapter_images=force_chapter_images,
                progress=self._log,
            )
            self._log(f"Pack généré : {pack_dir}")
            if make_zip:
                zip_path = zip_pack(pack_dir)
                self._log(f"Archive prête à importer dans STUdio : {zip_path}")
            self._log("Terminé.")
        except Exception as exc:  # noqa: BLE001 - affiché à l'utilisateur, pas avalé silencieusement
            self._log(f"Erreur : {exc}")
        finally:
            self.after(0, self._on_build_finished)

    def _on_build_finished(self) -> None:
        self.progress.stop()
        self.generate_btn.configure(state="normal")


def main() -> None:
    app = StoryPackGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
