"""
Testes para integração JFA_Suite (suite_client + fluxo /access/validate com saldo).

Estratégia:
  - Suite client: testes unitários com httpx.MockTransport (sem servidor real).
  - Endpoint /access/validate com Suite: testes HTTP com mock do SuiteClient via
    dependency_overrides e flag SUITE_INTEGRATION_ENABLED=True via monkeypatch.
  - Todos os testes são isolados — não requerem JFA_Suite em execução.
"""
import json
import uuid
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from app.services.suite_client import (
    SuiteClient,
    SuiteClientError,
    SuiteTokenInsufficient,
    SuiteTokenNotFound,
)
from app.services.access_crypto import hash_pin_for_device


# ─── Fixtures auxiliares ──────────────────────────────────────────────────────

@pytest.fixture
def sample_token_id() -> uuid.UUID:
    return uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")


@pytest.fixture
def sample_access_point_id() -> uuid.UUID:
    return uuid.UUID("bbbbbbbb-0000-0000-0000-000000000001")


@pytest.fixture
def active_token_data(sample_token_id, sample_access_point_id) -> dict:
    """Token activo com 3 usos restantes."""
    return {
        "token_id": str(sample_token_id),
        "status": "active",
        "usos_max": 5,
        "usos_done": 2,
        "usos_restantes": 3,
        "valido_ate": "2030-01-01T00:00:00",
        "holder_ref": None,
    }


@pytest.fixture
def exhausted_token_data(sample_token_id) -> dict:
    """Token sem usos restantes."""
    return {
        "token_id": str(sample_token_id),
        "status": "consumed",
        "usos_max": 5,
        "usos_done": 5,
        "usos_restantes": 0,
        "valido_ate": "2030-01-01T00:00:00",
        "holder_ref": None,
    }


# ─── Testes unitários SuiteClient ─────────────────────────────────────────────

class TestSuiteClientHasBalance:
    """Testes de lógica local sem I/O."""

    def test_active_token_with_uses_has_balance(self, active_token_data):
        client = SuiteClient(base_url="http://test", api_token="tok")
        assert client.has_balance(active_token_data) is True

    def test_consumed_token_no_balance(self, exhausted_token_data):
        client = SuiteClient(base_url="http://test", api_token="tok")
        assert client.has_balance(exhausted_token_data) is False

    def test_zero_uses_no_balance(self):
        client = SuiteClient(base_url="http://test", api_token="tok")
        data = {"status": "active", "usos_restantes": 0}
        assert client.has_balance(data) is False

    def test_expired_status_no_balance(self):
        client = SuiteClient(base_url="http://test", api_token="tok")
        data = {"status": "expired", "usos_restantes": 2}
        assert client.has_balance(data) is False


