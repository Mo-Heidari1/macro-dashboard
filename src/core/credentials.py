"""
API keys for scripts: the environment variable first, then the same
.streamlit/secrets.toml that Streamlit's st.secrets reads. Keys are never
passed on the command line, printed or logged (engineering rule 7).
Also feature flags (e.g. ENABLE_DATA_ENTRY), read from the environment or a
secrets mapping.
"""

import os
import tomllib
from collections.abc import Mapping

from src.core import paths


class MissingSecretError(RuntimeError):
    """Raised when a required key is in neither the environment nor secrets.toml."""


def get_secret(name: str, secrets_file: str | None = None) -> str:
    """
    Value of secret `name` from os.environ, else from .streamlit/secrets.toml
    (top-level key). Raises MissingSecretError, naming where to set it.
    """
    value = os.environ.get(name, "").strip()
    if value:
        return value
    path = secrets_file or paths.SECRETS_FILE
    if os.path.exists(path):
        # utf-8-sig: tolerate the byte-order mark some Windows editors add
        with open(path, encoding="utf-8-sig") as f:
            value = str(tomllib.loads(f.read()).get(name, "")).strip()
        if value:
            return value
    raise MissingSecretError(
        f"{name} is not set. Export it as an environment variable or add "
        f'{name} = "..." to .streamlit/secrets.toml (git-ignored).'
    )


TRUE_VALUES = {"1", "true", "yes", "on"}


def _truthy(value) -> bool:
    if isinstance(value, bool):
        return value
    return value is not None and str(value).strip().lower() in TRUE_VALUES


def flag_enabled(name: str, secrets: Mapping | None = None) -> bool:
    """
    True when feature flag `name` is set to true in the environment or in
    `secrets` (the page passes st.secrets, keeping this module Streamlit-free).
    Off by default, including when no secrets file exists.
    """
    if _truthy(os.environ.get(name)):
        return True
    if secrets is None:
        return False
    try:
        return _truthy(secrets.get(name))
    except (FileNotFoundError, KeyError):  # no secrets configured
        return False
