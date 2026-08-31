from __future__ import annotations

import sys
from pathlib import Path


def add_repository_root() -> Path:
    """Make the repository root importable for any standalone script runner."""
    root = Path(__file__).resolve().parents[1]
    value = str(root)
    if value not in sys.path:
        sys.path.insert(0, value)
    return root


REPOSITORY_ROOT = add_repository_root()

__all__ = ["REPOSITORY_ROOT", "add_repository_root"]
