"""
Every filesystem path the project uses, built relative to this file so the
app runs unchanged on Windows, Linux (Streamlit Community Cloud) or any
other machine.

Data lives in one folder per dataset, plus a local folder:
- data/yields/  Treasury yields history (committed)
- data/ism/     ISM Manufacturing history and sector rankings (committed,
                with attribution)
- data/local/   restricted data and source workbooks (git-ignored)
Each module names its folder in config.py (DATA_FOLDER).
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(ROOT, "data")
DATA_LOCAL = os.path.join(DATA_DIR, "local")
DATA_ISM = os.path.join(DATA_DIR, "ism")
DATA_YIELDS = os.path.join(DATA_DIR, "yields")
SECRETS_FILE = os.path.join(ROOT, ".streamlit", "secrets.toml")  # git-ignored


def local_path(filename: str) -> str:
    """Path of `filename` inside data/local/ (may not exist)."""
    return os.path.join(DATA_LOCAL, filename)


def dataset_dir(folder: str) -> str:
    """A dataset's committed folder, e.g. dataset_dir("ism") -> data/ism/."""
    return os.path.join(DATA_DIR, folder)


def dataset_path(folder: str, filename: str) -> str:
    """Path of `filename` in a dataset's committed folder (may not exist)."""
    return os.path.join(dataset_dir(folder), filename)


def resolve_data_file(
    filename: str, committed_dir: str, local_dir: str | None = None
) -> tuple[str, bool]:
    """
    Return (path, is_committed): the data/local/ copy if it exists (a local
    override), otherwise the copy in `committed_dir`. Raises
    FileNotFoundError if neither exists.
    """
    local_dir = local_dir or DATA_LOCAL
    local = os.path.join(local_dir, filename)
    if os.path.exists(local):
        return local, False
    committed = os.path.join(committed_dir, filename)
    if os.path.exists(committed):
        return committed, True
    raise FileNotFoundError(f"{filename} not found in {local_dir} or {committed_dir}")
