"""Image loading."""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from projectpaths import project_root

# Project root is the parent of this package; images live in <root>/SEM-images.
IMAGE_DIR = project_root() / "SEM-images"


def resolve_image_path(name: str | Path) -> Path:
    """Locate an image inside SEM-images (an absolute path is used as given)."""
    path = Path(name)
    candidate = path if path.is_absolute() else IMAGE_DIR / path
    if not candidate.is_file():
        raise FileNotFoundError(f"Image not found: {candidate}")
    return candidate


def load_greyscale(name: str | Path) -> np.ndarray:
    """Load an image from SEM-images as a 2D float array scaled to [0, 1]."""
    with Image.open(resolve_image_path(name)) as img:
        grey = img.convert("I;16" if img.mode.startswith("I;16") else "L")
        arr = np.asarray(grey, dtype=float)
    peak = arr.max()
    return arr / peak if peak > 0 else arr
