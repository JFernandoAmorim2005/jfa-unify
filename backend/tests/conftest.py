"""
Fixtures pytest para testes do backend JFA Unify.

Estratégia de isolamento:
  - Testes unitários (access_control, mqtt): mocks de sessão SQLAlchemy.
  - SQLite em memória (TESTING=1) para testes HTTP.
  - Fixtures de dados usam SimpleNamespace para simular objectos ORM
    sem activar a instrumentação SQLAlchemy (que requer registry completo).

Para testes de integração com PostgreSQL real, definir DATABASE_URL no ambiente
e usar pytest-postgresql ou docker-compose separado.
"""
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock

from app.services.access_crypto import hash_pin_for_device
from app.services.mqtt_adapter import MQTTService, IMQTTAdapter

# Capturar a implementação REAL de verify_hmac_token ANTES do patch global.
# Testes unitários de auth.py precisam da função verdadeira (não do mock).
from app.services.auth import verify_hmac_token as _REAL_VERIFY_HMAC_TOKEN


def _make_client_with_auth(app, sample_tenant_id):
    """Wrapper que injeta header Authorization em todos os requests do TestClient."""
    from fastapi.testclient import TestClient

    client = TestClient(app, raise_server_exceptions=False)
    original_request = client.request

    def request_with_auth(*args, **kwargs):
        if 'headers' not in kwargs or kwargs['headers'] is None:
            kwargs['headers'] = {}
        # Preservar headers existentes e adicionar Authorization
        if 'Authorization' not in kwargs['headers']:
            kwargs['headers']['Authorization'] = f'Bearer {sample_tenant_id}'
        return original_request(*args, **kwargs)

    client.request = request_with_auth
    return client


def pytest_configure(config):
    """Mocka verify_hmac_token ANTES de qualquer import de app."""
    patch('app.services.auth.verify_hmac_token',
           return_value={"tenant_id": "00000000-0000-0000-0000-000000000001"}).start()


@pytest.fixture
def real_verify_hmac_token():
    """Expõe a implementação real de verify_hmac_token para testes unitários de auth."""
    return _REAL_VERIFY_HMAC_TOKEN


def _make_device(**kwargs) -> SimpleNamespace:
    """Cria objecto simples que simula um modelo InputDevice para testes unitários."""
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        name="Dispositivo de Teste",
        device_type="pin_pad",
        auth_mode="pin_only",
        pin_salt=b"\x00" * 32,
        pin_hash_algorithm="hmac_sha256",
        card_uids={},
        mqtt_topic="tuya/thing/device001/status",
        mqtt_backend="tuya",
        enabled=True,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# --- Mock da sessão de BD ---

@pytest.fixture
def db() -> MagicMock:
    """
    Sessão SQLAlchemy simulada para testes unitários.
    query().filter().first() retorna None por omissão — sobrescrever por teste.
    """
    mock_db = MagicMock()
    mock_db.query.return_value = mock_db
    mock_db.filter.return_value = mock_db
    mock_db.filter_by.return_value = mock_db
    mock_db.first.return_value = None
    mock_db.all.return_value = []
    mock_db.add.return_value = None
    mock_db.commit.return_value = None
    mock_db.refresh.return_value = None
    return mock_db


# --- Dados de teste ---

@pytest.fixture
def sample_tenant_id() -> uuid.UUID:
    """UUID fixo para o tenant de teste."""
    return uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
def sample_device_id() -> uuid.UUID:
    """UUID fixo para o dispositivo de teste."""
    return uuid.UUID("00000000-0000-0000-0000-000000000002")


@pytest.fixture
def pin_salt() -> bytes:
    """Salt fixo para testes determinísticos."""
    return b"\x00" * 32


@pytest.fixture
def sample_device_pin_only(
    sample_device_id: uuid.UUID,
    sample_tenant_id: uuid.UUID,
    pin_salt: bytes,
) -> SimpleNamespace:
    """Dispositivo de teste com autenticação por PIN."""
    return _make_device(
        id=sample_device_id,
        tenant_id=sample_tenant_id,
        name="PIN Pad Entrada Principal",
        device_type="pin_pad",
        auth_mode="pin_only",
        pin_salt=pin_salt,
        card_uids={"__pin__": hash_pin_for_device("1234", pin_salt)},
    )


@pytest.fixture
def sample_device_card_only(
    sample_device_id: uuid.UUID,
    sample_tenant_id: uuid.UUID,
    pin_salt: bytes,
) -> SimpleNamespace:
    """Dispositivo de teste com autenticação por cartão."""
    return _make_device(
        id=sample_device_id,
        tenant_id=sample_tenant_id,
        name="Leitor Cartão Entrada Lateral",
        device_type="card_reader",
        auth_mode="card_only",
        pin_salt=pin_salt,
        card_uids={"AABBCCDD": True, "11223344": True},
        mqtt_topic="tuya/thing/device002/status",
    )


@pytest.fixture
def mock_mqtt_client() -> MagicMock:
    """Mock do cliente MQTT para testes sem broker real."""
    mock = MagicMock()
    mock.is_connected = True
    mock.connect.return_value = None
    mock.disconnect.return_value = None
    mock.publish.return_value = None
    mock.subscribe.return_value = None
    return mock


# --- Mock do middleware de autenticação para testes ---

@pytest.fixture
def mock_verify_hmac_token(monkeypatch):
    """Mocka verify_hmac_token para testes HTTP que precisam de autenticação mockada.

    Não é autouse para evitar conflito com testes unitários (test_auth.py)
    que restauram a função real via inject_mock_settings.
    """
    def mock_verify(token):
        return {"tenant_id": "00000000-0000-0000-0000-000000000001"}

    monkeypatch.setattr(
        'app.services.auth.verify_hmac_token',
        mock_verify
    )


# --- Fixtures Async (pytest-asyncio) ---

@pytest_asyncio.fixture
async def mqtt_service():
    """MQTTService com adapter mockado para testes async."""
    mock_adapter = AsyncMock(spec=IMQTTAdapter)
    service = MQTTService(mock_adapter, session_factory=MagicMock)
    return service


# --- Fixtures para testes HTTP (TestClient) ---

@pytest.fixture
def override_get_tenant_id_func(sample_tenant_id: uuid.UUID):
    """Factory para override de get_tenant_id com tenant_id fixo."""
    def _override():
        return sample_tenant_id
    return _override


@pytest.fixture
def override_get_db_tenant_func(sample_device_pin_only: SimpleNamespace, db: MagicMock):
    """Factory para override de get_db_tenant com dispositivo mock."""
    def _override():
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = [sample_device_pin_only]
        mock_db.query.return_value.filter.return_value.first.return_value = sample_device_pin_only
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        yield mock_db
    return _override


@pytest.fixture
def client_with_overrides(override_get_tenant_id_func, override_get_db_tenant_func, sample_tenant_id):
    """TestClient com dependency_overrides e middleware mockado."""
    from unittest.mock import patch
    from app.main import app
    from app.middleware.auth import get_tenant_id
    from app.db.session import get_db_tenant

    # Mockar verify_hmac_token para aceitar sempre e retornar tenant_id
    with patch('app.middleware.auth.verify_hmac_token') as mock_verify:
        mock_verify.return_value = str(sample_tenant_id)

        # Aplicar overrides
        app.dependency_overrides[get_tenant_id] = override_get_tenant_id_func
        app.dependency_overrides[get_db_tenant] = override_get_db_tenant_func

        # Usar helper que injeta headers de autenticação
        client = _make_client_with_auth(app, sample_tenant_id)

        yield client

        # Limpar overrides após teste
        app.dependency_overrides.clear()
