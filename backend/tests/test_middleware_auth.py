"""
Testes para middleware de autenticação e tenant context injection.

Estratégia: Testar TenantAuthMiddleware.dispatch() com rotas públicas,
tokens válidos/inválidos, tenant_id ausente/inválido, e dependency get_tenant_id().
"""
import uuid
from unittest.mock import MagicMock, AsyncMock, patch
from types import SimpleNamespace

import pytest
from fastapi import Request, HTTPException, Depends
from fastapi.testclient import TestClient
from starlette.responses import Response


class TestTenantAuthMiddlewarePublicPaths:
    """Testes para rotas públicas (sem autenticação)."""

    @pytest.mark.asyncio
    async def test_public_path_health_skips_auth(self):
        """GET /health não requer token."""
        from app.middleware.auth import TenantAuthMiddleware

        request = MagicMock(spec=Request)
        request.url.path = "/health"
        request.headers = {}

        call_next = AsyncMock(return_value=Response("OK"))

        middleware = TenantAuthMiddleware(call_next)
        result = await middleware.dispatch(request, call_next)

        assert call_next.called
        assert result.body == b"OK"

    @pytest.mark.asyncio
    async def test_public_path_docs_skips_auth(self):
        """GET /docs não requer token."""
        from app.middleware.auth import TenantAuthMiddleware

        request = MagicMock(spec=Request)
        request.url.path = "/docs"
        request.headers = {}

        call_next = AsyncMock(return_value=Response("OK"))

        middleware = TenantAuthMiddleware(call_next)
        result = await middleware.dispatch(request, call_next)

        assert call_next.called

    @pytest.mark.asyncio
    async def test_public_path_openapi_json_skips_auth(self):
        """GET /openapi.json não requer token."""
        from app.middleware.auth import TenantAuthMiddleware

        request = MagicMock(spec=Request)
        request.url.path = "/openapi.json"
        request.headers = {}

        call_next = AsyncMock(return_value=Response("OK"))

        middleware = TenantAuthMiddleware(call_next)
        result = await middleware.dispatch(request, call_next)

        assert call_next.called

    @pytest.mark.asyncio
    async def test_public_path_redoc_skips_auth(self):
        """GET /redoc não requer token."""
        from app.middleware.auth import TenantAuthMiddleware

        request = MagicMock(spec=Request)
        request.url.path = "/redoc"
        request.headers = {}

        call_next = AsyncMock(return_value=Response("OK"))

        middleware = TenantAuthMiddleware(call_next)
        result = await middleware.dispatch(request, call_next)

        assert call_next.called


class TestTenantAuthMiddlewareAuthorization:
    """Testes para validação de Authorization header."""

    @pytest.mark.asyncio
    async def test_missing_authorization_header_returns_401(self):
        """Falta header Authorization → 401."""
        from app.middleware.auth import TenantAuthMiddleware

        request = MagicMock(spec=Request)
        request.url.path = "/devices/"
        request.headers = {}  # Sem Authorization

        call_next = AsyncMock()

        middleware = TenantAuthMiddleware(call_next)

        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(request, call_next)

        assert exc_info.value.status_code == 401
        assert "ausente ou inválido" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_authorization_header_without_bearer_prefix_returns_401(self):
        """Authorization header sem 'Bearer ' prefix → 401."""
        from app.middleware.auth import TenantAuthMiddleware

        request = MagicMock(spec=Request)
        request.url.path = "/devices/"
        request.headers = {"Authorization": "Token abc123"}  # Tipo errado

        call_next = AsyncMock()

        middleware = TenantAuthMiddleware(call_next)

        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(request, call_next)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_authorization_header_malformed_returns_401(self):
        """Authorization header malformed → 401."""
        from app.middleware.auth import TenantAuthMiddleware

        request = MagicMock(spec=Request)
        request.url.path = "/devices/"
        request.headers = {"Authorization": "Bearer"}  # Sem token após Bearer

        call_next = AsyncMock()

        middleware = TenantAuthMiddleware(call_next)

        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(request, call_next)

        assert exc_info.value.status_code == 401


