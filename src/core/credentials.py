"""
API keys for scripts: the environment variable first, then the same
.streamlit/secrets.toml that Streamlit's st.secrets reads. Keys are never
passed on the command line, printed or logged (engineering rule 7).
"""

import os
import tomllib

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
