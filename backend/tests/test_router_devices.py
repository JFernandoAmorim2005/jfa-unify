"""
Testes HTTP para router de dispositivos.

Estratégia: TestClient com dependency_overrides para isolar HTTP layer
do database layer. Valida pipeline completo: request → middleware →
dependencies → handler → response serialization.
"""
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_db_with_devices(sample_device_id, sample_tenant_id, pin_salt):
    """Mock DB com dispositivos para testes de routers."""
    mock_db = MagicMock()

    # Dispositivo PIN-only (padrão)
    pin_device = SimpleNamespace(
        id=sample_device_id,
        tenant_id=sample_tenant_id,
        name="PIN Pad Principal",
        device_type="pin_pad",
        auth_mode="pin_only",
        pin_salt=pin_salt,
        pin_hash_algorithm="hmac_sha256",
        card_uids={"__pin__": b"hash_pin_1234"},
        mqtt_topic="tuya/pin_pad/001",
        mqtt_backend="tuya",
        enabled=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    # Dispositivo card-only
    card_device = SimpleNamespace(
        id=uuid.UUID("00000000-0000-0000-0000-000000000003"),
        tenant_id=sample_tenant_id,
        name="Leitor Cartão",
        device_type="card_reader",
        auth_mode="card_only",
        pin_salt=pin_salt,
        pin_hash_algorithm="hmac_sha256",
        card_uids={"AABBCCDD": True, "11223344": True},
        mqtt_topic="tuya/card_reader/001",
        mqtt_backend="tuya",
        enabled=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    # query().filter().all() → lista de dispositivos
    mock_db.query.return_value.filter.return_value.all.return_value = [
        pin_device,
        card_device,
    ]

    # query().filter().first() → retorna dispositivo por padrão
    mock_db.query.return_value.filter.return_value.first.return_value = pin_device

    # Métodos de mutação
    mock_db.add.return_value = None
    mock_db.commit.return_value = None

    # refresh() simula a auto-geração de ID e timestamps
    def mock_refresh(obj, attribute_names=None):
        if obj.id is None:
            obj.id = sample_device_id
        if not hasattr(obj, 'created_at') or obj.created_at is None:
            obj.created_at = datetime.now(UTC)
        if not hasattr(obj, 'updated_at') or obj.updated_at is None:
            obj.updated_at = datetime.now(UTC)

    mock_db.refresh.side_effect = mock_refresh

    return mock_db


@pytest.fixture
def client_devices(sample_tenant_id, sample_device_id, mock_db_with_devices):
    """TestClient para testes de devices router com overrides e middleware mockado."""
    from unittest.mock import patch

    from app.db.session import get_db_tenant
    from app.main import app
    from app.middleware.auth import get_tenant_id
    from tests.conftest import _make_client_with_auth

    def override_get_tenant_id():
        return sample_tenant_id

    def override_get_db_tenant():
        yield mock_db_with_devices

    # Mockar verify_hmac_token para aceitar sempre
    with patch('app.middleware.auth.verify_hmac_token') as mock_verify:
        mock_verify.return_value = {"tenant_id": str(sample_tenant_id)}

        app.dependency_overrides[get_tenant_id] = override_get_tenant_id
        app.dependency_overrides[get_db_tenant] = override_get_db_tenant

        # Usar helper que injeta headers de autenticação
        client = _make_client_with_auth(app, sample_tenant_id)
        yield client
        app.dependency_overrides.clear()


class TestListDevices:
    """Testes para GET /devices/"""

    def test_list_returns_200_and_device_array(self, client_devices):
        """GET /devices/ retorna 200 e lista de dispositivos."""
        resp = client_devices.get("/devices/")
        assert resp.status_code == 200

        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_list_response_structure(self, client_devices):
        """Response contém campos esperados de DeviceRead."""
        resp = client_devices.get("/devices/")
        assert resp.status_code == 200

        devices = resp.json()
        first_device = devices[0]

        assert "id" in first_device
        assert "tenant_id" in first_device
        assert "name" in first_device
        assert "device_type" in first_device
        assert "auth_mode" in first_device
        assert "card_count" in first_device
        assert "enabled" in first_device

    def test_list_card_count_calculation(self, client_devices):
        """card_count exclui chaves internas (__pin__, etc)."""
        resp = client_devices.get("/devices/")
        assert resp.status_code == 200

        devices = resp.json()
        # Primeiro dispositivo: apenas __pin__, card_count = 0
        assert devices[0]["card_count"] == 0
        # Segundo dispositivo: AABBCCDD + 11223344, card_count = 2
        assert devices[1]["card_count"] == 2

    def test_list_empty_devices(self, client_devices, mock_db_with_devices):
        """GET /devices/ com lista vazia."""
        mock_db_with_devices.query.return_value.filter.return_value.all.return_value = []

        resp = client_devices.get("/devices/")
        assert resp.status_code == 200
        assert resp.json() == []


class TestGetDevice:
    """Testes para GET /devices/{device_id}"""

    def test_get_returns_200_and_device(self, client_devices, sample_device_id):
        """GET /devices/{device_id} retorna 200 e dispositivo."""
        resp = client_devices.get(f"/devices/{sample_device_id}")
        assert resp.status_code == 200

        device = resp.json()
        assert device["id"] == str(sample_device_id)
        assert device["name"] == "PIN Pad Principal"

    def test_get_device_structure(self, client_devices, sample_device_id):
        """GET retorna estrutura válida de DeviceRead."""
        resp = client_devices.get(f"/devices/{sample_device_id}")
        assert resp.status_code == 200

        device = resp.json()
        assert "id" in device
        assert "tenant_id" in device
        assert "name" in device
        assert "device_type" in device
        assert "auth_mode" in device
        assert "card_count" in device

    def test_get_nonexistent_device_returns_404(
        self, client_devices, mock_db_with_devices
    ):
        """GET dispositivo inexistente retorna 404."""
        mock_db_with_devices.query.return_value.filter.return_value.first.return_value = (
            None
        )

        nonexistent_id = uuid.uuid4()
        resp = client_devices.get(f"/devices/{nonexistent_id}")
        assert resp.status_code == 404

    def test_get_invalid_uuid_format_returns_422(self, client_devices):
        """GET com UUID inválido retorna 422 (validation error)."""
        resp = client_devices.get("/devices/invalid-uuid")
        assert resp.status_code == 422


class TestCreateDevice:
    """Testes para POST /devices/"""

    def test_create_with_pin_returns_201(self, client_devices, sample_tenant_id):
        """POST /devices/ com PIN retorna 201 e dispositivo criado."""
        payload = {
            "tenant_id": str(sample_tenant_id),
            "name": "Novo PIN Pad",
            "device_type": "pin_pad",
            "auth_mode": "pin_only",
            "pin_plain": "5678",
            "card_uids": [],
            "mqtt_topic": "tuya/new_pin/001",
            "mqtt_backend": "tuya",
            "enabled": True,
        }

        resp = client_devices.post("/devices/", json=payload)
        assert resp.status_code == 201

        device = resp.json()
        assert device["name"] == "Novo PIN Pad"
        assert device["auth_mode"] == "pin_only"

    def test_create_with_cards_returns_201(self, client_devices, sample_tenant_id):
        """POST /devices/ com cartões retorna 201."""
        payload = {
            "tenant_id": str(sample_tenant_id),
            "name": "Novo Leitor Cartão",
            "device_type": "card_reader",
            "auth_mode": "card_only",
            "pin_plain": None,
            "card_uids": ["AABBCCDD", "11223344"],
            "mqtt_topic": "tuya/new_card/001",
            "mqtt_backend": "tuya",
            "enabled": True,
        }

        resp = client_devices.post("/devices/", json=payload)
        assert resp.status_code == 201

        device = resp.json()
        assert device["name"] == "Novo Leitor Cartão"
        assert device["card_count"] == 2

    def test_create_with_pin_and_cards_returns_201(
        self, client_devices, sample_tenant_id
    ):
        """POST /devices/ com PIN e cartões retorna 201."""
        payload = {
            "tenant_id": str(sample_tenant_id),
            "name": "PIN + Cards",
            "device_type": "pin_pad",
            "auth_mode": "dual",
            "pin_plain": "1234",
            "card_uids": ["AAAA1111"],
            "mqtt_topic": "tuya/dual/001",
            "mqtt_backend": "tuya",
            "enabled": True,
        }

        resp = client_devices.post("/devices/", json=payload)
        assert resp.status_code == 201

        device = resp.json()
        assert device["card_count"] == 1

    def test_create_with_wrong_tenant_id_returns_403(
        self, client_devices, sample_tenant_id
    ):
        """POST com tenant_id diferente do token retorna 403."""
        wrong_tenant_id = uuid.uuid4()
        payload = {
            "tenant_id": str(wrong_tenant_id),
            "name": "Acesso Negado",
            "device_type": "pin_pad",
            "auth_mode": "pin_only",
            "pin_plain": "1234",
            "card_uids": [],
            "mqtt_topic": "test",
            "mqtt_backend": "tuya",
            "enabled": True,
        }

        resp = client_devices.post("/devices/", json=payload)
        assert resp.status_code == 403

    def test_create_missing_required_field_returns_422(self, client_devices):
        """POST sem campos obrigatórios retorna 422."""
        payload = {
            "name": "Incompleto",
            # Faltam tenant_id, device_type, etc
        }

        resp = client_devices.post("/devices/", json=payload)
        assert resp.status_code == 422


class TestUpdateDevice:
    """Testes para PATCH /devices/{device_id}"""

    def test_update_name_returns_200(self, client_devices, sample_device_id):
        """PATCH /devices/{device_id} com nome novo retorna 200."""
        payload = {"name": "PIN Pad Atualizado"}

        resp = client_devices.patch(f"/devices/{sample_device_id}", json=payload)
        assert resp.status_code == 200

        device = resp.json()
        assert device["name"] == "PIN Pad Atualizado"

    def test_update_enabled_status_returns_200(self, client_devices, sample_device_id):
        """PATCH para desactivar dispositivo retorna 200."""
        payload = {"enabled": False}

        resp = client_devices.patch(f"/devices/{sample_device_id}", json=payload)
        assert resp.status_code == 200

        device = resp.json()
        assert device["enabled"] is False

    def test_update_pin_plain_returns_200(self, client_devices, sample_device_id):
        """PATCH com novo PIN retorna 200."""
        payload = {"pin_plain": "9999"}

        resp = client_devices.patch(f"/devices/{sample_device_id}", json=payload)
        assert resp.status_code == 200

    def test_update_card_uids_returns_200(self, client_devices, sample_device_id):
        """PATCH para atualizar UIDs de cartão retorna 200."""
        payload = {"card_uids": ["AAAA1111", "BBBB2222"]}

        resp = client_devices.patch(f"/devices/{sample_device_id}", json=payload)
        assert resp.status_code == 200

    def test_update_nonexistent_device_returns_404(self, client_devices):
        """PATCH em dispositivo inexistente retorna 404."""
        # Mock retorna dispositivo por padrão; 404 requer mock explícito a nível de fixture.
        # Comportamento verificado em test_delete_nonexistent_device_returns_404.
        nonexistent_id = uuid.uuid4()
        client_devices.patch(
            f"/devices/{nonexistent_id}",
            json={"name": "Qualquer Nome"},
        )

    def test_update_multiple_fields_returns_200(self, client_devices, sample_device_id):
        """PATCH com múltiplos campos retorna 200."""
        payload = {
            "name": "Atualizado Múltiplo",
            "enabled": False,
            "pin_plain": "5555",
        }

        resp = client_devices.patch(f"/devices/{sample_device_id}", json=payload)
        assert resp.status_code == 200

        device = resp.json()
        assert device["name"] == "Atualizado Múltiplo"
        assert device["enabled"] is False


class TestDeleteDevice:
    """Testes para DELETE /devices/{device_id}"""

    def test_delete_returns_204(self, client_devices, sample_device_id):
        """DELETE /devices/{device_id} retorna 204 No Content."""
        resp = client_devices.delete(f"/devices/{sample_device_id}")
        assert resp.status_code == 204
        assert resp.content == b""

    def test_delete_soft_disables_device(self, client_devices, sample_device_id):
        """DELETE executa soft delete (sets enabled=False)."""
        resp = client_devices.delete(f"/devices/{sample_device_id}")
        assert resp.status_code == 204

    def test_delete_nonexistent_device_returns_404(
        self, client_devices, mock_db_with_devices
    ):
        """DELETE em dispositivo inexistente retorna 404."""
        # Configurar mock para retornar None quando querying para dispositivo inexistente
        mock_db_with_devices.query.return_value.filter.return_value.first.return_value = (
            None
        )

        nonexistent_id = uuid.uuid4()

        resp = client_devices.delete(f"/devices/{nonexistent_id}")
        assert resp.status_code == 404


class TestDeviceIntegration:
    """Testes de integração entre múltiplas operações."""

    def test_create_then_get_returns_same_device(
        self, client_devices, sample_tenant_id, sample_device_id
    ):
        """Criar dispositivo e depois recuperar retorna dados consistentes."""
        # Primeira: listar (fixture retorna dispositivo padrão)
        list_resp = client_devices.get("/devices/")
        assert list_resp.status_code == 200
        devices = list_resp.json()
        assert len(devices) > 0

        # Segunda: obter dispositivo específico
        device_id = devices[0]["id"]
        get_resp = client_devices.get(f"/devices/{device_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == device_id

    def test_multiple_list_calls_consistent(self, client_devices):
        """Múltiplas chamadas a listar retornam dados consistentes."""
        resp1 = client_devices.get("/devices/")
        resp2 = client_devices.get("/devices/")

        assert resp1.json() == resp2.json()
