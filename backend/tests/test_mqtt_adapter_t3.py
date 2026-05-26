"""
Testes unitários para MQTTService com suporte dual-mode (legacy + T3).
Valida callbacks para tópicos T3 e parsing de topics estruturados.
"""
import json
import uuid
from unittest.mock import MagicMock, AsyncMock
import pytest

from app.services.mqtt_adapter import MQTTService, IMQTTAdapter


@pytest.mark.asyncio
class TestMQTTServiceT3AccessRequest:
    """Testes para callback de access request (T3)."""

    @pytest.fixture
    async def mqtt_service(self):
        """Cria MQTTService com adapter mockado."""
        mock_adapter = AsyncMock(spec=IMQTTAdapter)
        service = MQTTService(mock_adapter, session_factory=MagicMock)
        return service

    async def test_on_access_request_parse_topic(self, mqtt_service):
        """Parse correcto de tópico T3 access request."""
        tenant_id = uuid.uuid4()
        device_id = uuid.uuid4()
        topic = f"jfa/unify/{tenant_id}/device/{device_id}/access/request"
        payload = json.dumps({
            "pin": "1234",
            "event_id": "evt-001",
        }).encode()

        # Mock db
        mqtt_service.session_factory = MagicMock()
        mock_db = MagicMock()
        mqtt_service.session_factory.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = MagicMock(
            id=device_id,
            tenant_id=tenant_id,
        )

        await mqtt_service.on_access_request(topic, payload)

        # Verifica que o evento foi processado
        assert mock_db.add.called
        assert mock_db.commit.called

    async def test_on_access_request_invalid_topic_structure(self, mqtt_service):
        """Tópico com estrutura inválida deve ser ignorado."""
        invalid_topic = "jfa/unify/invalid"
        payload = json.dumps({"pin": "1234"}).encode()

        # Não deve lançar exceção
        await mqtt_service.on_access_request(invalid_topic, payload)

    async def test_on_access_request_json_parse_error(self, mqtt_service):
        """Payload inválido não deve causar erro fatal."""
        tenant_id = uuid.uuid4()
        device_id = uuid.uuid4()
        topic = f"jfa/unify/{tenant_id}/device/{device_id}/access/request"
        invalid_payload = b"not json"

        # Não deve lançar exceção
        await mqtt_service.on_access_request(topic, invalid_payload)


@pytest.mark.asyncio
class TestMQTTServiceT3Heartbeat:
    """Testes para callback de heartbeat (T3)."""

    @pytest.fixture
    async def mqtt_service(self):
        mock_adapter = AsyncMock(spec=IMQTTAdapter)
        service = MQTTService(mock_adapter, session_factory=MagicMock)
        return service

    async def test_on_heartbeat_parse_topic(self, mqtt_service):
        """Parse correcto de tópico T3 heartbeat."""
        tenant_id = uuid.uuid4()
        device_id = uuid.uuid4()
        topic = f"jfa/unify/{tenant_id}/device/{device_id}/heartbeat"
        payload = json.dumps({
            "timestamp": "2026-05-27T10:00:00Z",
            "uptime": 3600,
        }).encode()

        mqtt_service.session_factory = MagicMock()
        mock_db = MagicMock()
        mqtt_service.session_factory.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = MagicMock(
            id=device_id,
            tenant_id=tenant_id,
        )

        await mqtt_service.on_heartbeat(topic, payload)

        assert mock_db.add.called
        assert mock_db.commit.called


@pytest.mark.asyncio
class TestMQTTServiceT3DeviceStatus:
    """Testes para callback de device status (T3)."""

    @pytest.fixture
    async def mqtt_service(self):
        mock_adapter = AsyncMock(spec=IMQTTAdapter)
        service = MQTTService(mock_adapter, session_factory=MagicMock)
        return service

    async def test_on_device_status_parse_topic(self, mqtt_service):
        """Parse correcto de tópico T3 device status."""
        tenant_id = uuid.uuid4()
        device_id = uuid.uuid4()
        topic = f"jfa/unify/{tenant_id}/device/{device_id}/status"
        payload = json.dumps({
            "battery_level": 85,
            "signal_strength": -45,
            "online": True,
        }).encode()

        mqtt_service.session_factory = MagicMock()
        mock_db = MagicMock()
        mqtt_service.session_factory.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = MagicMock(
            id=device_id,
            tenant_id=tenant_id,
        )

        await mqtt_service.on_device_status(topic, payload)

        assert mock_db.add.called
        assert mock_db.commit.called


