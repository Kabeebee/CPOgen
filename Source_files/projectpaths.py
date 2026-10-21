"""Locations of user-facing folders, valid both from source and in a frozen executable."""
from __future__ import annotations

import sys
from pathlib import Path


def project_root() -> Path:
    """Folder holding SEM-images/ and output/: the exe's folder when packaged."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent
