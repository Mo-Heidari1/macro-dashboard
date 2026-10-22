"""Engineering rules 1 and 7: no pickle anywhere; API keys only from env or secrets.toml."""

import importlib.util
import os

import pytest

from src.core import paths
from src.core.credentials import MissingSecretError, get_secret

KEY = "FRED_API_KEY"


def test_environment_variable_wins(tmp_path, monkeypatch):
    secrets = tmp_path / "secrets.toml"
    secrets.write_text(f'{KEY} = "from-file"\n')
    monkeypatch.setenv(KEY, "from-env")
    assert get_secret(KEY, str(secrets)) == "from-env"


def test_falls_back_to_secrets_toml(tmp_path, monkeypatch):
    secrets = tmp_path / "secrets.toml"
    secrets.write_text(f'{KEY} = "from-file"\n')
    monkeypatch.delenv(KEY, raising=False)
    assert get_secret(KEY, str(secrets)) == "from-file"


def test_missing_key_raises_without_echoing_values(tmp_path, monkeypatch):
    monkeypatch.delenv(KEY, raising=False)
    with pytest.raises(MissingSecretError) as err:
        get_secret(KEY, str(tmp_path / "absent.toml"))
    assert KEY in str(err.value) and "secrets.toml" in str(err.value)


def test_secrets_file_is_git_ignored():
    with open(os.path.join(paths.ROOT, ".gitignore"), encoding="utf-8") as f:
        lines = f.read().splitlines()
    # the exact file and any editor-added suffix (e.g. secrets.toml.txt)
    assert ".streamlit/secrets.toml*" in lines


def test_update_script_rejects_key_on_command_line():
    path = os.path.join(paths.ROOT, "scripts", "update_yields.py")
    spec = importlib.util.spec_from_file_location("update_yields", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.parse_args([])
    with pytest.raises(SystemExit):
        module.parse_args(["abc123secret"])


def test_no_pickle_in_code():
    hits = []
    for folder in ("src", "scripts", "pages"):
        for dirpath, _, files in os.walk(os.path.join(paths.ROOT, folder)):
            for name in files:
                if name.endswith(".py"):
                    with open(os.path.join(dirpath, name), encoding="utf-8") as f:
                        if "pickle" in f.read():
                            hits.append(name)
    assert hits == []


def test_secrets_toml_with_byte_order_mark(tmp_path, monkeypatch):
    secrets = tmp_path / "secrets.toml"
    bom = b"\xef\xbb\xbf"
    secrets.write_bytes(bom + f'{KEY} = "from-bom-file"\n'.encode())
    monkeypatch.delenv(KEY, raising=False)
    assert get_secret(KEY, str(secrets)) == "from-bom-file"