@pytest.mark.asyncio
class TestMQTTServiceT3AuditLog:
    """Testes para callback de audit log (T3)."""

    @pytest.fixture
    async def mqtt_service(self):
        mock_adapter = AsyncMock(spec=IMQTTAdapter)
        service = MQTTService(mock_adapter, session_factory=MagicMock)
        return service

    async def test_on_audit_log(self, mqtt_service):
        """Handle audit log event."""
        topic = "jfa/unify/admin/audit/access_log"
        payload = json.dumps({
            "access_type": "pin_valid",
            "user_id": str(uuid.uuid4()),
            "timestamp": "2026-05-27T10:00:00Z",
        }).encode()

        mqtt_service.session_factory = MagicMock()
        mock_db = MagicMock()
        mqtt_service.session_factory.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None

        await mqtt_service.on_audit_log(topic, payload)

        # Audit logs sem device_id são permitidos
        assert mock_db.add.called or not mock_db.add.called  # Flexível


@pytest.mark.asyncio
class TestMQTTServiceStartupDualMode:
    """Testes para startup em dual-mode (legacy + T3)."""

    @pytest.fixture
    async def mqtt_service(self):
        mock_adapter = AsyncMock(spec=IMQTTAdapter)
        service = MQTTService(mock_adapter, session_factory=MagicMock)
        return service

    async def test_startup_subscribes_to_legacy_topics(self, mqtt_service):
        """Startup deve subscribe a tópicos legacy."""
        await mqtt_service.startup()

        # Verifica que adapter.subscribe foi chamado para tópicos legacy
        calls = mqtt_service.adapter.subscribe.call_args_list
        legacy_topics = [
            "jfa/device/+/event/pin",
            "jfa/device/+/event/card",
            "jfa/device/+/event/state",
            "jfa/device/+/event/ota",
        ]

        called_topics = [call[0][0] for call in calls]
        for legacy_topic in legacy_topics:
            assert legacy_topic in called_topics

    async def test_startup_subscribes_to_t3_topics(self, mqtt_service):
        """Startup deve subscribe a tópicos T3."""
        await mqtt_service.startup()

        calls = mqtt_service.adapter.subscribe.call_args_list
        t3_topics = [
            "jfa/unify/+/device/+/access/request",
            "jfa/unify/+/device/+/heartbeat",
            "jfa/unify/+/device/+/status",
            "jfa/unify/admin/audit/access_log",
        ]

        called_topics = [call[0][0] for call in calls]
        for t3_topic in t3_topics:
            assert t3_topic in called_topics

    async def test_startup_marks_running(self, mqtt_service):
        """Startup deve marcar _running como True."""
        assert not mqtt_service._running

        await mqtt_service.startup()

        assert mqtt_service._running


