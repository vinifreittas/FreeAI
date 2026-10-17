import asyncio
import io
import time
from typing import Any

import litellm
from pydantic import BaseModel, Field

from freeai.core import Settings, get_settings
from freeai.core.config import ResolvedTarget


class ModelTestResult(BaseModel):
    model_id: str
    litellm_model: str
    provider_id: str
    types: list[str] = Field(default_factory=list)
    status: str
    success: bool
    latency_ms: int
    details: str


async def test_single_model(
    target: ResolvedTarget,
    api_key: str | None = None,
    timeout: float = 10.0,
) -> ModelTestResult:
    """Executa um teste de conectividade pontual para um único modelo."""
    if not api_key:
        return ModelTestResult(
            model_id=target.target_id,
            litellm_model=target.litellm_model,
            provider_id=target.provider_id,
            types=target.types,
            status="Sem Chave",
            success=False,
            latency_ms=0,
            details="Chave de API não configurada",
        )

    start = time.perf_counter()
    try:
        async with asyncio.timeout(timeout):
            if "embedding" in target.types:
                await litellm.aembedding(
                    model=target.litellm_model,
                    input=["ping"],
                    api_key=api_key,
                )
            elif "stt" in target.types:
                dummy_wav = b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
                buf = io.BytesIO(dummy_wav)
                buf.name = "ping.wav"
                await litellm.atranscription(
                    model=target.litellm_model,
                    file=buf,
                    api_key=api_key,
                )
            elif "tts" in target.types:
                await litellm.aspeech(
                    model=target.litellm_model,
                    input="ping",
                    voice="alloy",
                    api_key=api_key,
                )
            else:
                kwargs: dict[str, Any] = {
                    "model": target.litellm_model,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 1,
                    "api_key": api_key,
                }
                await litellm.acompletion(**kwargs)

        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return ModelTestResult(
            model_id=target.target_id,
            litellm_model=target.litellm_model,
            provider_id=target.provider_id,
            types=target.types,
            status="OK",
            success=True,
            latency_ms=elapsed_ms,
            details="Operacional",
        )
    except litellm.RateLimitError as exc:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return ModelTestResult(
            model_id=target.target_id,
            litellm_model=target.litellm_model,
            provider_id=target.provider_id,
            types=target.types,
            status="Rate Limit",
            success=True,
            latency_ms=elapsed_ms,
            details=f"Cota momentaneamente excedida: {exc}"[:80],
        )
    except litellm.AuthenticationError:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return ModelTestResult(
            model_id=target.target_id,
            litellm_model=target.litellm_model,
            provider_id=target.provider_id,
            types=target.types,
            status="Erro",
            success=False,
            latency_ms=elapsed_ms,
            details="Chave de API não autorizada ou inválida",
        )
    except litellm.NotFoundError:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return ModelTestResult(
            model_id=target.target_id,
            litellm_model=target.litellm_model,
            provider_id=target.provider_id,
            types=target.types,
            status="Erro",
            success=False,
            latency_ms=elapsed_ms,
            details="Modelo não encontrado no provedor (404)",
        )
    except TimeoutError:
        return ModelTestResult(
            model_id=target.target_id,
            litellm_model=target.litellm_model,
            provider_id=target.provider_id,
            types=target.types,
            status="Timeout",
            success=False,
            latency_ms=int(timeout * 1000),
            details=f"Tempo limite excedido ({timeout}s)",
        )
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return ModelTestResult(
            model_id=target.target_id,
            litellm_model=target.litellm_model,
            provider_id=target.provider_id,
            types=target.types,
            status="Erro",
            success=False,
            latency_ms=elapsed_ms,
            details=str(exc)[:80],
        )


async def test_all_models(
    settings: Settings | None = None,
    provider_id: str | None = None,
    max_concurrency: int = 5,
    timeout: float = 10.0,
) -> list[ModelTestResult]:
    """Testa todos os modelos conectados dos provedores ativos e configurados."""
    if settings is None:
        settings = get_settings()

    targets: list[tuple[ResolvedTarget, str]] = []
    for provider in settings.providers:
        api_key = provider.api_key
        if not api_key:
            continue
        if provider_id and provider.id != provider_id:
            continue
        for model in provider.models:
            tgt = ResolvedTarget(
                target_id=model.id,
                litellm_model=f"{provider.id}/{model.remote_model}",
                provider_id=provider.id,
                api_key_env=provider.api_key_env,
                types=model.types,
            )
            targets.append((tgt, api_key))

    sem = asyncio.Semaphore(max_concurrency)

    async def _test_worker(tgt: ResolvedTarget, key: str) -> ModelTestResult:
        async with sem:
            return await test_single_model(tgt, api_key=key, timeout=timeout)

    return list(await asyncio.gather(*(_test_worker(t, k) for t, k in targets)))


test_single_model.__test__ = False  # type: ignore[attr-defined]
test_all_models.__test__ = False  # type: ignore[attr-defined]
ping_model = test_single_model
check_all_models = test_all_models
