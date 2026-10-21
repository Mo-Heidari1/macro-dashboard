"""requirements.txt pins exact versions, and the test environment matches them."""

import importlib.metadata
import os
import sys

import pytest

from src.core import paths


def _pins() -> dict[str, str]:
    pins = {}
    with open(os.path.join(paths.ROOT, "requirements.txt"), encoding="utf-8") as f:
        for line in f:
            line = line.split("#")[0].strip()
            if line:
                assert "==" in line, f"unpinned requirement: {line}"
                name, version = line.split("==")
                pins[name.strip()] = version.strip()
    return pins


def test_every_requirement_is_pinned():
    assert len(_pins()) >= 8


def test_python_is_3_12():
    assert sys.version_info[:2] == (3, 12)


@pytest.mark.parametrize("name, version", sorted(_pins().items()))
def test_installed_version_matches_pin(name, version):
    assert importlib.metadata.version(name) == version