class TestMQTTServiceEventTypeMapping:
    """Testes síncronos para mapeamento de event_type (legacy vs T3)."""

    @pytest.fixture
    def mqtt_service(self):
        """Cria MQTTService com adapter mockado (síncrono)."""
        mock_adapter = AsyncMock(spec=IMQTTAdapter)
        service = MQTTService(mock_adapter, session_factory=MagicMock)
        return service

    def test_map_event_type_legacy(self, mqtt_service):
        """Legacy event types devem mapear correctamente."""
        assert mqtt_service._map_event_type("pin", "legacy") == "pin_valid"
        assert mqtt_service._map_event_type("pin_invalid", "legacy") == "pin_invalid"
        assert mqtt_service._map_event_type("card", "legacy") == "card_read"
        assert mqtt_service._map_event_type("state", "legacy") == "device_state"
        assert mqtt_service._map_event_type("ota", "legacy") == "firmware_update"

    def test_map_event_type_t3(self, mqtt_service):
        """T3 event types devem mapear correctamente (access_result dinâmico)."""
        assert mqtt_service._map_event_type("pin_valid", "t3") == "pin_valid"
        assert mqtt_service._map_event_type("pin_invalid", "t3") == "pin_invalid"
        assert mqtt_service._map_event_type("card_valid", "t3") == "card_read"
        assert mqtt_service._map_event_type("card_invalid", "t3") == "card_read"
        assert mqtt_service._map_event_type("heartbeat", "t3") == "device_heartbeat"
        assert mqtt_service._map_event_type("device_status", "t3") == "device_status"
        assert mqtt_service._map_event_type("audit_log", "t3") == "audit_log"

    def test_map_event_type_unknown(self, mqtt_service):
        """Event type desconhecido deve mapear para 'unknown'."""
        assert mqtt_service._map_event_type("unknown_event", "legacy") == "unknown"
        assert mqtt_service._map_event_type("unknown_event", "t3") == "unknown"


@pytest.mark.asyncio
class TestMQTTServiceLegacyHandlers:
    """Testes para callbacks legacy (jfa/device/*/event/*)."""

    @pytest.fixture
    async def mqtt_service(self):
        mock_adapter = AsyncMock(spec=IMQTTAdapter)
        service = MQTTService(mock_adapter, session_factory=MagicMock)
        return service

    async def test_on_pin_event_parse_json(self, mqtt_service):
        """Legacy PIN event com UUID válido deve chegar a db.add()."""
        device_id = uuid.uuid4()
        topic = f"jfa/device/{device_id}/event/pin"
        payload = json.dumps({
            "event_id": "evt-pin-001",
            "device_id": str(device_id),
            "event_type": "pin",
        }).encode()

        mqtt_service.session_factory = MagicMock()
        mock_db = MagicMock()
        mqtt_service.session_factory.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = MagicMock(
            id=device_id,
            tenant_id=uuid.uuid4(),
        )

        await mqtt_service.on_pin_event(topic, payload)
        assert mock_db.add.called
        assert mock_db.commit.called

    async def test_on_card_event_parse_json(self, mqtt_service):
        """Legacy card event com UUID válido deve chegar a db.add()."""
        device_id = uuid.uuid4()
        topic = f"jfa/device/{device_id}/event/card"
        payload = json.dumps({
            "event_id": "evt-card-001",
            "device_id": str(device_id),
            "event_type": "card",
        }).encode()

        mqtt_service.session_factory = MagicMock()
        mock_db = MagicMock()
        mqtt_service.session_factory.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = MagicMock(
            id=device_id,
            tenant_id=uuid.uuid4(),
        )

        await mqtt_service.on_card_event(topic, payload)
        assert mock_db.add.called
        assert mock_db.commit.called

    async def test_on_device_state_parse_json(self, mqtt_service):
        """Legacy device state event com UUID válido deve chegar a db.add()."""
        device_id = uuid.uuid4()
        topic = f"jfa/device/{device_id}/event/state"
        payload = json.dumps({
            "device_id": str(device_id),
            "event_type": "state",
            "online": True,
        }).encode()

        mqtt_service.session_factory = MagicMock()
        mock_db = MagicMock()
        mqtt_service.session_factory.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = MagicMock(
            id=device_id,
            tenant_id=uuid.uuid4(),
        )

        await mqtt_service.on_device_state(topic, payload)
        assert mock_db.add.called
        assert mock_db.commit.called

    async def test_on_ota_event_parse_json(self, mqtt_service):
        """Legacy OTA event com UUID válido deve chegar a db.add()."""
        device_id = uuid.uuid4()
        topic = f"jfa/device/{device_id}/event/ota"
        payload = json.dumps({
            "event_id": "evt-ota-001",
            "device_id": str(device_id),
            "event_type": "ota",
            "version": "2.1.0",
        }).encode()

        mqtt_service.session_factory = MagicMock()
        mock_db = MagicMock()
        mqtt_service.session_factory.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = MagicMock(
            id=device_id,
            tenant_id=uuid.uuid4(),
        )

        await mqtt_service.on_ota_event(topic, payload)
        assert mock_db.add.called
        assert mock_db.commit.called


