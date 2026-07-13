from __future__ import annotations

from functools import lru_cache
from pathlib import Path


_VERSION_FILE = Path(__file__).with_name("VERSION")


@lru_cache(maxsize=1)
def get_project_version() -> str:
    version = _VERSION_FILE.read_text(encoding="utf-8").strip()
    if not version:
        raise RuntimeError("VERSION file is empty.")
    return version


PROJECT_VERSION = get_project_version()


__all__ = ["PROJECT_VERSION", "get_project_version"]
