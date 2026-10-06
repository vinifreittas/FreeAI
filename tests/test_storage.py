import os
import stat

from freeai.core.storage import load_vault, save_vault


def test_storage_save_and_load(tmp_path, monkeypatch):
    test_vault_file = tmp_path / ".test_vault.json"
    monkeypatch.setenv("FREEAI_VAULT_PATH", str(test_vault_file))

    data = {
        "GOOGLE_API_KEY": "test_google_key_123",
        "PORT": 4005,
        "HOST": "127.0.0.1",
    }
    save_vault(data)

    assert test_vault_file.exists()
    # Verifica permissão 0600
    file_stat = os.stat(test_vault_file)
    assert file_stat.st_mode & (stat.S_IRWXG | stat.S_IRWXO) == 0

    # Verifica que o conteúdo salvo não está em texto puro (está protegido/cifrado)
    raw_content = test_vault_file.read_text()
    assert "test_google_key_123" not in raw_content

    # Carrega e valida integridade
    loaded = load_vault()
    assert loaded == data
