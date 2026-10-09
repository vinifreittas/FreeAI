from typing import Any

import litellm

from freeai.core import get_settings


async def validate_provider_key(provider_id: str, api_key: str) -> tuple[bool, str]:
    """Lightweight single-token connection health-check testing API key validity for provider."""
    if not api_key or not api_key.strip():
        return False, "Chave não informada ou vazia."

    settings = get_settings()
    provider = settings.get_provider(provider_id)
    if not provider or not provider.models:
        return False, f"Provedor '{provider_id}' não possui modelos configurados."

    chat_model = next((m for m in provider.models if "chat" in m.types), provider.models[0])
    test_model = f"{provider.id}/{chat_model.remote_model}"

    try:
        kwargs: dict[str, Any] = {
            "model": test_model,
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 1,
            "api_key": api_key.strip(),
        }
        await litellm.acompletion(**kwargs)
        return True, "Conexão estabelecida com sucesso! Chave válida."
    except litellm.AuthenticationError:
        return False, "Chave inválida ou não autorizada pelo provedor."
    except litellm.RateLimitError:
        return True, "Chave válida, mas com cota momentaneamente esgotada (Rate Limit)."
    except litellm.NotFoundError:
        return False, f"Modelo de teste '{test_model}' não encontrado no provedor."
    except (litellm.APIConnectionError, litellm.Timeout):
        return False, "Falha de conexão ou timeout ao validar com o provedor."
    except Exception as exc:
        return False, f"Erro ao testar chave: {exc}"


test_provider_key = validate_provider_key
