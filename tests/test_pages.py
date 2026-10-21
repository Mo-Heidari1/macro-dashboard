"""Smoke tests: every page renders without an exception, on sample and local data."""

import os

import pytest
from streamlit.testing.v1 import AppTest

from src.core import paths

PAGES = ["Home.py", "pages/1_Treasury_Yields.py", "pages/2_ISM_Manufacturing.py"]


def _run(page: str) -> AppTest:
    at = AppTest.from_file(os.path.join(paths.ROOT, page), default_timeout=120)
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    return at


@pytest.mark.parametrize("page", PAGES)
def test_page_renders_on_sample(sample_only, page):
    _run(page)


def test_ism_page_labels_sample_and_disables_form(sample_only):
    at = _run("pages/2_ISM_Manufacturing.py")
    assert any("Sample data" in i.value for i in at.info)
    assert any("Illustrative data" in c.value for c in at.caption)
    assert not at.get("form")


def test_home_labels_sample_pmi(sample_only):
    at = _run("Home.py")
    assert any("Sample data" in c.value for c in at.caption)


@pytest.mark.parametrize("page", PAGES)
def test_page_renders_on_local(page, has_local_ism):
    if not has_local_ism:
        pytest.skip("licensed full ISM history not present")
    at = _run(page)
    assert not any("Sample data" in i.value for i in at.info)
