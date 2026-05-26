"""
Fixtures pytest para testes do backend JFA Unify.

Estratégia de isolamento:
  - Testes unitários (access_control, mqtt): mocks de sessão SQLAlchemy.
  - Sem dependência de PostgreSQL ou SQLite em runtime — testes correm offline.
  - Fixtures de dados usam SimpleNamespace para simular objectos ORM
    sem activar a instrumentação SQLAlchemy (que requer registry completo).

Para testes de integração com PostgreSQL real, definir DATABASE_URL no ambiente
e usar pytest-postgresql ou docker-compose separado.
"""
import sys
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

# Mock database modules antes de qualquer import que dependa deles
sys.modules['app.db'] = MagicMock()
sys.modules['app.db.database'] = MagicMock()
sys.modules['app.models'] = MagicMock()
sys.modules['app.models.device'] = MagicMock()
sys.modules['app.models.access_log'] = MagicMock()

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from unittest.mock import AsyncMock  # noqa: E402

from app.services.access_crypto import hash_pin_for_device  # noqa: E402
from app.services.mqtt_adapter import MQTTService, IMQTTAdapter  # noqa: E402


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


# --- Fixtures Async (pytest-asyncio) ---

@pytest_asyncio.fixture
async def mqtt_service():
    """MQTTService com adapter mockado para testes async."""
    mock_adapter = AsyncMock(spec=IMQTTAdapter)
    service = MQTTService(mock_adapter, session_factory=MagicMock)
    return service
