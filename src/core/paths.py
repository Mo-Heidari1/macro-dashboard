"""
Every filesystem path the project uses, built relative to this file so the
app runs unchanged on Windows, Linux (Streamlit Community Cloud) or any
other machine.

Data lives in two folders:
- data/local/   full or proprietary history (git-ignored)
- data/sample/  committed data: full public datasets (Treasury yields, ISM
                compiled from public releases) and samples of restricted data
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(ROOT, "data")
DATA_LOCAL = os.path.join(DATA_DIR, "local")
DATA_SAMPLE = os.path.join(DATA_DIR, "sample")
SECRETS_FILE = os.path.join(ROOT, ".streamlit", "secrets.toml")  # git-ignored


def local_path(filename: str) -> str:
    """Path of `filename` inside data/local/ (may not exist)."""
    return os.path.join(DATA_LOCAL, filename)


def sample_path(filename: str) -> str:
    """Path of `filename` inside data/sample/ (may not exist)."""
    return os.path.join(DATA_SAMPLE, filename)


def resolve_data_file(
    filename: str, local_dir: str | None = None, sample_dir: str | None = None
) -> tuple[str, bool]:
    """
    Return (path, is_sample): the data/local/ copy if it exists, otherwise
    the data/sample/ copy. Raises FileNotFoundError if neither exists.
    """
    local_dir = local_dir or DATA_LOCAL
    sample_dir = sample_dir or DATA_SAMPLE
    local = os.path.join(local_dir, filename)
    if os.path.exists(local):
        return local, False
    sample = os.path.join(sample_dir, filename)
    if os.path.exists(sample):
        return sample, True
    raise FileNotFoundError(f"{filename} not found in {local_dir} or {sample_dir}")