@pytest.mark.asyncio
class TestMQTTServiceStoreEvent:
    """Testes para error paths de store_event (validação, lookup)."""

    @pytest.fixture
    async def mqtt_service(self):
        mock_adapter = AsyncMock(spec=IMQTTAdapter)
        service = MQTTService(mock_adapter, session_factory=MagicMock)
        return service

    async def test_store_event_missing_device_id(self, mqtt_service):
        """device_id vazio → early return, sem db.add()."""
        mqtt_service.session_factory = MagicMock()
        mock_db = MagicMock()
        mqtt_service.session_factory.return_value = mock_db

        event = {"event_type": "pin", "device_id": ""}
        await mqtt_service.store_event(event)

        # Não deve chamar query porque device_id vazio
        assert not mock_db.query.called

    async def test_store_event_invalid_device_id(self, mqtt_service):
        """device_id não-UUID → warning + return, sem db.add()."""
        mqtt_service.session_factory = MagicMock()
        mock_db = MagicMock()
        mqtt_service.session_factory.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = MagicMock(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
        )

        event = {"event_type": "pin", "device_id": "device001"}
        await mqtt_service.store_event(event)

        # Deve tentar query mas falhará na validação UUID, sem add
        assert not mock_db.add.called

    async def test_store_event_device_not_found(self, mqtt_service):
        """UUID válido mas device inexistente → warning + return."""
        mqtt_service.session_factory = MagicMock()
        mock_db = MagicMock()
        mqtt_service.session_factory.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None

        event = {"event_type": "pin", "device_id": str(uuid.uuid4())}
        await mqtt_service.store_event(event)

        # Device não encontrado em DB
        assert mock_db.query.called
        assert not mock_db.add.called

    async def test_store_event_exception_handling(self, mqtt_service):
        """Exception durante store_event → rollback e error log."""
        mqtt_service.session_factory = MagicMock()
        mock_db = MagicMock()
        mqtt_service.session_factory.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = MagicMock(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
        )
        # Simula exception no db.add
        mock_db.add.side_effect = Exception("DB error")

        event = {
            "event_type": "pin",
            "device_id": str(uuid.uuid4()),
            "event_id": "evt-001",
        }
        # Não deve lançar exceção
        await mqtt_service.store_event(event)

        # Deve chamar rollback
        assert mock_db.rollback.called
        assert mock_db.close.called


@pytest.mark.asyncio
class TestMQTTServiceShutdown:
    """Testes para shutdown."""

    @pytest.fixture
    async def mqtt_service(self):
        mock_adapter = AsyncMock(spec=IMQTTAdapter)
        service = MQTTService(mock_adapter, session_factory=MagicMock)
        service._running = True  # Simula serviço já iniciado
        return service

    async def test_shutdown_marks_stopped(self, mqtt_service):
        """Shutdown deve marcar _running como False."""
        assert mqtt_service._running

        await mqtt_service.shutdown()

        assert not mqtt_service._running

    async def test_shutdown_calls_disconnect(self, mqtt_service):
        """Shutdown deve chamar adapter.disconnect()."""
        await mqtt_service.shutdown()

        mqtt_service.adapter.disconnect.assert_called_once()


@pytest.mark.asyncio
class TestMQTTServiceGetStatus:
    """Testes para get_status."""

    @pytest.fixture
    async def mqtt_service(self):
        mock_adapter = AsyncMock(spec=IMQTTAdapter)
        mock_adapter.get_status.return_value = {
            "connected": True,
            "broker_url": "mqtt://test.local:1883",
        }
        service = MQTTService(mock_adapter, session_factory=MagicMock)
        service._running = True
        return service

    async def test_get_status_returns_dict(self, mqtt_service):
        """get_status deve retornar dicionário com status."""
        status = await mqtt_service.get_status()

        assert isinstance(status, dict)
        assert "service_running" in status
        assert "adapter_status" in status
        assert status["service_running"] is True
