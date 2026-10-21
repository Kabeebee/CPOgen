"""Command line: py -m tipmodel IMAGE --bar-length 1e-6 [--apex up]"""
from __future__ import annotations

import argparse

import matplotlib.pyplot as plt

from . import build_tip_model
from .scalebar import parse_length
from .visualize import plot_profile, plot_segmentation, plot_surface


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("image")
    p.add_argument("--bar-length", required=True,
                   help="Physical length printed on the scale bar, e.g. '3um', '500nm' (plain number = metres)")
    p.add_argument("--apex", default="auto", choices=["auto", "up", "down", "left", "right"])
    args = p.parse_args()

    res = build_tip_model(args.image, parse_length(args.bar_length), apex=args.apex)
    print(f"Scale: {res.scale_bar.metres_per_pixel * 1e9:.2f} nm/px; "
          f"tip length {res.profile.z[-1] * 1e6:.2f} um, max radius {res.profile.r.max() * 1e6:.2f} um")

    fig = plt.figure(figsize=(15, 5))
    plot_segmentation(res.image, res.mask, res.scale_bar, fig.add_subplot(1, 3, 1))
    plot_profile(res.profile, fig.add_subplot(1, 3, 2))
    plot_surface(res.mesh, fig.add_subplot(1, 3, 3, projection="3d"))
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
