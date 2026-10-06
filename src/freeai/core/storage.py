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
    """Deriva uma chave criptográfica estável baseada na máquina e usuário atual."""
    node = str(uuid.getnode())
    home = str(Path.home())
    user = os.getenv("USER", "freeai")
    seed = f"{node}:{home}:{user}:freeai_keystream_salt".encode()
    return hashlib.sha256(seed).digest()


def _xor_crypt(data: bytes, key: bytes) -> bytes:
    """Cifra simétrica simples via XOR de keystream (stdlib)."""
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def load_vault() -> dict[str, Any]:
    """Carrega as configurações e segredos do vault protegido no diretório do usuário."""
    target_path = Path(os.getenv("FREEAI_VAULT_PATH") or VAULT_PATH)
    legacy_path = Path.cwd() / ".freeai_vault.json"

    # Migração automática se existir arquivo legado no repositório
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
        return {}

    try:
        raw_b64 = target_path.read_bytes()
        encrypted = base64.b64decode(raw_b64)
        decrypted = _xor_crypt(encrypted, _derive_key())
        return json.loads(decrypted.decode("utf-8"))
    except Exception:
        return {}


def save_vault(data: dict[str, Any]) -> None:
    """Salva configurações e segredos com cifra local e permissão 0600 em ~/.freeai/vault.json."""
    target_path = Path(os.getenv("FREEAI_VAULT_PATH") or VAULT_PATH)
    target_dir = target_path.parent

    target_dir.mkdir(parents=True, exist_ok=True)
    with contextlib.suppress(OSError):
        os.chmod(target_dir, 0o700)

    key = _derive_key()
    payload = json.dumps(data).encode("utf-8")
    encrypted = _xor_crypt(payload, key)
    b64_data = base64.b64encode(encrypted)

    # Cria ou sobrescreve com permissão restrita 0o600 (apenas proprietário)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    fd = os.open(target_path, flags, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(b64_data)
    os.chmod(target_path, 0o600)
