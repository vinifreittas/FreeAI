import base64
import contextlib
import hashlib
import json
import os
import uuid
from pathlib import Path
from typing import Any

VAULT_DIR = Path.home() / ".freeai"
VAULT_PATH = Path(os.getenv("FREEAI_VAULT_PATH") or (VAULT_DIR / "vault.json"))


def _derive_key() -> bytes:
    """Derives stable cryptographic key based on current machine and user."""
    node = str(uuid.getnode())
    home = str(Path.home())
    user = os.getenv("USER", "freeai")
    seed = f"{node}:{home}:{user}:freeai_keystream_salt".encode()
    return hashlib.sha256(seed).digest()


def _xor_crypt(data: bytes, key: bytes) -> bytes:
    """Simple symmetric cipher via keystream XOR (stdlib)."""
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


_cache_entry: tuple[str, float, dict[str, Any]] | None = None


def load_vault() -> dict[str, Any]:
    """Loads settings and secrets from protected user vault."""
    global _cache_entry
    target_path = Path(os.getenv("FREEAI_VAULT_PATH") or VAULT_PATH)
    legacy_path = Path.cwd() / ".freeai_vault.json"

    # Automatic migration if legacy file exists in repository
    if not target_path.exists() and legacy_path.exists():
        try:
            raw_b64 = legacy_path.read_bytes()
            decrypted = _xor_crypt(base64.b64decode(raw_b64), _derive_key())
            data = json.loads(decrypted.decode("utf-8"))
            save_vault(data)
            legacy_path.unlink(missing_ok=True)
            return data
        except Exception:
            pass

    if not target_path.exists():
        _cache_entry = None
        return {}

    mtime = target_path.stat().st_mtime
    target_str = str(target_path)
    if _cache_entry and _cache_entry[0] == target_str and _cache_entry[1] == mtime:
        return dict(_cache_entry[2])

    try:
        raw_b64 = target_path.read_bytes()
        encrypted = base64.b64decode(raw_b64)
        decrypted = _xor_crypt(encrypted, _derive_key())
        data = json.loads(decrypted.decode("utf-8"))
        _cache_entry = (target_str, mtime, data)
        return dict(data)
    except Exception:
        return {}


def save_vault(data: dict[str, Any]) -> None:
    """Saves settings and secrets encrypted with 0600 permissions to ~/.freeai/vault.json."""
    global _cache_entry
    target_path = Path(os.getenv("FREEAI_VAULT_PATH") or VAULT_PATH)
    target_dir = target_path.parent

    target_dir.mkdir(parents=True, exist_ok=True)
    with contextlib.suppress(OSError):
        os.chmod(target_dir, 0o700)

    key = _derive_key()
    payload = json.dumps(data).encode("utf-8")
    encrypted = _xor_crypt(payload, key)
    b64_data = base64.b64encode(encrypted)

    # Create or overwrite with restricted 0o600 permissions (owner only)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    fd = os.open(target_path, flags, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(b64_data)
    os.chmod(target_path, 0o600)
    _cache_entry = (str(target_path), target_path.stat().st_mtime, dict(data))
