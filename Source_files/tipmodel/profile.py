"""Extract a radial profile r(z) from a tip mask."""
from __future__ import annotations

import numpy as np

from .types import TipProfile


def _orient_apex_up(mask: np.ndarray, apex: str) -> np.ndarray:
    """Rotate/flip so the tip axis is vertical with the apex at the top."""
    if apex == "up":
        return mask
    if apex == "down":
        return mask[::-1]
    if apex == "left":
        return np.rot90(mask, -1)
    if apex == "right":
        return np.rot90(mask, 1)
    raise ValueError(f"apex must be up/down/left/right/auto, got {apex!r}")


def _guess_apex(mask: np.ndarray) -> str:
    """Tip axis is along the mask's longer extent; apex is the narrower end."""
    ys, xs = np.nonzero(mask)
    vertical = np.ptp(ys) >= np.ptp(xs)
    m = mask if vertical else mask.T
    widths = m[m.any(axis=1)].sum(axis=1)
    k = max(len(widths) // 10, 1)
    first_narrow = widths[:k].mean() < widths[-k:].mean()
    if vertical:
        return "up" if first_narrow else "down"
    return "left" if first_narrow else "right"


def extract_profile(
    mask: np.ndarray, metres_per_pixel: float, apex: str = "auto", smooth_window: int = 5
) -> TipProfile:
    """Convert a tip mask to r(z) in metres, apex at z = 0.

    Radius is half the mask width per row. The tip is assumed roughly aligned
    with an image axis (see ``apex``).
    """
    if apex == "auto":
        apex = _guess_apex(mask)
    m = _orient_apex_up(mask, apex)
    m = m[m.any(axis=1)]  # drop empty rows

    # Width per row = last - first foreground pixel + 1, robust to small holes.
    first = np.argmax(m, axis=1)
    last = m.shape[1] - 1 - np.argmax(m[:, ::-1], axis=1)
    radius_px = (last - first + 1) / 2.0

    if smooth_window > 1:
        padded = np.pad(radius_px, smooth_window // 2, mode="edge")
        radius_px = np.convolve(padded, np.ones(smooth_window) / smooth_window, mode="valid")

    z_px = np.arange(len(radius_px)) + 0.5
    return TipProfile(z=z_px * metres_per_pixel, r=radius_px * metres_per_pixel)
