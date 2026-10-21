"""Tkinter front end: pick SEM image -> tip model -> enter voltages -> export CPO2D .DAT."""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from PIL import Image

from projectpaths import project_root
from tipmodel import TipModelResult, build_tip_model
from tipmodel.imageio import resolve_image_path
from tipmodel.revolve import revolve_profile
from tipmodel.scalebar import parse_length
from tipmodel.types import TipProfile

from .geometry import add_shank, build_geometry, mesh_to_tip_outline
from .writer import write_dat


class App(tk.Tk):
    FIELDS = [
        ("image", "Image", ""),
        ("bar", "Scale bar length (e.g. 1um)", "1um"),
        ("volts", "Tip voltage (V)", "1000"),
        ("ext_v", "Extractor voltage (V)", "0"),
        ("gap", "Tip-extractor gap (e.g. 500um)", "500um"),
        ("aperture", "Extractor aperture radius", "250um"),
        ("outer", "Extractor outer radius", "1mm"),
        ("min_pts", "Min. tip profile points", "150"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.title("SEM tip -> CPO2D input")
        self.result: TipModelResult | None = None
        self.vars = {k: tk.StringVar(value=d) for k, _, d in self.FIELDS}
        self.apex = tk.StringVar(value="auto")
        self.shank_radius = tk.StringVar(value="")
        self.flare_length = tk.StringVar(value="20 um")
        self.shank_length = tk.StringVar(value="100 um")

        form = ttk.Frame(self, padding=8)
        form.grid(row=0, column=0, sticky="nw")
        for i, (k, label, _) in enumerate(self.FIELDS):
            ttk.Label(form, text=label).grid(row=i, column=0, sticky="w")
            entry = ttk.Entry(form, textvariable=self.vars[k], width=34)
            entry.grid(row=i, column=1, pady=2)
            if k == "image":
                entry.bind("<Return>", lambda _: self._update_image_preview(show_errors=True))
                entry.bind("<FocusOut>", lambda _: self._update_image_preview(show_errors=True))
        ttk.Button(form, text="Browse...", command=self.browse).grid(row=0, column=2, padx=4)
        n = len(self.FIELDS)
        ttk.Label(form, text="Apex direction").grid(row=n, column=0, sticky="w")
        ttk.Combobox(form, textvariable=self.apex, state="readonly", width=10,
                     values=["auto", "up", "down", "left", "right"]).grid(row=n, column=1, sticky="w")
        ttk.Button(form, text="Process image", command=self.process).grid(row=n + 1, column=0, pady=8)
        ttk.Button(form, text="Export CPO .DAT...", command=self.export).grid(row=n + 1, column=1, sticky="w")
        self.status = ttk.Label(form, text="Select an image.", wraplength=380)
        self.status.grid(row=n + 2, column=0, columnspan=3, sticky="w")

        shank_frame = ttk.LabelFrame(form, text="Shank and flare", padding=6)
        shank_frame.grid(row=n + 3, column=0, columnspan=3, pady=(8, 0), sticky="ew")
        for row, (label, variable) in enumerate((
            ("Shank radius (e.g. 10 um)", self.shank_radius),
            ("Tapered flare length", self.flare_length),
            ("Cylindrical shank length", self.shank_length),
        )):
            ttk.Label(shank_frame, text=label).grid(row=row, column=0, sticky="w")
            ttk.Entry(shank_frame, textvariable=variable, width=20).grid(
                row=row, column=1, padx=(8, 0), pady=2, sticky="ew")
            variable.trace_add("write", self._refresh_profile_preview)

        previews = ttk.Frame(self, padding=8)
        previews.grid(row=0, column=1, sticky="nsew")
        image_frame = ttk.LabelFrame(previews, text="Imported image and detected edge", padding=6)
        image_frame.grid(row=0, column=0, pady=(0, 8), sticky="nsew")
        self.image_fig = Figure(figsize=(5, 3.5))
        self.image_ax = self.image_fig.add_subplot(111)
        self.image_ax.text(0.5, 0.5, "No image selected", ha="center", va="center",
                           transform=self.image_ax.transAxes)
        self.image_ax.axis("off")
        self.image_canvas = FigureCanvasTkAgg(self.image_fig, master=image_frame)
        self.image_canvas.get_tk_widget().grid(row=0, column=0)

        profile_frame = ttk.LabelFrame(previews, text="Constructed tip outline", padding=6)
        profile_frame.grid(row=1, column=0, sticky="nsew")
        self.profile_fig = Figure(figsize=(5, 3.5))
        self.profile_ax = self.profile_fig.add_subplot(111)
        self.profile_canvas = FigureCanvasTkAgg(self.profile_fig, master=profile_frame)
        self.profile_canvas.get_tk_widget().grid(row=0, column=0)
        self._refresh_profile_preview()

        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        previews.columnconfigure(0, weight=1)
        previews.rowconfigure(0, weight=1)
        previews.rowconfigure(1, weight=1)

    def browse(self) -> None:
        sem_dir = project_root() / "SEM-Images"
        path = filedialog.askopenfilename(
            initialdir=sem_dir / "test images" if (sem_dir / "test images").is_dir() else sem_dir,
            filetypes=[("Images", "*.jpg *.jpeg *.png *.tif *.tiff *.bmp"), ("All", "*.*")])
        if path:
            self.vars["image"].set(path)
            self._update_image_preview(show_errors=True)

    def _update_image_preview(self, show_errors: bool = False, mask: np.ndarray | None = None) -> None:
        path = self.vars["image"].get().strip()
        self.image_ax.clear()
        if not path:
            self.image_ax.text(0.5, 0.5, "No image selected", ha="center", va="center",
                               transform=self.image_ax.transAxes)
            self.image_ax.axis("off")
            self.image_canvas.draw()
            return
        try:
            image_path = resolve_image_path(path)
        except FileNotFoundError:
            self.image_ax.text(0.5, 0.5, "Image not found", ha="center", va="center",
                               transform=self.image_ax.transAxes)
            self.image_ax.axis("off")
            self.image_canvas.draw()
            return
        try:
            with Image.open(image_path) as image:
                image.thumbnail((640, 480))
                preview = image.convert("RGB")
        except OSError as exc:
            self.image_ax.text(0.5, 0.5, "Image could not be previewed", ha="center", va="center",
                               transform=self.image_ax.transAxes)
            self.image_ax.axis("off")
            self.image_canvas.draw()
            if show_errors:
                messagebox.showerror("Image preview failed", str(exc))
            return
        self.image_ax.imshow(np.asarray(preview))
        if mask is not None:
            resized_mask = Image.fromarray(mask.astype(np.uint8) * 255).resize(
                preview.size, Image.Resampling.NEAREST)
            self.image_ax.contour(np.asarray(resized_mask), levels=[127.5], colors="red", linewidths=1)
        self.image_ax.axis("off")
        self.image_fig.tight_layout(pad=0)
        self.image_canvas.draw()

    def _num(self, key: str) -> float:
        text = self.vars[key].get().strip()
        try:
            return float(text)
        except ValueError:
            return parse_length(text)

    def _min_points(self) -> int:
        try:
            return max(2, int(float(self.vars["min_pts"].get())))
        except ValueError:
            raise ValueError("Min. tip profile points must be a number.")

    def _tip_length(self) -> float:
        p = self.result.profile
        return float(p.z[-1] - p.z[0])

    def process(self) -> None:
        try:
            result = build_tip_model(
                self.vars["image"].get(), parse_length(self.vars["bar"].get()), apex=self.apex.get())
        except Exception as e:  # surface any pipeline failure to the user
            messagebox.showerror("Processing failed", str(e))
            return
        self.result = result
        p = result.profile
        self._update_image_preview(mask=result.mask)
        self._refresh_profile_preview()
        self.status.config(text=f"Tip length {p.z[-1] * 1e6:.2f} um, max radius {p.r.max() * 1e6:.2f} um.")

    def _constructed_profile(self) -> TipProfile:
        if self.result is None:
            raise ValueError("Process an image before constructing the tip outline.")
        radius = self.shank_radius.get().strip()
        if not radius:
            return self.result.profile
        return add_shank(
            self.result.profile,
            parse_length(radius),
            parse_length(self.flare_length.get()),
            parse_length(self.shank_length.get()),
        )

    def _refresh_profile_preview(self, *_) -> None:
        self.profile_ax.clear()
        if self.result is None:
            self.profile_ax.text(0.5, 0.5, "Process an image to preview the tip outline",
                                 ha="center", va="center", transform=self.profile_ax.transAxes)
            self.profile_ax.axis("off")
            self.profile_canvas.draw()
            return
        note = ""
        try:
            profile = self._constructed_profile()
            if not self.shank_radius.get().strip():
                note = "Enter a shank radius to add the flare and shank."
        except ValueError as exc:  # still show the bare tip so the preview is never empty
            profile = self.result.profile
            note = f"Flare/shank not added: {exc}"
        # Same outline build_geometry writes to the DAT file (tip -> flare -> shank -> axis).
        outline = mesh_to_tip_outline(revolve_profile(profile), min_tip_points=self._min_points(),
                                      tip_length_m=self._tip_length()) * 1e6
        loop = np.vstack([outline, outline[:1]])
        self.profile_ax.plot(loop[:, 0], loop[:, 1], "b-o", markersize=3, linewidth=1.2)
        self.profile_ax.plot(loop[-2:, 0], loop[-2:, 1], "b--", linewidth=1)  # closing axis segment
        if note:
            self.profile_ax.set_title(note, fontsize=8, color="red", wrap=True)
        self.profile_ax.set_xlabel("r (um)")
        self.profile_ax.set_ylabel("z (um), apex at 0")
        self.profile_ax.set_aspect("equal")
        self.profile_ax.invert_yaxis()
        self.profile_ax.grid(True, alpha=0.25)
        self.profile_fig.tight_layout()
        self.profile_canvas.draw()

    def export(self) -> None:
        if self.result is None:
            messagebox.showinfo("No model", "Process an image first.")
            return
        try:
            profile = self._constructed_profile()
            mesh = revolve_profile(profile) if profile is not self.result.profile else self.result.mesh
            geo = build_geometry(
                mesh, self._num("volts"), self._num("gap"), self._num("aperture"),
                self._num("outer"), self._num("ext_v"),
                min_tip_points=self._min_points(), tip_length_m=self._tip_length())
            a, b = geo.electrodes[1].points[:, 0]
            if a >= b:
                raise ValueError("Extractor outer radius must exceed aperture radius.")
        except Exception as e:
            messagebox.showerror("Invalid input", str(e))
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".dat", initialfile="tip.dat", filetypes=[("CPO data", "*.dat")])
        if path:
            write_dat(path, geo)
            self.status.config(text=f"Saved {path} (lengths in {geo.unit}).")


def main() -> None:
    App().mainloop()
