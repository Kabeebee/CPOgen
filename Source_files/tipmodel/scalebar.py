"""Locate the scale bar in the bottom-right corner of an SEM image.

The bar is drawn as a horizontal line with a short vertical end cap at each
end and the length label (e.g. "3 um") sitting in a gap in the middle. The bar
length is the distance between the two end-cap centres.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

from .types import ScaleBar

_MIN_CAP_HEIGHT = 8      # px
_MAX_CAP_WIDTH = 6       # px
_MIN_CAP_ASPECT = 3.0    # height / width
_MIN_LINE_FILL = 0.5     # bright fraction of the connecting line between caps


def _cap_candidates(mask: np.ndarray) -> list[tuple[slice, slice, float]]:
    """Thin, tall bright components: (row slice, col slice, centroid x)."""
    labels, _ = ndimage.label(mask)
    caps = []
    for idx, sl in enumerate(ndimage.find_objects(labels), start=1):
        h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if h >= _MIN_CAP_HEIGHT and w <= _MAX_CAP_WIDTH and h / w >= _MIN_CAP_ASPECT:
            cx = ndimage.center_of_mass(labels[sl] == idx)[1] + sl[1].start
            caps.append((sl[0], sl[1], cx))
    return caps


def _line_fill(mask: np.ndarray, left: tuple, right: tuple) -> float:
    """Best bright fraction over rows spanned by both caps, between the caps."""
    rows = range(max(left[0].start, right[0].start), min(left[0].stop, right[0].stop))
    x0, x1 = left[1].stop, right[1].start
    if x1 <= x0:
        return 0.0
    return max((mask[r, x0:x1].mean() for r in rows), default=0.0)


def find_scale_bar(
    image: np.ndarray,
    length_m: float | None = None,
    search_fraction: tuple[float, float] = (0.25, 0.45),
    bright_threshold: float = 0.8,
) -> ScaleBar:
    """Find the scale bar and return its pixel geometry.

    ``search_fraction`` is the (height, width) fraction of the bottom-right
    corner searched. The bar's physical length is printed in the image; pass it
    as ``length_m`` (see ``parse_length``).
    """
    h, w = image.shape
    y_off = int(h * (1 - search_fraction[0]))
    x_off = int(w * (1 - search_fraction[1]))
    mask = image[y_off:, x_off:] >= bright_threshold * image.max()

    # A vertical opening removes the horizontal line, isolating the end caps.
    vertical = ndimage.binary_opening(mask, structure=np.ones((_MIN_CAP_HEIGHT, 1)))
    caps = _cap_candidates(vertical)
    best = None
    for i, left in enumerate(caps):
        for right in caps[i + 1:]:
            same_rows = abs(left[0].start - right[0].start) <= 1 and abs(left[0].stop - right[0].stop) <= 1
            if same_rows and _line_fill(mask, left, right) >= _MIN_LINE_FILL:
                length = right[2] - left[2]
                if best is None or length > best[0]:
                    best = (length, left, right)
    if best is None:
        raise RuntimeError("No scale bar (line with two end caps) found in the bottom-right region.")

    length, left, right = best
    return ScaleBar(
        x0=x_off + left[1].start, x1=x_off + right[1].stop,
        y0=y_off + min(left[0].start, right[0].start),
        y1=y_off + max(left[0].stop, right[0].stop),
        length_px=float(length), length_m=length_m,
    )


def parse_length(text: str) -> float:
    """Convert a label such as '3 um', '500nm' or '2 µm' to metres."""
    units = {"nm": 1e-9, "um": 1e-6, "µm": 1e-6, "μm": 1e-6, "mm": 1e-3, "m": 1.0}
    t = text.strip().lower().replace(" ", "")
    for suffix in sorted(units, key=len, reverse=True):
        if t.endswith(suffix):
            return float(t[: -len(suffix)]) * units[suffix]
    return float(t)  # plain number: metres


def valid_image_mask(image: np.ndarray, bar: ScaleBar, pad: int = 10) -> np.ndarray:
    """Boolean mask, True where pixels are real sample image.

    SEM images carry a data strip along the bottom; everything below the
    bar's top edge (minus ``pad``) is excluded.
    """
    valid = np.ones(image.shape, dtype=bool)
    valid[max(bar.y0 - pad, 0):, :] = False
    return valid