@pytest.mark.asyncio
class TestSuiteClientHTTP:
    """Testes de chamadas HTTP com httpx mocked."""

    async def test_get_token_balance_success(
        self, active_token_data, sample_token_id
    ):
        client = SuiteClient(base_url="http://suite-test", api_token="tok")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = active_token_data

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_async_context = AsyncMock()
            mock_async_context.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            mock_client_class.return_value = mock_async_context

            result = await client.get_token_balance(sample_token_id)

        assert result["usos_restantes"] == 3
        assert result["status"] == "active"

    async def test_get_token_balance_404_raises_not_found(self, sample_token_id):
        client = SuiteClient(base_url="http://suite-test", api_token="tok")
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_async_context = AsyncMock()
            mock_async_context.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            mock_client_class.return_value = mock_async_context

            with pytest.raises(SuiteTokenNotFound):
                await client.get_token_balance(sample_token_id)

    async def test_get_token_balance_500_raises_client_error(self, sample_token_id):
        client = SuiteClient(base_url="http://suite-test", api_token="tok")
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_async_context = AsyncMock()
            mock_async_context.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            mock_client_class.return_value = mock_async_context

            with pytest.raises(SuiteClientError):
                await client.get_token_balance(sample_token_id)

    async def test_consume_token_success(
        self, sample_token_id, sample_access_point_id
    ):
        client = SuiteClient(base_url="http://suite-test", api_token="tok")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "token_id": str(sample_token_id),
            "usos_restantes": 2,
            "valido_ate": "2030-01-01T00:00:00",
            "acesso": "granted",
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_async_context = AsyncMock()
            mock_async_context.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            mock_client_class.return_value = mock_async_context

            result = await client.consume_token(sample_token_id, sample_access_point_id)

        assert result["acesso"] == "granted"
        assert result["usos_restantes"] == 2

    async def test_consume_token_409_raises_insufficient(
        self, sample_token_id, sample_access_point_id
    ):
        client = SuiteClient(base_url="http://suite-test", api_token="tok")
        mock_response = MagicMock()
        mock_response.status_code = 409
        mock_response.json.return_value = {"detail": "Token consumed"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_async_context = AsyncMock()
            mock_async_context.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            mock_client_class.return_value = mock_async_context

            with pytest.raises(SuiteTokenInsufficient):
                await client.consume_token(sample_token_id, sample_access_point_id)


# ─── Testes do endpoint /access/validate com integração Suite ─────────────────

@contextmanager
def _make_client_suite(
    sample_tenant_id,
    sample_device_id,
    pin_salt,
    mock_suite_client: SuiteClient,
    suite_enabled: bool = True,
):
    """Cria TestClient com Suite integration configurada."""
    from unittest.mock import patch
    from fastapi.testclient import TestClient
    from app.main import app
    from app.middleware.auth import get_tenant_id
    from app.db.session import get_db_tenant
    from app.services.suite_client import get_suite_client  # Importar da origem
    from tests.conftest import _make_client_with_auth

    mock_device = SimpleNamespace(
        id=sample_device_id,
        tenant_id=sample_tenant_id,
        name="Dispositivo Suite Teste",
        device_type="pin_pad",
        auth_mode="pin_only",
        pin_salt=pin_salt,
        pin_hash_algorithm="hmac_sha256",
        card_uids={"__pin__": hash_pin_for_device("1234", pin_salt)},
        mqtt_topic="jfa/unify/test/device/001",
        mqtt_backend="esp32",
        enabled=True,
    )

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = mock_device
    mock_db.query.return_value.filter.return_value.all.return_value = []
    mock_db.add.return_value = None
    mock_db.commit.return_value = None

    def override_get_tenant_id():
        return sample_tenant_id

    def override_get_db_tenant():
        yield mock_db

    async def override_get_suite_client():
        return mock_suite_client

    settings_patch = {
        "suite_integration_enabled": suite_enabled,
        "suite_base_url": "http://test-suite",
        "suite_api_token": "test-token",
    }

    with patch("app.middleware.auth.verify_hmac_token") as mock_verify, \
         patch("app.routers.access.get_settings") as mock_settings_fn:

        mock_verify.return_value = {"tenant_id": str(sample_tenant_id)}

        mock_settings_obj = MagicMock()
        mock_settings_obj.suite_integration_enabled = suite_enabled
        mock_settings_obj.environment = "test"
        mock_settings_fn.return_value = mock_settings_obj

        app.dependency_overrides[get_tenant_id] = override_get_tenant_id
        app.dependency_overrides[get_db_tenant] = override_get_db_tenant
        app.dependency_overrides[get_suite_client] = override_get_suite_client

        client = _make_client_with_auth(app, sample_tenant_id)
        yield client

        app.dependency_overrides.clear()


@pytest.fixture
def mock_suite_client_ok(active_token_data):
    """SuiteClient mockado que retorna saldo OK e consome com sucesso."""
    mock = AsyncMock(spec=SuiteClient)
    mock.get_token_balance.return_value = active_token_data
    mock.has_balance.return_value = True
    mock.consume_token.return_value = {
        "acesso": "granted",
        "usos_restantes": 2,
        "valido_ate": "2030-01-01T00:00:00",
    }
    # Usar a implementação real de has_balance
    real_client = SuiteClient(base_url="http://test", api_token="tok")
    mock.has_balance = real_client.has_balance
    return mock


@pytest.fixture
def mock_suite_client_no_balance(exhausted_token_data):
    """SuiteClient mockado que retorna saldo esgotado."""
    mock = AsyncMock(spec=SuiteClient)
    mock.get_token_balance.return_value = exhausted_token_data
    real_client = SuiteClient(base_url="http://test", api_token="tok")
    mock.has_balance = real_client.has_balance
    return mock


@pytest.fixture
def mock_suite_client_error():
    """SuiteClient mockado que levanta SuiteClientError."""
    mock = AsyncMock(spec=SuiteClient)
    mock.get_token_balance.side_effect = SuiteClientError("Broker inacessível")
    return mock


class TestValidateWithSuiteIntegration:
    """Testes do fluxo /access/validate com verificação de saldo JFA_Suite."""

    def test_valid_pin_with_valid_balance_grants_access(
        self,
        sample_tenant_id,
        sample_device_id,
        pin_salt,
        mock_suite_client_ok,
        sample_token_id,
        sample_access_point_id,
    ):
        """PIN válido + saldo OK → granted=True."""
        with _make_client_suite(
            sample_tenant_id, sample_device_id, pin_salt, mock_suite_client_ok
        ) as client:
            resp = client.post("/access/validate", json={
                "device_id": str(sample_device_id),
                "pin": "1234",
                "suite_token_id": str(sample_token_id),
                "suite_access_point_id": str(sample_access_point_id),
            })
            assert resp.status_code == 200
            data = resp.json()
            assert data["granted"] is True

    def test_valid_pin_insufficient_balance_denies(
        self,
        sample_tenant_id,
        sample_device_id,
        pin_salt,
        mock_suite_client_no_balance,
        sample_token_id,
        sample_access_point_id,
    ):
        """PIN válido mas saldo esgotado → granted=False, access_type=insufficient_balance."""
        with _make_client_suite(
            sample_tenant_id, sample_device_id, pin_salt, mock_suite_client_no_balance
        ) as client:
            resp = client.post("/access/validate", json={
                "device_id": str(sample_device_id),
                "pin": "1234",
                "suite_token_id": str(sample_token_id),
                "suite_access_point_id": str(sample_access_point_id),
            })
            assert resp.status_code == 200
            data = resp.json()
            assert data["granted"] is False
            assert data["access_type"] == "insufficient_balance"

    def test_suite_error_denies_access(
        self,
        sample_tenant_id,
        sample_device_id,
        pin_salt,
        mock_suite_client_error,
        sample_token_id,
        sample_access_point_id,
    ):
        """Erro de comunicação com JFA_Suite → granted=False, access_type=suite_error."""
        with _make_client_suite(
            sample_tenant_id, sample_device_id, pin_salt, mock_suite_client_error
        ) as client:
            resp = client.post("/access/validate", json={
                "device_id": str(sample_device_id),
                "pin": "1234",
                "suite_token_id": str(sample_token_id),
                "suite_access_point_id": str(sample_access_point_id),
            })
            assert resp.status_code == 200
            data = resp.json()
            assert data["granted"] is False
            assert data["access_type"] == "suite_error"

    def test_no_suite_token_skips_suite_check(
        self,
        sample_tenant_id,
        sample_device_id,
        pin_salt,
        mock_suite_client_ok,
    ):
        """
        Quando suite_token_id não é fornecido (mesmo com integração activa),
        flui pelo caminho original sem chamar o suite_client.
        """
        with _make_client_suite(
            sample_tenant_id, sample_device_id, pin_salt, mock_suite_client_ok
        ) as client:
            resp = client.post("/access/validate", json={
                "device_id": str(sample_device_id),
                "pin": "1234",
                # Sem suite_token_id
            })
            assert resp.status_code == 200
            # Suite client não deve ter sido chamado
            mock_suite_client_ok.get_token_balance.assert_not_called()

    def test_mqtt_grant_published_on_valid_balance(
        self,
        sample_tenant_id,
        sample_device_id,
        pin_salt,
        mock_suite_client_ok,
        sample_token_id,
        sample_access_point_id,
    ):
        """
        Com saldo OK, o comando MQTT de grant é publicado no tópico correcto.

        Verifica que `mqtt_service.adapter.publish` é chamado com:
          - tópico: jfa/unify/{tenant_id}/device/{device_id}/access/response
          - payload: JSON com action="grant"
        """
        import json as _json
        from unittest.mock import patch, AsyncMock as _AsyncMock
        from app.main import app
        from app.middleware.auth import get_tenant_id
        from app.db.session import get_db_tenant
        from app.services.suite_client import get_suite_client
        from tests.conftest import _make_client_with_auth

        mock_adapter = MagicMock()
        mock_adapter.publish = _AsyncMock(return_value=None)
        mock_mqtt_svc = MagicMock()
        mock_mqtt_svc.adapter = mock_adapter

        mock_device = SimpleNamespace(
            id=sample_device_id,
            tenant_id=sample_tenant_id,
            name="Dispositivo MQTT Teste",
            device_type="pin_pad",
            auth_mode="pin_only",
            pin_salt=pin_salt,
            pin_hash_algorithm="hmac_sha256",
            card_uids={"__pin__": hash_pin_for_device("1234", pin_salt)},
            mqtt_topic="jfa/unify/test/device/001",
            mqtt_backend="esp32",
            enabled=True,
        )
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_device
        mock_db.add.return_value = None
        mock_db.commit.return_value = None

        def override_get_tenant_id():
            return sample_tenant_id

        def override_get_db_tenant():
            yield mock_db

        async def override_get_suite_client():
            return mock_suite_client_ok

        expected_topic = (
            f"jfa/unify/{sample_tenant_id}/device/{sample_device_id}/access/response"
        )

        with patch("app.middleware.auth.verify_hmac_token") as mock_verify, \
             patch("app.routers.access.get_settings") as mock_settings_fn:

            mock_verify.return_value = {"tenant_id": str(sample_tenant_id)}
            mock_settings_obj = MagicMock()
            mock_settings_obj.suite_integration_enabled = True
            mock_settings_fn.return_value = mock_settings_obj

            app.dependency_overrides[get_tenant_id] = override_get_tenant_id
            app.dependency_overrides[get_db_tenant] = override_get_db_tenant
            app.dependency_overrides[get_suite_client] = override_get_suite_client

            # Injectar o MQTT service mockado no estado da app
            app.state.mqtt_service = mock_mqtt_svc

            client = _make_client_with_auth(app, sample_tenant_id)
            try:
                resp = client.post("/access/validate", json={
                    "device_id": str(sample_device_id),
                    "pin": "1234",
                    "suite_token_id": str(sample_token_id),
                    "suite_access_point_id": str(sample_access_point_id),
                })
            finally:
                app.dependency_overrides.clear()
                # Limpar state da app para não afectar outros testes
                if hasattr(app.state, "mqtt_service"):
                    del app.state.mqtt_service

        assert resp.status_code == 200
        data = resp.json()
        assert data["granted"] is True

        # Verificar que publish foi chamado com o tópico correcto
        mock_adapter.publish.assert_called_once()
        call_args = mock_adapter.publish.call_args
        published_topic = call_args.args[0] if call_args.args else call_args.kwargs.get("topic")
        assert published_topic == expected_topic, (
            f"Tópico publicado: {published_topic!r} != esperado: {expected_topic!r}"
        )

        # Verificar conteúdo do payload
        published_payload = call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get("payload")
        payload_dict = _json.loads(published_payload)
        assert payload_dict["action"] == "grant"
        assert payload_dict["device_id"] == str(sample_device_id)
        assert payload_dict["tenant_id"] == str(sample_tenant_id)
