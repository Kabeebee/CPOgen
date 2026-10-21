"""High-level orchestration: image file -> 3D tip model. GUI/CLI call into this."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .imageio import load_greyscale
from .profile import extract_profile
from .revolve import revolve_profile
from .scalebar import find_scale_bar, valid_image_mask
from .segmentation import segment_tip
from .types import Mesh, ScaleBar, TipProfile


@dataclass
class TipModelResult:
    image: np.ndarray
    scale_bar: ScaleBar
    mask: np.ndarray
    profile: TipProfile
    mesh: Mesh


def build_tip_model(
    image_path: str | Path,
    scale_bar_length_m: float,
    apex: str = "auto",
    n_theta: int = 72,
    smooth_sigma: float = 2.0,
) -> TipModelResult:
    image = load_greyscale(image_path)
    bar = find_scale_bar(image, length_m=scale_bar_length_m)
    valid = valid_image_mask(image, bar)
    mask = segment_tip(image, valid, smooth_sigma=smooth_sigma)
    profile = extract_profile(mask, bar.metres_per_pixel, apex=apex)
    mesh = revolve_profile(profile, n_theta=n_theta)
    return TipModelResult(image, bar, mask, profile, mesh)
