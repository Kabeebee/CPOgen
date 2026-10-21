"""Revolve a 2D profile about the z axis to form a 3D surface."""
from __future__ import annotations

import numpy as np

from .types import Mesh, TipProfile


def revolve_profile(profile: TipProfile, n_theta: int = 72, full: bool = True) -> Mesh:
    """Surface of revolution of r(z) about the z axis.

    ``full=False`` sweeps only 270 degrees, leaving a cut-away wedge so the
    shape is easier to inspect.
    """
    sweep = 2 * np.pi if full else 1.5 * np.pi
    theta = np.linspace(0, sweep, n_theta)
    X = profile.r[:, None] * np.cos(theta)[None, :]
    Y = profile.r[:, None] * np.sin(theta)[None, :]
    Z = np.repeat(profile.z[:, None], n_theta, axis=1)
    return Mesh(X, Y, Z)
