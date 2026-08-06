import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse, StreamingResponse
from litellm import Router

from freeai.gateway.auth import verify_bearer_token

router = APIRouter(prefix="/v1", dependencies=[Depends(verify_bearer_token)])


def get_litellm_router(request: Request) -> Router:
    """Obtém a instância do litellm.Router configurada no estado da aplicação."""
    litellm_router: Router | None = getattr(request.app.state, "router", None)
    if not litellm_router:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mecanismo de roteamento não inicializado no servidor",
        )
    return litellm_router


@router.post("/chat/completions")
async def chat_completions(
    request: Request,
    litellm_router: Router = Depends(get_litellm_router),
) -> Any:
    """Endpoint de Chat Completion (compatível com OpenAI API) com suporte a SSE Streaming."""
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"JSON inválido: {e}") from e

    is_stream = body.get("stream", False)

    if is_stream:

        async def stream_generator():
            try:
                response = await litellm_router.acompletion(**body)
                async for chunk in response:
                    if hasattr(chunk, "model_dump_json"):
                        chunk_data = chunk.model_dump_json()
                    elif isinstance(chunk, dict):
                        chunk_data = json.dumps(chunk)
                    else:
                        chunk_data = str(chunk)
                    yield f"data: {chunk_data}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as exc:
                err_data = json.dumps({"error": {"message": str(exc), "type": "gateway_error"}})
                yield f"data: {err_data}\n\n"
                yield "data: [DONE]\n\n"

        return StreamingResponse(stream_generator(), media_type="text/event-stream")

    try:
        response = await litellm_router.acompletion(**body)
        if hasattr(response, "model_dump"):
            return response.model_dump()
        return response
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post("/embeddings")
async def embeddings(
    request: Request,
    litellm_router: Router = Depends(get_litellm_router),
) -> Any:
    """Endpoint de Embeddings (compatível com OpenAI API)."""
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"JSON inválido: {e}") from e

    try:
        response = await litellm_router.aembedding(**body)
        if hasattr(response, "model_dump"):
            return response.model_dump()
        return response
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post("/audio/speech")
async def text_to_speech(
    request: Request,
    litellm_router: Router = Depends(get_litellm_router),
) -> Any:
    """Endpoint de Text-to-Speech (TTS)."""
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"JSON inválido: {e}") from e

    try:
        response = await litellm_router.aspeech(**body)
        content = response.content if hasattr(response, "content") else response
        return Response(content=content, media_type="audio/mpeg")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post("/audio/transcriptions")
async def audio_transcriptions(
    request: Request,
    litellm_router: Router = Depends(get_litellm_router),
) -> Any:
    """Endpoint de Speech-to-Text (STT / Transcrição)."""
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"JSON inválido: {e}") from e

    try:
        response = await litellm_router.atranscription(**body)
        if hasattr(response, "model_dump"):
            return response.model_dump()
        return response
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get("/models")
async def list_models(
    litellm_router: Router = Depends(get_litellm_router),
) -> JSONResponse:
    """Retorna os modelos e aliases configurados no formato OpenAI Models List."""
    configured_models = getattr(litellm_router, "model_list", [])
    model_ids = sorted({model.get("model_name") for model in configured_models if model.get("model_name")})

    data = [{"id": model_id, "object": "model", "owned_by": "freeai"} for model_id in model_ids]

    return JSONResponse(content={"object": "list", "data": data})
