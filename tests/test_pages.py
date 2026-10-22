"""Smoke tests: every page renders without an exception from the committed data."""

import os

import pytest
from streamlit.testing.v1 import AppTest

from src.core import paths
from src.core.signals import ZSCORE_NA_LABEL
from src.modules.ism_manufacturing import config as ism_cfg

PAGES = ["Home.py", "pages/1_Treasury_Yields.py", "pages/2_ISM_Manufacturing.py"]


def _run(page: str) -> AppTest:
    at = AppTest.from_file(os.path.join(paths.ROOT, page), default_timeout=120)
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    return at


def _text(at: AppTest) -> str:
    parts = [c.value for c in at.caption] + [i.value for i in at.info]
    parts += [m.value for m in at.markdown]
    return " ".join(parts)


@pytest.mark.parametrize("page", PAGES)
def test_page_renders(page):
    _run(page)


@pytest.mark.parametrize("page", PAGES)
def test_every_page_shows_as_of_and_source(page):
    captions = " ".join(c.value for c in _run(page).caption)
    assert "As of" in captions
    assert "Source" in captions


@pytest.mark.parametrize("page", ["Home.py", "pages/2_ISM_Manufacturing.py"])
def test_no_sample_or_illustrative_labels(page):
    text = _text(_run(page))
    assert "Sample data" not in text
    assert "Illustrative" not in text and "illustrative" not in text


def test_ism_page_shows_attribution_zscore_and_form():
    at = _run("pages/2_ISM_Manufacturing.py")
    captions = [c.value for c in at.caption]
    assert f"Source: {ism_cfg.SOURCE}" in captions
    assert ism_cfg.SOURCE == (
        "ISM Manufacturing Report On Business, compiled from public monthly releases"
    )
    z = next(m for m in at.metric if m.label == "Z-score vs 10y")
    assert z.value != ZSCORE_NA_LABEL
    float(z.value)
    assert at.get("form"), "manual-entry form should always be available"
