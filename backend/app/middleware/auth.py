"""
Middleware de autenticação e injecção de contexto de tenant.

Extrai o tenant_id do token de autorização e define o contexto
de sessão PostgreSQL para RLS antes de cada pedido.
"""
import logging
import uuid

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse

from app.services.auth import verify_hmac_token

logger = logging.getLogger(__name__)

# Rotas que não requerem autenticação
PUBLIC_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


class TenantAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware que:
    1. Verifica o token HMAC-SHA256 no header Authorization.
    2. Extrai tenant_id do payload do token.
    3. Injeta tenant_id no estado do pedido (request.state.tenant_id).
    4. Define SET LOCAL app.current_tenant na sessão de BD (RLS hook).
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Rotas públicas — sem autenticação
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        # Extrair token do header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Token de autorização ausente ou inválido."},
            )

        token = auth_header.removeprefix("Bearer ").strip()
        payload = verify_hmac_token(token)

        if payload is None:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Token expirado ou inválido."},
            )

        tenant_id_str = payload.get("tenant_id")
        if not tenant_id_str:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Token sem tenant_id."},
            )

        try:
            tenant_id = uuid.UUID(tenant_id_str)
        except ValueError:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "tenant_id inválido no token."},
            )

        # Injectar no estado do pedido para uso nos handlers
        request.state.tenant_id = tenant_id

        logger.debug("Pedido autenticado — tenant_id=%s path=%s", tenant_id, request.url.path)

        return await call_next(request)


def get_tenant_id(request: Request) -> uuid.UUID:
    """
    Dependency FastAPI — retorna tenant_id do estado do pedido.

    Uso:
        @router.get("/recurso")
        def endpoint(tenant_id: uuid.UUID = Depends(get_tenant_id)):
            ...
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Contexto de tenant em falta.",
        )
    return tenant_id
