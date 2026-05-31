"""
Testes E2E de RLS para routers com PostgreSQL real.

Validar que:
1. Endpoints usam get_db_tenant que activa SET LOCAL
2. RLS fail-closed: sem contexto = 403/404
3. RLS isolação: Tenant A não vê Tenant B (silencioso)
4. RLS WITH CHECK: INSERT alien falha com constraint violation
"""
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.auth import generate_hmac_token

pytestmark = pytest.mark.integration


@pytest.fixture(scope="session")
def client(setup_database):
    """TestClient com DATABASE_URL configurado antes da importação."""
    import sys
    # Remover módulos já carregados para forçar reload com DATABASE_URL correcto
    for mod in list(sys.modules.keys()):
        if mod.startswith("app."):
            del sys.modules[mod]

    from app.main import app
    return TestClient(app)


class TestRLSRoutersFailClosed:
    """Validar fail-closed sem contexto de autenticação."""

    def test_list_devices_without_auth_returns_401(self, client):
        """Sem token, GET /devices retorna 401."""
        response = client.get("/devices/")
        assert response.status_code == 401

    def test_get_device_without_auth_returns_401(self, client):
        """Sem token, GET /devices/{id} retorna 401."""
        fake_id = uuid.uuid4()
        response = client.get(f"/devices/{fake_id}")
        assert response.status_code == 401


class TestRLSRoutersIsolation:
    """Validar que RLS isola routers por tenant."""

    def test_tenant_a_sees_only_own_devices(
        self,
        client,
        db_superuser: Session,
        sample_tenant_a: uuid.UUID,
        sample_tenant_b: uuid.UUID,
        sample_device_a,
        sample_device_b,
    ):
        """Tenant A vê só seu device, não o de B."""
        token = generate_hmac_token({"tenant_id": str(sample_tenant_a)})
        response = client.get(
            "/devices/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        devices = response.json()
        assert len(devices) == 1, f"Tenant A deve ver 1 device, viu {len(devices)}"
        assert devices[0]["id"] == str(sample_device_a.id)

    def test_tenant_b_sees_only_own_devices(
        self,
        client,
        db_superuser: Session,
        sample_tenant_a: uuid.UUID,
        sample_tenant_b: uuid.UUID,
        sample_device_a,
        sample_device_b,
    ):
        """Tenant B vê só seu device, não o de A."""
        token = generate_hmac_token({"tenant_id": str(sample_tenant_b)})
        response = client.get(
            "/devices/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        devices = response.json()
        assert len(devices) == 1, f"Tenant B deve ver 1 device, viu {len(devices)}"
        assert devices[0]["id"] == str(sample_device_b.id)

    def test_tenant_a_cannot_access_tenant_b_device(
        self,
        client,
        db_superuser: Session,
        sample_tenant_a: uuid.UUID,
        sample_tenant_b: uuid.UUID,
        sample_device_a,
        sample_device_b,
    ):
        """Tenant A tenta aceder device de B — GET retorna 404 (RLS bloqueia)."""
        token = generate_hmac_token({"tenant_id": str(sample_tenant_a)})
        response = client.get(
            f"/devices/{sample_device_b.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        # RLS bloqueia a query, SQLAlchemy não encontra o device
        assert response.status_code == 404

    def test_create_device_with_wrong_tenant_id_fails(
        self,
        client,
        db_superuser: Session,
        sample_tenant_a: uuid.UUID,
        sample_tenant_b: uuid.UUID,
    ):
        """Tenant A tenta criar device com tenant_id de B — POST falha."""
        token = generate_hmac_token({"tenant_id": str(sample_tenant_a)})
        payload = {
            "tenant_id": str(sample_tenant_b),  # Alien tenant_id
            "name": "Alien Device",
            "device_type": "pin_pad",
            "mqtt_topic": "test/alien",
            "mqtt_backend": "tuya",
            "auth_mode": "pin",
            "card_uids": [],
        }
        response = client.post(
            "/devices/",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        # Middleware valida que token.tenant_id != payload.tenant_id
        assert response.status_code == 403


class TestRLSRoutersContextSwitching:
    """Validar que contexto muda corretamente entre pedidos."""

    def test_sequential_requests_different_tenants(
        self,
        client,
        db_superuser: Session,
        sample_tenant_a: uuid.UUID,
        sample_tenant_b: uuid.UUID,
        sample_device_a,
        sample_device_b,
    ):
        """Dois pedidos sequenciais — diferentes tenants, diferentes devices."""
        token_a = generate_hmac_token({"tenant_id": str(sample_tenant_a)})
        token_b = generate_hmac_token({"tenant_id": str(sample_tenant_b)})

        # Pedido 1: Tenant A
        response_a = client.get(
            "/devices/",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert response_a.status_code == 200
        devices_a = response_a.json()
        assert len(devices_a) == 1
        assert devices_a[0]["id"] == str(sample_device_a.id)

        # Pedido 2: Tenant B (mesma conexão do client)
        response_b = client.get(
            "/devices/",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert response_b.status_code == 200
        devices_b = response_b.json()
        assert len(devices_b) == 1
        assert devices_b[0]["id"] == str(sample_device_b.id)


class TestRLSRoutersE2E:
    """E2E: Criar device, validar acesso, tentar delete alien."""

    def test_create_and_list_own_device(
        self,
        client,
        db_superuser: Session,
        sample_tenant_a: uuid.UUID,
    ):
        """Criar device para Tenant A, depois listá-lo."""
        token = generate_hmac_token({"tenant_id": str(sample_tenant_a)})

        # Criar
        payload = {
            "tenant_id": str(sample_tenant_a),
            "name": "Test Device",
            "device_type": "pin_pad",
            "mqtt_topic": "test/e2e",
            "mqtt_backend": "tuya",
            "auth_mode": "pin",
            "card_uids": [],
        }
        create_response = client.post(
            "/devices/",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert create_response.status_code == 201
        created_device = create_response.json()
        device_id = created_device["id"]

        # Listar
        list_response = client.get(
            "/devices/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert list_response.status_code == 200
        devices = list_response.json()
        assert len(devices) == 1
        assert devices[0]["id"] == device_id

        # GET específico
        get_response = client.get(
            f"/devices/{device_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert get_response.status_code == 200
        assert get_response.json()["id"] == device_id
