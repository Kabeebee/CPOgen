"""Matplotlib views. Each function takes an optional Axes so a GUI can embed them."""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.patches import Rectangle

from .types import Mesh, ScaleBar, TipProfile

_UM = 1e6  # metres -> micrometres


def plot_segmentation(image: np.ndarray, mask: np.ndarray, bar: ScaleBar, ax: Axes | None = None) -> Axes:
    ax = ax or plt.subplots()[1]
    ax.imshow(image, cmap="gray")
    ax.contour(mask, levels=[0.5], colors="r", linewidths=1)
    ax.add_patch(Rectangle((bar.x0, bar.y0), bar.x1 - bar.x0, bar.y1 - bar.y0,
                           fill=False, edgecolor="c"))
    ax.set_title("Segmentation and scale bar")
    return ax


def plot_profile(profile: TipProfile, ax: Axes | None = None) -> Axes:
    ax = ax or plt.subplots()[1]
    ax.plot(profile.r * _UM, profile.z * _UM, "b")
    ax.plot(-profile.r * _UM, profile.z * _UM, "b")
    ax.invert_yaxis()
    ax.set_aspect("equal")
    ax.set_xlabel("r (µm)")
    ax.set_ylabel("z from apex (µm)")
    ax.set_title("Extracted profile")
    return ax


def plot_surface(mesh: Mesh, ax: Axes | None = None) -> Axes:
    ax = ax or plt.figure().add_subplot(projection="3d")
    ax.plot_surface(mesh.X * _UM, mesh.Y * _UM, mesh.Z * _UM, cmap="viridis", linewidth=0)
    ax.invert_zaxis()  # apex at the top
    ax.set_box_aspect((np.ptp(mesh.X), np.ptp(mesh.Y), np.ptp(mesh.Z)))
    ax.set_xlabel("x (µm)")
    ax.set_ylabel("y (µm)")
    ax.set_zlabel("z (µm)")
    ax.set_title("3D tip model")
    for axis in (ax.xaxis, ax.yaxis):
        axis.set_major_locator(plt.MaxNLocator(3))  # few ticks: the tip is thin, so labels collide
    return ax
