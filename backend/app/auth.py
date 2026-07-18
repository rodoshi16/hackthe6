"""Auth0 JWT validation with demo-mode fallback."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings

security = HTTPBearer(auto_error=False)

# Cached JWKS
_jwks_cache: dict | None = None


async def _get_jwks(domain: str) -> dict:
    global _jwks_cache
    if _jwks_cache:
        return _jwks_cache
    import httpx

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"https://{domain}/.well-known/jwks.json")
        resp.raise_for_status()
        _jwks_cache = resp.json()
        return _jwks_cache


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    """
    Validate Auth0 JWT when configured.
    In demo mode without Auth0, accept X-Demo-User or default demo user.
    """
    settings = get_settings()

    if not settings.auth0_domain or not settings.auth0_audience:
        # Demo mode — no Auth0 configured
        return {"sub": "demo-user", "name": "Demo Trader", "demo": True}

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token",
        )

    token = credentials.credentials
    try:
        import jwt
        from jwt import PyJWKClient

        jwks_url = f"https://{settings.auth0_domain}/.well-known/jwks.json"
        jwks_client = PyJWKClient(jwks_url)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=settings.auth0_algorithms.split(","),
            audience=settings.auth0_audience,
            issuer=f"https://{settings.auth0_domain}/",
        )
        return payload
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
        ) from e


def user_id_from(user: dict, override: str | None = None) -> str:
    if override:
        return override
    return user.get("sub") or "demo-user"
