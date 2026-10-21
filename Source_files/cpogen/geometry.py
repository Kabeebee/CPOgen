"""Tip mesh -> CPO2D electrode geometry (r, z polylines in a chosen length unit)."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from tipmodel.types import Mesh, TipProfile

UNITS = {"m": 1.0, "mm": 1e-3, "um": 1e-6, "nm": 1e-9}


@dataclass(frozen=True)
class Electrode:
    """Connected chain of straight segments; ``points`` is (n, 2) of (r, z)."""
    name: str
    points: np.ndarray
    voltage_index: int  # 1-based index into the CPO voltage list


@dataclass(frozen=True)
class CpoGeometry:
    electrodes: list[Electrode]
    unit: str
    voltages_per_index: dict[int, float]


def auto_unit(extent_m: float) -> str:
    """Pick the unit that leaves the largest dimension >= 1."""
    for unit in ("mm", "um", "nm"):
        if extent_m / UNITS[unit] >= 1.0:
            return unit
    return "nm"


def mesh_to_rz(mesh: Mesh) -> np.ndarray:
    """Meridional (r, z) profile in metres from the first generator column of a revolved mesh."""
    r = np.hypot(mesh.X[:, 0], mesh.Y[:, 0])
    return np.column_stack([r, mesh.Z[:, 0]])


def add_shank(
    profile: TipProfile,
    shank_radius_m: float,
    flare_length_m: float,
    shank_length_m: float,
    flare_points: int = 50,
) -> TipProfile:
    """Extend a measured tip profile with a convex flare and cylindrical shank."""
    dimensions = (shank_radius_m, flare_length_m, shank_length_m)
    if not np.isfinite(dimensions).all() or min(dimensions) <= 0:
        raise ValueError("Shank radius, flare length, and shank length must be positive finite lengths.")
    if len(profile.r) < 2 or np.any(np.diff(profile.z) <= 0):
        raise ValueError("Tip profile must contain at least two points with increasing z.")
    if not np.isfinite(profile.z).all() or not np.isfinite(profile.r).all():
        raise ValueError("Tip profile must contain only finite coordinates.")
    if shank_radius_m <= profile.r[-1]:
        raise ValueError("Shank radius must exceed the tip profile's base radius.")
    if flare_points < 2:
        raise ValueError("The flare requires at least two points.")

    z0, r0 = profile.z[-1], profile.r[-1]
    # Concave arc: leaves the tip radius flat and steepens into a sharp join at the shank.
    t = np.linspace(0, 1, flare_points + 1)[1:]
    flare_z = t * flare_length_m
    flare_r = r0 + (shank_radius_m - r0) * t**2
    shank_z = z0 + flare_length_m + shank_length_m
    if not np.isfinite(flare_r).all() or not np.isfinite(shank_z):
        raise ValueError("Shank dimensions are too large to construct a finite profile.")
    return TipProfile(
        z=np.concatenate((profile.z, z0 + flare_z, [shank_z])),
        r=np.concatenate((profile.r, flare_r, [shank_radius_m])),
    )


def simplify(points: np.ndarray, tol: float) -> np.ndarray:
    """Ramer-Douglas-Peucker polyline simplification (iterative)."""
    keep = np.zeros(len(points), bool)
    keep[[0, -1]] = True
    stack = [(0, len(points) - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        a, b = points[i], points[j]
        d = b - a
        n = np.hypot(*d)
        seg = points[i + 1:j] - a
        dist = np.hypot(*seg.T) if n == 0 else np.abs(d[0] * seg[:, 1] - d[1] * seg[:, 0]) / n
        k = int(np.argmax(dist))
        if dist[k] > tol:
            m = i + 1 + k
            keep[m] = True
            stack += [(i, m), (m, j)]
    return points[keep]


def simplify_min_points(points: np.ndarray, tol: float, min_points: int) -> np.ndarray:
    """RDP simplification, tightening the tolerance until at least ``min_points`` remain."""
    out = simplify(points, tol)
    if len(out) >= min(min_points, len(points)):
        return out
    lo, hi = 0.0, tol  # tolerance in [lo, hi]: hi is too coarse, lo keeps everything
    for _ in range(30):
        mid = (lo + hi) / 2
        if len(simplify(points, mid)) >= min_points:
            lo = mid
        else:
            hi = mid
    return simplify(points, lo)


def mesh_to_tip_outline(
    mesh: Mesh,
    tolerance_frac: float = 0.002,
    min_tip_points: int = 150,
    tip_length_m: float | None = None,
) -> np.ndarray:
    """Return the simplified, closed (r, z) tip electrode outline in metres.

    The measured tip (z <= ``tip_length_m``) is simplified against its own radius and keeps at
    least ``min_tip_points`` points; the flare/shank beyond it is simplified separately so the
    large shank radius cannot flatten the tip detail.
    """
    rz = mesh_to_rz(mesh)
    rz = rz[np.argsort(rz[:, 1])]
    rz[0, 0] = 0.0
    rz[:, 1] -= rz[0, 1]
    if tip_length_m is None:
        tip_length_m = rz[-1, 1]
    n_tip = max(2, int(np.searchsorted(rz[:, 1], tip_length_m * (1 + 1e-9), side="right")))
    tip_part, rest = rz[:n_tip], rz[n_tip - 1:]
    tip = simplify_min_points(tip_part, tolerance_frac * tip_part[:, 0].max(), min_tip_points)
    if len(rest) > 2:
        tip = np.vstack([tip, simplify(rest, tolerance_frac * rest[:, 0].max())[1:]])
    return np.vstack([tip, [0.0, tip[-1, 1]]])


def build_geometry(
    mesh: Mesh,
    tip_voltage: float,
    gap_m: float,
    aperture_radius_m: float,
    extractor_outer_radius_m: float,
    extractor_voltage: float = 0.0,
    tolerance_frac: float = 0.002,
    unit: str | None = None,
    min_tip_points: int = 150,
    tip_length_m: float | None = None,
) -> CpoGeometry:
    """Tip electrode (apex at z=0, shank towards +z) plus a flat annular extractor at z=-gap."""
    rz = mesh_to_rz(mesh)
    tip = mesh_to_tip_outline(mesh, tolerance_frac, min_tip_points, tip_length_m)

    ext = np.array([[aperture_radius_m, -gap_m], [extractor_outer_radius_m, -gap_m]])
    unit = unit or auto_unit(max(rz[:, 1].max(), extractor_outer_radius_m, gap_m))
    s = UNITS[unit]
    return CpoGeometry(
        [Electrode("tip", tip / s, 1), Electrode("extractor", ext / s, 2)],
        unit,
        {1: tip_voltage, 2: extractor_voltage},
    )
