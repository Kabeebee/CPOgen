"""Plain data containers passed between pipeline stages (GUI-friendly, no logic)."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ScaleBar:
    """Detected scale bar: pixel bounding box plus its real-world length."""
    x0: int
    x1: int  # exclusive
    y0: int
    y1: int  # exclusive
    length_px: float
    length_m: float | None = None

    @property
    def metres_per_pixel(self) -> float:
        if self.length_m is None:
            raise ValueError("Scale bar physical length unknown; pass it explicitly.")
        return self.length_m / self.length_px


@dataclass(frozen=True)
class TipProfile:
    """Radius r(z) of a cylindrically symmetric tip, in metres.

    z runs along the axis from the apex (z = 0) towards the shank (increasing z).
    """
    z: np.ndarray
    r: np.ndarray


@dataclass(frozen=True)
class Mesh:
    """Surface of revolution as coordinate grids X, Y, Z of shape (nz, n_theta)."""
    X: np.ndarray
    Y: np.ndarray
    Z: np.ndarray
