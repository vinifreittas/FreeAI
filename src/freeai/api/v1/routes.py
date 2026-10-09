import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse, StreamingResponse

from freeai.api.auth import verify_bearer_token
from freeai.services import Router

router = APIRouter(prefix="/v1", dependencies=[Depends(verify_bearer_token)])


def get_litellm_router(request: Request) -> Router:
    """Returns the Router instance configured in the application state."""
    app_router: Router | None = getattr(request.app.state, "router", None)
    if not app_router:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Router not initialized on server",
        )
    return app_router


def _diag_headers(obj: Any) -> dict[str, str]:
    return {
        "X-FreeAI-Provider": getattr(obj, "_freeai_provider", ""),
        "X-FreeAI-Model": getattr(obj, "_freeai_model", ""),
        "X-FreeAI-Fallback-Attempts": str(getattr(obj, "_freeai_attempts", 0)),
    }


@router.post("/chat/completions")
async def chat_completions(
    request: Request,
    app_router: Router = Depends(get_litellm_router),
) -> Any:
    """Chat Completion endpoint (OpenAI API compatible) with SSE Streaming support."""
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid JSON: {e}") from e

    is_stream = body.get("stream", False)

    if is_stream:
        try:
            stream_resp = await app_router.acompletion(**body)
            headers = _diag_headers(stream_resp)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

        async def stream_generator():
            try:
                async for chunk in stream_resp:
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

        return StreamingResponse(stream_generator(), media_type="text/event-stream", headers=headers)

    try:
        response = await app_router.acompletion(**body)
        content = response.model_dump() if hasattr(response, "model_dump") else response
        return JSONResponse(content=content, headers=_diag_headers(response))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post("/embeddings")
async def embeddings(
    request: Request,
    app_router: Router = Depends(get_litellm_router),
) -> Any:
    """Embeddings endpoint (OpenAI API compatible)."""
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid JSON: {e}") from e

    try:
        response = await app_router.aembedding(**body)
        content = response.model_dump() if hasattr(response, "model_dump") else response
        return JSONResponse(content=content, headers=_diag_headers(response))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post("/audio/speech")
async def text_to_speech(
    request: Request,
    app_router: Router = Depends(get_litellm_router),
) -> Any:
    """Text-to-Speech (TTS) endpoint."""
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid JSON: {e}") from e

    try:
        response = await app_router.aspeech(**body)
        content = response.content if hasattr(response, "content") else response
        return Response(content=content, media_type="audio/mpeg")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post("/audio/transcriptions")
async def audio_transcriptions(
    request: Request,
    app_router: Router = Depends(get_litellm_router),
) -> Any:
    """Speech-to-Text (STT / Transcription) endpoint."""
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid JSON: {e}") from e

    try:
        response = await app_router.atranscription(**body)
        if hasattr(response, "model_dump"):
            return response.model_dump()
        return response
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get("/models")
async def list_models(
    app_router: Router = Depends(get_litellm_router),
) -> JSONResponse:
    """Returns active configured models and aliases in OpenAI Models List format."""
    catalog = app_router.catalog
    route_names: list[str] = []
    if hasattr(catalog, "list_all_route_names"):
        route_names = catalog.list_all_route_names()
    elif hasattr(catalog, "routes") and isinstance(catalog.routes, dict):
        route_names = list(catalog.routes.keys())
    elif isinstance(catalog, dict):
        route_names = list(catalog.keys())

    data = [{"id": name, "object": "model", "owned_by": "freeai"} for name in sorted(set(route_names))]
    return JSONResponse(content={"object": "list", "data": data})
