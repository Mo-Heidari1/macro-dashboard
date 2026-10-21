"""Shared pytest fixtures."""

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.core import paths  # noqa: E402


@pytest.fixture
def sample_only(tmp_path, monkeypatch):
    """Point data/local/ at an empty folder so every loader falls back to data/sample/."""
    monkeypatch.setattr(paths, "DATA_LOCAL", str(tmp_path / "local"))
    return tmp_path


@pytest.fixture
def has_local_ism() -> bool:
    """True when the full (proprietary) ISM history exists in data/local/."""
    return os.path.exists(paths.local_path("ism_history.csv"))
