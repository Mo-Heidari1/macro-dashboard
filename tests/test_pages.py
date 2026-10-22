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


def test_ism_page_shows_attribution_and_zscore():
    at = _run("pages/2_ISM_Manufacturing.py")
    assert f"Source: {ism_cfg.SOURCE}" in [c.value for c in at.caption]
    z = next(m for m in at.metric if m.label == "Z-score vs 10y")
    assert z.value != ZSCORE_NA_LABEL
    float(z.value)


def _ism_page(monkeypatch, env=None, secret=None) -> AppTest:
    monkeypatch.delenv(ism_cfg.DATA_ENTRY_FLAG, raising=False)
    if env is not None:
        monkeypatch.setenv(ism_cfg.DATA_ENTRY_FLAG, env)
    at = AppTest.from_file(
        os.path.join(paths.ROOT, "pages/2_ISM_Manufacturing.py"), default_timeout=120
    )
    if secret is not None:
        at.secrets[ism_cfg.DATA_ENTRY_FLAG] = secret
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    return at


def test_data_entry_form_hidden_by_default(monkeypatch):
    at = _ism_page(monkeypatch)
    assert not at.get("form")
    assert "Add This Month's Data" not in [t.label for t in at.tabs]


@pytest.mark.parametrize("env, secret", [("true", None), (None, True), ("1", None)])
def test_data_entry_form_shown_when_flag_set(monkeypatch, env, secret):
    at = _ism_page(monkeypatch, env=env, secret=secret)
    assert at.get("form")
    assert "Add This Month's Data" in [t.label for t in at.tabs]


def test_data_entry_flag_false_keeps_form_hidden(monkeypatch):
    at = _ism_page(monkeypatch, env="false", secret=False)
    assert not at.get("form")


def test_ism_attribution_is_exact():
    expected = (
        "Source: ISM Manufacturing Report On Business (Institute for Supply "
        "Management). 1948\u2013Sep 2026: ISM monthly releases (ismworld.org), with "
        "historical data via Investing.com and Quandl."
    )
    at = _run("pages/2_ISM_Manufacturing.py")
    assert expected in [c.value for c in at.caption]
    for doc in ("README.md", "CLAUDE.md", os.path.join("data", "README.md")):
        with open(os.path.join(paths.ROOT, doc), encoding="utf-8") as f:
            text = f.read()
        assert expected in text, doc
        assert "compiled from public" not in text, doc
