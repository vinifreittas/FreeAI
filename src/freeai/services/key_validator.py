from typing import Any

import litellm

from freeai.core import get_settings


async def validate_provider_key(
    provider_id: str,
    api_key: str,
    max_candidates: int = 3,
) -> tuple[bool, str]:
    """Lightweight connection health-check testing API key validity across provider candidate models."""
    if not api_key or not api_key.strip():
        return False, "Chave não informada ou vazia."

    settings = get_settings()
    provider = settings.get_provider(provider_id)
    if not provider or not provider.models:
        return False, f"Provedor '{provider_id}' não possui modelos configurados."

    # Prioritize chat models, then append other models as fallback
    candidates = [m for m in provider.models if "chat" in m.types]
    for m in provider.models:
        if m not in candidates:
            candidates.append(m)

    last_error = "Nenhum modelo respondeu com sucesso."
    for model in candidates[:max_candidates]:
        test_model = f"{provider.id}/{model.remote_model}"
        try:
            kwargs: dict[str, Any] = {
                "model": test_model,
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 1,
                "api_key": api_key.strip(),
            }
            await litellm.acompletion(**kwargs)
            return True, f"Conexão estabelecida com sucesso via '{model.id}'! Chave válida."
        except litellm.AuthenticationError:
            return False, "Chave inválida ou não autorizada pelo provedor."
        except litellm.RateLimitError:
            return True, "Chave válida, mas com cota momentaneamente esgotada (Rate Limit)."
        except litellm.NotFoundError:
            last_error = f"Modelo '{test_model}' não encontrado (404)."
            continue
        except (litellm.APIConnectionError, litellm.Timeout):
            last_error = "Falha de conexão ou timeout ao validar com o provedor."
            continue
        except Exception as exc:
            last_error = str(exc)
            continue

    return False, f"Falha na validação do provedor '{provider_id}': {last_error}"


test_provider_key = validate_provider_key
