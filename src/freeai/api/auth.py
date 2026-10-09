import secrets

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from freeai.core import get_settings

security = HTTPBearer(auto_error=False)


async def verify_bearer_token(
    credentials: HTTPAuthorizationCredentials | None = Security(security),
) -> str:
    """Verifies presence and validity of Bearer token in Authorization header."""
    settings = get_settings()

    # If FreeAI API key is not configured on server, access is open (local development)
    if not settings.FREEAI_API_KEY:
        return ""

    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autorização ausente ou inválido no cabeçalho Bearer",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not secrets.compare_digest(credentials.credentials, settings.FREEAI_API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key inválida",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return credentials.credentials
