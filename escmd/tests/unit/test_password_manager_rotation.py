"""Tests for PasswordManager.rotate_master_key."""

import base64
import json
import pytest
from cryptography.fernet import Fernet

from security.password_manager import PasswordManager


@pytest.fixture
def state_dir(tmp_path):
    return tmp_path


def _encrypt_value(fernet: Fernet, plaintext: str) -> str:
    enc = fernet.encrypt(plaintext.encode("utf-8"))
    return base64.urlsafe_b64encode(enc).decode("utf-8")


def test_rotate_master_key_reencrypts_and_backup(state_dir, monkeypatch):
    monkeypatch.delenv("ESCMD_MASTER_KEY", raising=False)
    key = Fernet.generate_key().decode("utf-8")
    f_old = Fernet(key.encode("utf-8"))
    cfg = {
        "current_cluster": "test",
        "security": {
            "master_key": key,
            "encrypted_passwords": {
                "prod.user": _encrypt_value(f_old, "secret-one"),
                "global": _encrypt_value(f_old, "secret-two"),
            },
        },
    }
    path = state_dir / "escmd.json"
    path.write_text(json.dumps(cfg, indent=4), encoding="utf-8")

    pm = PasswordManager(str(path))
    ok, msg, details = pm.rotate_master_key()
    assert ok, msg
    assert details is not None
    assert details["reencrypted_count"] == 2

    backup = state_dir / "escmd.json.old"
    assert backup.is_file()
    assert json.loads(backup.read_text(encoding="utf-8")) == cfg

    updated = json.loads(path.read_text(encoding="utf-8"))
    new_key = updated["security"]["master_key"]
    assert new_key != key
    f_new = Fernet(new_key.encode("utf-8"))
    blobs = updated["security"]["encrypted_passwords"]
    assert f_new.decrypt(base64.urlsafe_b64decode(blobs["prod.user"])).decode() == "secret-one"
    assert f_new.decrypt(base64.urlsafe_b64decode(blobs["global"])).decode() == "secret-two"


def test_rotate_master_key_uses_env_key_when_set(state_dir, monkeypatch):
    file_key = Fernet.generate_key().decode("utf-8")
    env_key = Fernet.generate_key().decode("utf-8")
    f_file = Fernet(file_key.encode("utf-8"))
    f_env = Fernet(env_key.encode("utf-8"))
    cfg = {
        "security": {
            "master_key": file_key,
            "encrypted_passwords": {"a": _encrypt_value(f_env, "from-env")},
        },
    }
    path = state_dir / "escmd.json"
    path.write_text(json.dumps(cfg), encoding="utf-8")

    monkeypatch.setenv("ESCMD_MASTER_KEY", env_key)
    pm = PasswordManager(str(path))
    ok, _, details = pm.rotate_master_key()
    assert ok
    assert details is not None

    monkeypatch.delenv("ESCMD_MASTER_KEY", raising=False)
    updated = json.loads(path.read_text(encoding="utf-8"))
    new_key = updated["security"]["master_key"]
    f_new = Fernet(new_key.encode("utf-8"))
    pt = f_new.decrypt(
        base64.urlsafe_b64decode(updated["security"]["encrypted_passwords"]["a"])
    ).decode()
    assert pt == "from-env"


def test_rotate_master_key_fails_when_cannot_decrypt(state_dir, monkeypatch):
    monkeypatch.delenv("ESCMD_MASTER_KEY", raising=False)
    wrong = Fernet.generate_key().decode("utf-8")
    right = Fernet.generate_key().decode("utf-8")
    f_right = Fernet(right.encode("utf-8"))
    cfg = {
        "security": {
            "master_key": wrong,
            "encrypted_passwords": {"x": _encrypt_value(f_right, "nope")},
        },
    }
    path = state_dir / "escmd.json"
    path.write_text(json.dumps(cfg), encoding="utf-8")

    pm = PasswordManager(str(path))
    ok, msg, details = pm.rotate_master_key()
    assert not ok
    assert details is None
    assert "decrypt" in msg.lower() or "Failed" in msg


def test_get_rotate_master_key_preview(state_dir, monkeypatch):
    monkeypatch.delenv("ESCMD_MASTER_KEY", raising=False)
    key = Fernet.generate_key().decode("utf-8")
    f = Fernet(key.encode("utf-8"))
    cfg = {
        "security": {
            "master_key": key,
            "encrypted_passwords": {"a.b": _encrypt_value(f, "x")},
        },
    }
    path = state_dir / "escmd.json"
    path.write_text(json.dumps(cfg), encoding="utf-8")
    pm = PasswordManager(str(path))
    err, preview = pm.get_rotate_master_key_preview()
    assert err is None
    assert preview["entry_count"] == 1
    assert preview["storage_keys"] == ["a.b"]
