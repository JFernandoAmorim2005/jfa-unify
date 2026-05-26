"""
Comprehensive async tests for MQTT adapters (Tuya and ESP32).
Matches Go adapter test coverage patterns.
"""
import asyncio
import json
import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, MagicMock

import pytest
import pytest_asyncio

# Mock database module before importing mqtt_adapter
sys.modules['app.db.database'] = MagicMock()
sys.modules['app.db'] = MagicMock()
sys.modules['app.models'] = MagicMock()
sys.modules['app.models.access_log'] = MagicMock()
sys.modules['app.models.device'] = MagicMock()

from app.services.mqtt_adapter import (
    TuyaAdapterAsync,
    ESP32AdapterAsync,
    MQTTService,
)


@pytest_asyncio.fixture
async def tuya_adapter():
    """Fixture for TuyaAdapterAsync."""
    adapter = TuyaAdapterAsync(
        broker_url="mqtt://test.mosquitto.org:1883",
        client_id="test_tuya_client",
        username="test_user",
        password="test_pass",
    )
    yield adapter


@pytest_asyncio.fixture
async def esp32_adapter():
    """Fixture for ESP32AdapterAsync."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        cache_path = Path(tmpdir) / "cache.db"
        adapter = ESP32AdapterAsync(
            broker_url="mqtt://192.168.1.100:1883",
            client_id="test_esp32_device",
            ble_fallback_enabled=True,
            local_cache_path=str(cache_path),
        )
        yield adapter


class TestTuyaAdapterAsync:
    """Test suite for TuyaAdapterAsync."""

    @pytest.mark.asyncio
    async def test_initialization(self, tuya_adapter):
        """Test adapter initialization."""
        assert tuya_adapter.broker_url == "mqtt://test.mosquitto.org:1883"
        assert tuya_adapter.client_id == "test_tuya_client"
        assert tuya_adapter.username == "test_user"
        assert tuya_adapter.password == "test_pass"
        assert not tuya_adapter._connected
        assert len(tuya_adapter._callbacks) == 0

    @pytest.mark.asyncio
    async def test_broker_url_parsing(self, tuya_adapter):
        """Test MQTT broker URL parsing."""
        assert tuya_adapter.broker_host == "test.mosquitto.org"
        assert tuya_adapter.broker_port == 1883

    @pytest.mark.asyncio
    async def test_broker_url_parsing_custom_port(self):
        """Test parsing custom MQTT broker port."""
        adapter = TuyaAdapterAsync(
            broker_url="mqtt://localhost:8883",
            client_id="client",
            username="user",
            password="pass",
        )
        assert adapter.broker_host == "localhost"
        assert adapter.broker_port == 8883

    @pytest.mark.asyncio
    async def test_is_connected_initial_state(self, tuya_adapter):
        """Test initial connection state."""
        connected = await tuya_adapter.is_connected()
        assert not connected

    @pytest.mark.asyncio
    async def test_get_status_initial(self, tuya_adapter):
        """Test initial status."""
        status = await tuya_adapter.get_status()
        assert not status["is_connected"]
        assert status["broker_url"] == "mqtt://test.mosquitto.org:1883"
        assert status["client_id"] == "test_tuya_client"
        assert status["buffered_messages"] == 0

    @pytest.mark.asyncio
    async def test_subscribe_stores_callback(self, tuya_adapter):
        """Test subscribe stores callback."""
        callback = AsyncMock()
        await tuya_adapter.subscribe("test/topic", callback)

        assert "test/topic" in tuya_adapter._callbacks
        assert tuya_adapter._callbacks["test/topic"] == callback

    @pytest.mark.asyncio
    async def test_subscribe_multiple_topics(self, tuya_adapter):
        """Test subscribing to multiple topics."""
        callback1 = AsyncMock()
        callback2 = AsyncMock()
        callback3 = AsyncMock()

        await tuya_adapter.subscribe("topic1", callback1)
        await tuya_adapter.subscribe("topic2", callback2)
        await tuya_adapter.subscribe("topic3", callback3)

        assert len(tuya_adapter._callbacks) == 3
        assert tuya_adapter._callbacks["topic1"] == callback1
        assert tuya_adapter._callbacks["topic2"] == callback2
        assert tuya_adapter._callbacks["topic3"] == callback3

    @pytest.mark.asyncio
    async def test_publish_when_disconnected(self, tuya_adapter):
        """Test publish logs warning when disconnected."""
        with patch("app.services.mqtt_adapter.logger") as mock_logger:
            await tuya_adapter.publish("test/topic", b"payload")
            mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_disconnect_without_client(self, tuya_adapter):
        """Test disconnect when client not initialized."""
        await tuya_adapter.disconnect()
        assert not tuya_adapter._connected


class TestESP32AdapterAsync:
    """Test suite for ESP32AdapterAsync."""

    @pytest.mark.asyncio
    async def test_initialization(self, esp32_adapter):
        """Test ESP32 adapter initialization."""
        assert esp32_adapter.broker_url == "mqtt://192.168.1.100:1883"
        assert esp32_adapter.client_id == "test_esp32_device"
        assert esp32_adapter.ble_fallback_enabled
        assert esp32_adapter.local_cache_path
        assert not esp32_adapter._connected
        assert not esp32_adapter._ble_fallback_active

    @pytest.mark.asyncio
    async def test_broker_url_parsing_local_ip(self, esp32_adapter):
        """Test local IP broker parsing."""
        assert esp32_adapter.broker_host == "192.168.1.100"
        assert esp32_adapter.broker_port == 1883

    @pytest.mark.asyncio
    async def test_default_local_cache_path(self):
        """Test default local cache path."""
        adapter = ESP32AdapterAsync(
            broker_url="mqtt://localhost:1883",
            client_id="test",
        )
        assert adapter.local_cache_path == "/tmp/jfa_mqtt_cache.db"

    @pytest.mark.asyncio
    async def test_cache_message_creates_table(self, esp32_adapter):
        """Test caching creates SQLite table."""
        await esp32_adapter._cache_message("jfa/device/hub_001/event/pin", b"test_payload")

        conn = sqlite3.connect(esp32_adapter.local_cache_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM cached_messages WHERE topic = ?",
            ("jfa/device/hub_001/event/pin",),
        )
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 1

    @pytest.mark.asyncio
    async def test_cache_multiple_messages(self, esp32_adapter):
        """Test caching multiple messages."""
        await esp32_adapter._cache_message("topic1", b"msg1")
        await esp32_adapter._cache_message("topic2", b"msg2")
        await esp32_adapter._cache_message("topic3", b"msg3")

        count = esp32_adapter._get_cached_message_count()
        assert count == 3

    @pytest.mark.asyncio
    async def test_get_cached_message_count(self, esp32_adapter):
        """Test retrieving cached message count."""
        assert esp32_adapter._get_cached_message_count() == 0

        await esp32_adapter._cache_message("topic1", b"msg1")
        assert esp32_adapter._get_cached_message_count() == 1

        await esp32_adapter._cache_message("topic2", b"msg2")
        assert esp32_adapter._get_cached_message_count() == 2

    @pytest.mark.asyncio
    async def test_cache_message_with_retry_tracking(self, esp32_adapter):
        """Test cache message tracks retry count."""
        await esp32_adapter._cache_message("test/topic", b"payload")

        conn = sqlite3.connect(esp32_adapter.local_cache_path)
        cursor = conn.cursor()
        cursor.execute("SELECT retry_count FROM cached_messages LIMIT 1")
        retry_count = cursor.fetchone()[0]
        conn.close()

        assert retry_count == 0

    @pytest.mark.asyncio
    async def test_is_connected_without_ble(self):
        """Test is_connected without BLE fallback."""
        adapter = ESP32AdapterAsync(
            broker_url="mqtt://localhost:1883",
            client_id="test",
            ble_fallback_enabled=False,
        )
        connected = await adapter.is_connected()
        assert not connected

    @pytest.mark.asyncio
    async def test_is_connected_ble_fallback_active(self, esp32_adapter):
        """Test is_connected returns True when BLE fallback active."""
        esp32_adapter._ble_fallback_active = True
        connected = await esp32_adapter.is_connected()
        assert connected

    @pytest.mark.asyncio
    async def test_get_status_initial(self, esp32_adapter):
        """Test initial status with ESP32."""
        status = await esp32_adapter.get_status()
        assert not status["is_connected"]
        assert not status["ble_fallback_active"]
        assert status["ble_fallback_enabled"]
        assert status["client_id"] == "test_esp32_device"
        assert status["buffered_messages"] == 0

    @pytest.mark.asyncio
    async def test_get_status_with_cached_messages(self, esp32_adapter):
        """Test status reports cached message count."""
        await esp32_adapter._cache_message("topic1", b"msg1")
        await esp32_adapter._cache_message("topic2", b"msg2")

        status = await esp32_adapter.get_status()
        assert status["buffered_messages"] == 2

    @pytest.mark.asyncio
    async def test_subscribe_stores_callback(self, esp32_adapter):
        """Test subscribe stores callback."""
        callback = AsyncMock()
        await esp32_adapter.subscribe("jfa/device/+/event/pin", callback)

        assert "jfa/device/+/event/pin" in esp32_adapter._callbacks

    @pytest.mark.asyncio
    async def test_disconnect_clears_ble_fallback_flag(self, esp32_adapter):
        """Test disconnect clears BLE fallback flag."""
        esp32_adapter._ble_fallback_active = True
        await esp32_adapter.disconnect()

        assert not esp32_adapter._ble_fallback_active


class TestMQTTServiceAsync:
    """Test suite for MQTTService async operations."""

    @pytest_asyncio.fixture
    async def mock_adapter(self):
        """Fixture for mock adapter."""
        adapter = AsyncMock()
        adapter.get_status = AsyncMock(return_value={"is_connected": True})
        return adapter

    @pytest.mark.asyncio
    async def test_mqtt_service_initialization(self, mock_adapter):
        """Test MQTTService initialization."""
        service = MQTTService(mock_adapter)
        assert service.adapter == mock_adapter
        assert not service._running

    @pytest.mark.asyncio
    async def test_mqtt_service_get_status(self, mock_adapter):
        """Test getting MQTT service status."""
        service = MQTTService(mock_adapter)
        status = await service.get_status()

        assert "service_running" in status
        assert "adapter_status" in status
        assert not status["service_running"]

    @pytest.mark.asyncio
    async def test_event_mapping_pin(self, mock_adapter):
        """Test PIN event type mapping."""
        service = MQTTService(mock_adapter)
        assert service._map_event_type("pin") == "pin_valid"
        assert service._map_event_type("pin_invalid") == "pin_invalid"

    @pytest.mark.asyncio
    async def test_event_mapping_card(self, mock_adapter):
        """Test card event type mapping."""
        service = MQTTService(mock_adapter)
        assert service._map_event_type("card") == "card_read"
        assert service._map_event_type("card_invalid") == "card_read"

    @pytest.mark.asyncio
    async def test_event_mapping_device_state(self, mock_adapter):
        """Test device state event mapping."""
        service = MQTTService(mock_adapter)
        assert service._map_event_type("state") == "device_state"

    @pytest.mark.asyncio
    async def test_event_mapping_ota(self, mock_adapter):
        """Test OTA firmware event mapping."""
        service = MQTTService(mock_adapter)
        assert service._map_event_type("ota") == "firmware_update"

    @pytest.mark.asyncio
    async def test_event_mapping_unknown(self, mock_adapter):
        """Test unknown event type mapping."""
        service = MQTTService(mock_adapter)
        assert service._map_event_type("unknown_type") == "unknown"

    @pytest.mark.asyncio
    async def test_on_pin_event_parsing(self, mock_adapter):
        """Test PIN event parsing."""
        service = MQTTService(mock_adapter)
        service.store_event = AsyncMock()

        event_payload = json.dumps({
            "event_id": "evt_123",
            "device_id": "dev_456",
            "event_type": "pin",
        }).encode()

        await service.on_pin_event("jfa/device/dev_456/event/pin", event_payload)
        service.store_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_card_event_parsing(self, mock_adapter):
        """Test card event parsing."""
        service = MQTTService(mock_adapter)
        service.store_event = AsyncMock()

        event_payload = json.dumps({
            "event_id": "evt_789",
            "device_id": "dev_456",
            "event_type": "card",
        }).encode()

        await service.on_card_event("jfa/device/dev_456/event/card", event_payload)
        service.store_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_invalid_json(self, mock_adapter):
        """Test handling invalid JSON."""
        service = MQTTService(mock_adapter)
        service.store_event = AsyncMock()

        with patch("app.services.mqtt_adapter.logger") as mock_logger:
            await service.on_pin_event("topic", b"invalid json")
            mock_logger.error.assert_called()


class TestConcurrentOperations:
    """Test concurrent async operations."""

    @pytest.mark.asyncio
    async def test_concurrent_subscribe(self, tuya_adapter):
        """Test concurrent subscriptions."""
        callbacks = [AsyncMock() for _ in range(10)]
        topics = [f"topic/{i}" for i in range(10)]

        await asyncio.gather(
            *[
                tuya_adapter.subscribe(topic, callback)
                for topic, callback in zip(topics, callbacks)
            ]
        )

        assert len(tuya_adapter._callbacks) == 10
        for topic in topics:
            assert topic in tuya_adapter._callbacks

    @pytest.mark.asyncio
    async def test_concurrent_cache_writes(self, esp32_adapter):
        """Test concurrent message caching."""
        tasks = [
            esp32_adapter._cache_message(f"topic{i}", f"msg{i}".encode())
            for i in range(10)
        ]

        await asyncio.gather(*tasks)

        count = esp32_adapter._get_cached_message_count()
        assert count == 10

    @pytest.mark.asyncio
    async def test_concurrent_publish(self, tuya_adapter):
        """Test concurrent publish operations."""
        tuya_adapter._connected = True
        tuya_adapter._client = MagicMock()
        tuya_adapter._client.publish.return_value.rc = 0

        tasks = [
            tuya_adapter.publish(f"topic{i}", f"msg{i}".encode())
            for i in range(10)
        ]

        await asyncio.gather(*tasks)
        assert tuya_adapter._client.publish.call_count == 10
