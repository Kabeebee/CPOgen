"""Separate the tip from the background."""
from __future__ import annotations

import numpy as np
from scipy import ndimage


def otsu_threshold(values: np.ndarray, bins: int = 256) -> float:
    hist, edges = np.histogram(values, bins=bins)
    centres = (edges[:-1] + edges[1:]) / 2
    w0 = np.cumsum(hist)
    w1 = w0[-1] - w0
    m0 = np.cumsum(hist * centres) / np.maximum(w0, 1)
    m1 = (np.sum(hist * centres) - np.cumsum(hist * centres)) / np.maximum(w1, 1)
    return float(centres[np.argmax(w0 * w1 * (m0 - m1) ** 2)])


def segment_tip(image: np.ndarray, valid: np.ndarray, smooth_sigma: float = 2.0) -> np.ndarray:
    """Return a boolean mask of the tip (largest connected object, holes filled).

    Polarity is chosen automatically: the image border is assumed to be background.
    """
    smooth = ndimage.gaussian_filter(image, smooth_sigma)
    mask = smooth > otsu_threshold(smooth[valid])
    top = mask[:valid.any(axis=1).nonzero()[0][-1] + 1]  # exclude masked footer
    border = np.concatenate([top[0], top[:, 0], top[:, -1]])
    if border.mean() > 0.5:  # bright background -> invert
        mask = ~mask
    mask &= valid
    mask = ndimage.binary_opening(mask, iterations=2)
    labels, n = ndimage.label(mask)
    if n == 0:
        raise RuntimeError("No tip found: segmentation produced an empty mask.")
    sizes = ndimage.sum(mask, labels, range(1, n + 1))
    return ndimage.binary_fill_holes(labels == (np.argmax(sizes) + 1))