class TestTenantAuthMiddlewareTokenValidation:
    """Testes para validação do token HMAC."""

    @pytest.mark.asyncio
    async def test_invalid_token_returns_401(self):
        """verify_hmac_token retorna None → 401."""
        from app.middleware.auth import TenantAuthMiddleware

        request = MagicMock(spec=Request)
        request.url.path = "/devices/"
        request.headers = {"Authorization": "Bearer invalid.token.here"}

        call_next = AsyncMock()

        middleware = TenantAuthMiddleware(call_next)

        with patch("app.middleware.auth.verify_hmac_token", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await middleware.dispatch(request, call_next)

            assert exc_info.value.status_code == 401
            assert "expirado ou inválido" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_token_missing_tenant_id_returns_403(self):
        """Token sem tenant_id no payload → 403."""
        from app.middleware.auth import TenantAuthMiddleware

        request = MagicMock(spec=Request)
        request.url.path = "/devices/"
        request.headers = {"Authorization": "Bearer valid.token"}

        call_next = AsyncMock()

        middleware = TenantAuthMiddleware(call_next)

        # Token válido mas sem tenant_id
        payload = {"user_id": "some-user"}

        with patch("app.middleware.auth.verify_hmac_token", return_value=payload):
            with pytest.raises(HTTPException) as exc_info:
                await middleware.dispatch(request, call_next)

            assert exc_info.value.status_code == 403
            assert "sem tenant_id" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_token_tenant_id_invalid_uuid_returns_403(self):
        """tenant_id não é UUID válido → 403."""
        from app.middleware.auth import TenantAuthMiddleware

        request = MagicMock(spec=Request)
        request.url.path = "/devices/"
        request.headers = {"Authorization": "Bearer valid.token"}

        call_next = AsyncMock()

        middleware = TenantAuthMiddleware(call_next)

        # tenant_id é string mas não é UUID válido
        payload = {"tenant_id": "not-a-uuid"}

        with patch("app.middleware.auth.verify_hmac_token", return_value=payload):
            with pytest.raises(HTTPException) as exc_info:
                await middleware.dispatch(request, call_next)

            assert exc_info.value.status_code == 403
            assert "inválido" in exc_info.value.detail


class TestTenantAuthMiddlewareSuccess:
    """Testes para autenticação bem-sucedida."""

    @pytest.mark.asyncio
    async def test_valid_token_sets_request_state_tenant_id(self):
        """Token válido com UUID valid tenant_id → request.state.tenant_id é setado."""
        from app.middleware.auth import TenantAuthMiddleware

        sample_tenant_id = str(uuid.uuid4())
        request = MagicMock(spec=Request)
        request.url.path = "/devices/"
        request.headers = {"Authorization": "Bearer valid.token"}
        request.state = SimpleNamespace()

        response = Response("OK")
        call_next = AsyncMock(return_value=response)

        middleware = TenantAuthMiddleware(call_next)

        payload = {"tenant_id": sample_tenant_id}

        with patch("app.middleware.auth.verify_hmac_token", return_value=payload):
            result = await middleware.dispatch(request, call_next)

            # request.state.tenant_id deve ser setado
            assert hasattr(request.state, "tenant_id")
            assert request.state.tenant_id == uuid.UUID(sample_tenant_id)
            assert call_next.called
            assert result == response

    @pytest.mark.asyncio
    async def test_valid_token_calls_next_middleware(self):
        """Token válido → call_next() é invocado."""
        from app.middleware.auth import TenantAuthMiddleware

        sample_tenant_id = str(uuid.uuid4())
        request = MagicMock(spec=Request)
        request.url.path = "/devices/"
        request.headers = {"Authorization": "Bearer valid.token"}
        request.state = SimpleNamespace()

        response = Response("OK")
        call_next = AsyncMock(return_value=response)

        middleware = TenantAuthMiddleware(call_next)

        payload = {"tenant_id": sample_tenant_id}

        with patch("app.middleware.auth.verify_hmac_token", return_value=payload):
            result = await middleware.dispatch(request, call_next)

            assert call_next.called

    @pytest.mark.asyncio
    async def test_valid_token_logs_debug_message(self):
        """Token válido → mensagem debug é logada."""
        from app.middleware.auth import TenantAuthMiddleware

        sample_tenant_id = str(uuid.uuid4())
        request = MagicMock(spec=Request)
        request.url.path = "/devices/"
        request.headers = {"Authorization": "Bearer valid.token"}
        request.state = SimpleNamespace()

        response = Response("OK")
        call_next = AsyncMock(return_value=response)

        middleware = TenantAuthMiddleware(call_next)

        payload = {"tenant_id": sample_tenant_id}

        with patch("app.middleware.auth.verify_hmac_token", return_value=payload):
            with patch("app.middleware.auth.logger") as mock_logger:
                result = await middleware.dispatch(request, call_next)

                # debug() deve ter sido chamado
                assert mock_logger.debug.called


class TestGetTenantIdDependency:
    """Testes para a dependency get_tenant_id()."""

    def test_get_tenant_id_returns_uuid_from_request_state(self):
        """get_tenant_id() retorna tenant_id do request.state."""
        from app.middleware.auth import get_tenant_id

        sample_tenant_id = uuid.uuid4()
        request = MagicMock(spec=Request)
        request.state = SimpleNamespace(tenant_id=sample_tenant_id)

        result = get_tenant_id(request)

        assert result == sample_tenant_id

    def test_get_tenant_id_missing_raises_403(self):
        """get_tenant_id() sem tenant_id em request.state → 403."""
        from app.middleware.auth import get_tenant_id

        request = MagicMock(spec=Request)
        request.state = SimpleNamespace()  # Sem tenant_id

        with pytest.raises(HTTPException) as exc_info:
            get_tenant_id(request)

        assert exc_info.value.status_code == 403
        assert "em falta" in exc_info.value.detail

    def test_get_tenant_id_none_raises_403(self):
        """get_tenant_id() com tenant_id=None → 403."""
        from app.middleware.auth import get_tenant_id

        request = MagicMock(spec=Request)
        request.state = SimpleNamespace(tenant_id=None)

        with pytest.raises(HTTPException) as exc_info:
            get_tenant_id(request)

        assert exc_info.value.status_code == 403


class TestTenantAuthMiddlewareIntegration:
    """Testes de integração com mocks de Request/Response."""

    @pytest.mark.asyncio
    async def test_multiple_sequential_requests_independence(self):
        """Múltiplos pedidos sequenciais não partilham estado."""
        from app.middleware.auth import TenantAuthMiddleware

        middleware = TenantAuthMiddleware(lambda r, c: Response("OK"))

        tenant1 = str(uuid.uuid4())
        tenant2 = str(uuid.uuid4())

        # Pedido 1
        request1 = MagicMock(spec=Request)
        request1.url.path = "/devices/"
        request1.headers = {"Authorization": "Bearer token1"}
        request1.state = SimpleNamespace()

        call_next1 = AsyncMock(return_value=Response("OK"))

        payload1 = {"tenant_id": tenant1}
        with patch("app.middleware.auth.verify_hmac_token", return_value=payload1):
            await middleware.dispatch(request1, call_next1)

        # Pedido 2 com tenant diferente
        request2 = MagicMock(spec=Request)
        request2.url.path = "/devices/"
        request2.headers = {"Authorization": "Bearer token2"}
        request2.state = SimpleNamespace()

        call_next2 = AsyncMock(return_value=Response("OK"))

        payload2 = {"tenant_id": tenant2}
        with patch("app.middleware.auth.verify_hmac_token", return_value=payload2):
            await middleware.dispatch(request2, call_next2)

        # request1 e request2 devem ter tenant_ids diferentes
        assert request1.state.tenant_id == uuid.UUID(tenant1)
        assert request2.state.tenant_id == uuid.UUID(tenant2)

    @pytest.mark.asyncio
    async def test_request_continues_after_auth_success(self):
        """Pedido continua após autenticação bem-sucedida."""
        from app.middleware.auth import TenantAuthMiddleware

        sample_tenant_id = str(uuid.uuid4())
        request = MagicMock(spec=Request)
        request.url.path = "/devices/"
        request.headers = {"Authorization": "Bearer valid"}
        request.state = SimpleNamespace()

        # call_next é chamado com o request e retorna Response
        next_response = Response("Handler executed")
        call_next = AsyncMock(return_value=next_response)

        middleware = TenantAuthMiddleware(call_next)

        payload = {"tenant_id": sample_tenant_id}

        with patch("app.middleware.auth.verify_hmac_token", return_value=payload):
            result = await middleware.dispatch(request, call_next)

            # call_next deve ter sido invocado
            assert call_next.call_count == 1

            # Response do handler deve ser retornado
            assert result == next_response


class TestAuthErrorMessages:
    """Testes para mensagens de erro claras."""

    @pytest.mark.asyncio
    async def test_missing_header_error_message_is_clear(self):
        """Mensagem de erro para header ausente é clara."""
        from app.middleware.auth import TenantAuthMiddleware

        request = MagicMock(spec=Request)
        request.url.path = "/devices/"
        request.headers = {}

        call_next = AsyncMock()

        middleware = TenantAuthMiddleware(call_next)

        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(request, call_next)

        assert "ausente ou inválido" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_invalid_token_error_message_is_clear(self):
        """Mensagem de erro para token inválido é clara."""
        from app.middleware.auth import TenantAuthMiddleware

        request = MagicMock(spec=Request)
        request.url.path = "/devices/"
        request.headers = {"Authorization": "Bearer invalid"}

        call_next = AsyncMock()

        middleware = TenantAuthMiddleware(call_next)

        with patch("app.middleware.auth.verify_hmac_token", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await middleware.dispatch(request, call_next)

            assert "expirado ou inválido" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_missing_tenant_id_error_message_is_clear(self):
        """Mensagem de erro para tenant_id ausente é clara."""
        from app.middleware.auth import TenantAuthMiddleware

        request = MagicMock(spec=Request)
        request.url.path = "/devices/"
        request.headers = {"Authorization": "Bearer valid"}

        call_next = AsyncMock()

        middleware = TenantAuthMiddleware(call_next)

        payload = {}  # Sem tenant_id

        with patch("app.middleware.auth.verify_hmac_token", return_value=payload):
            with pytest.raises(HTTPException) as exc_info:
                await middleware.dispatch(request, call_next)

            assert "sem tenant_id" in exc_info.value.detail


class TestAuthTokenParsing:
    """Testes para parsing do token."""

    @pytest.mark.asyncio
    async def test_bearer_token_is_extracted_correctly(self):
        """Token é extraído corretamente do header."""
        from app.middleware.auth import TenantAuthMiddleware

        sample_tenant_id = str(uuid.uuid4())
        request = MagicMock(spec=Request)
        request.url.path = "/devices/"
        request.headers = {"Authorization": "Bearer mytoken123"}
        request.state = SimpleNamespace()

        response = Response("OK")
        call_next = AsyncMock(return_value=response)

        middleware = TenantAuthMiddleware(call_next)

        payload = {"tenant_id": sample_tenant_id}

        with patch("app.middleware.auth.verify_hmac_token") as mock_verify:
            mock_verify.return_value = payload

            result = await middleware.dispatch(request, call_next)

            # verify_hmac_token deve ter sido chamado com o token extraído
            mock_verify.assert_called_once_with("mytoken123")

    @pytest.mark.asyncio
    async def test_bearer_token_with_extra_whitespace_is_stripped(self):
        """Token com espaços é normalizado."""
        from app.middleware.auth import TenantAuthMiddleware

        sample_tenant_id = str(uuid.uuid4())
        request = MagicMock(spec=Request)
        request.url.path = "/devices/"
        request.headers = {"Authorization": "Bearer   mytoken123   "}
        request.state = SimpleNamespace()

        response = Response("OK")
        call_next = AsyncMock(return_value=response)

        middleware = TenantAuthMiddleware(call_next)

        payload = {"tenant_id": sample_tenant_id}

        with patch("app.middleware.auth.verify_hmac_token") as mock_verify:
            mock_verify.return_value = payload

            result = await middleware.dispatch(request, call_next)

            # Token deve ser normalizado (espaços removidos)
            mock_verify.assert_called_once_with("mytoken123")
