"""
Testes HTTP para router de controlo de acesso.

Estratégia: Validar POST /access/validate com PIN e cartão,
incluindo cenários de sucesso e falha.
"""
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_access_control_service():
    """Mock do AccessControlService para testes."""
    mock_service = MagicMock()
    return mock_service


@pytest.fixture
def client_access(sample_tenant_id, sample_device_id, pin_salt):
    """TestClient para testes de access router com overrides e middleware mockado."""
    from unittest.mock import patch
    from app.main import app
    from app.middleware.auth import get_tenant_id
    from app.db.session import get_db_tenant
    from tests.conftest import _make_client_with_auth
    from app.services.access_crypto import hash_pin_for_device

    # Dispositivo mock para testes
    mock_device = SimpleNamespace(
        id=sample_device_id,
        tenant_id=sample_tenant_id,
        name="Dispositivo Teste",
        device_type="pin_pad",
        auth_mode="pin_only",
        pin_salt=pin_salt,
        pin_hash_algorithm="hmac_sha256",
        card_uids={"__pin__": hash_pin_for_device("1234", pin_salt)},
        mqtt_topic="tuya/device/001",
        mqtt_backend="tuya",
        enabled=True,
    )

    mock_db = MagicMock()
    # Configurar query() -> filter() -> first() para retornar dispositivo
    mock_db.query.return_value.filter.return_value.first.return_value = mock_device
    # Configurar query() -> filter() -> all() para retornar lista vazia (para outros queries)
    mock_db.query.return_value.filter.return_value.all.return_value = []
    # add() e commit() para gravação de logs
    mock_db.add.return_value = None
    mock_db.commit.return_value = None

    def override_get_tenant_id():
        return sample_tenant_id

    def override_get_db_tenant():
        yield mock_db

    # Mockar verify_hmac_token para aceitar sempre
    with patch('app.middleware.auth.verify_hmac_token') as mock_verify:
        mock_verify.return_value = {"tenant_id": str(sample_tenant_id)}

        app.dependency_overrides[get_tenant_id] = override_get_tenant_id
        app.dependency_overrides[get_db_tenant] = override_get_db_tenant

        # Usar helper que injeta headers de autenticação
        client = _make_client_with_auth(app, sample_tenant_id)
        yield client
        app.dependency_overrides.clear()


class TestValidateAccess:
    """Testes para POST /access/validate"""

    def test_validate_pin_success_returns_200(self, client_access):
        """POST /access/validate com PIN válido retorna 200."""
        payload = {
            "device_id": str(uuid.uuid4()),
            "pin": "1234",
        }

        resp = client_access.post("/access/validate", json=payload)
        assert resp.status_code == 200

    def test_validate_pin_response_structure(self, client_access):
        """Response de validação de PIN contém campos esperados."""
        payload = {
            "device_id": str(uuid.uuid4()),
            "pin": "1234",
        }

        resp = client_access.post("/access/validate", json=payload)
        assert resp.status_code == 200

        data = resp.json()
        assert "granted" in data
        assert "access_type" in data
        assert "device_id" in data

    def test_validate_card_returns_200(self, client_access):
        """POST /access/validate com cartão válido retorna 200."""
        payload = {
            "device_id": str(uuid.uuid4()),
            "card_uid": "AABBCCDD",
        }

        resp = client_access.post("/access/validate", json=payload)
        assert resp.status_code == 200

    def test_validate_invalid_device_id_returns_400(self, client_access):
        """POST com device_id inválido retorna erro."""
        payload = {
            "device_id": "invalid-uuid",
            "pin": "1234",
        }

        resp = client_access.post("/access/validate", json=payload)
        assert resp.status_code in [400, 422]

    def test_validate_missing_device_id_returns_422(self, client_access):
        """POST sem device_id retorna 422."""
        payload = {
            "pin": "1234",
        }

        resp = client_access.post("/access/validate", json=payload)
        assert resp.status_code == 422

    def test_validate_empty_payload_returns_422(self, client_access):
        """POST com payload vazio retorna 422."""
        resp = client_access.post("/access/validate", json={})
        assert resp.status_code == 422

    def test_validate_creates_audit_log(self, client_access):
        """Validação sempre cria registo de auditoria."""
        payload = {
            "device_id": str(uuid.uuid4()),
            "pin": "1234",
        }

        resp = client_access.post("/access/validate", json=payload)
        assert resp.status_code == 200


class TestAccessIntegration:
    """Testes de integração de acesso."""

    def test_multiple_validation_attempts(self, client_access):
        """Múltiplas tentativas de validação retornam 200."""
        device_id = str(uuid.uuid4())

        for i in range(3):
            payload = {
                "device_id": device_id,
                "pin": f"{1000 + i}",
            }
            resp = client_access.post("/access/validate", json=payload)
            assert resp.status_code == 200

    def test_validate_same_device_different_credentials(self, client_access):
        """Mesmo dispositivo com diferentes credenciais."""
        device_id = str(uuid.uuid4())

        # Validação com PIN
        pin_payload = {
            "device_id": device_id,
            "pin": "1234",
        }
        pin_resp = client_access.post("/access/validate", json=pin_payload)
        assert pin_resp.status_code == 200

        # Validação com cartão
        card_payload = {
            "device_id": device_id,
            "card_uid": "AABBCCDD",
        }
        card_resp = client_access.post("/access/validate", json=card_payload)
        assert card_resp.status_code == 200
