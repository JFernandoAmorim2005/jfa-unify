"""
FastAPI integration layer for MQTT adapters (Tuya, ESP32).
Provides async interface and dependency injection pattern.
"""
import asyncio
import json
import logging
import sqlite3
import uuid
from abc import ABC, abstractmethod
from typing import Optional, Callable, Dict, Any
from urllib.parse import urlparse

from app.db.database import SessionLocal
from app.models.access_log import AccessLog
from app.models.device import InputDevice
from app.services.mqtt_topics import TopicBuilder, LegacyTopicBuilder  # noqa: F401

logger = logging.getLogger(__name__)

# Type alias for async message callback
MessageCallback = Callable[[str, bytes], Any]


class IMQTTAdapter(ABC):
    """Async MQTT adapter interface for FastAPI integration."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to MQTT broker."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Gracefully close MQTT connection."""
        pass

    @abstractmethod
    async def is_connected(self) -> bool:
        """Check if adapter is connected."""
        pass

    @abstractmethod
    async def publish(self, topic: str, payload: bytes, qos: int = 1) -> None:
        """Publish message to topic."""
        pass

    @abstractmethod
    async def subscribe(self, topic: str, callback: MessageCallback) -> None:
        """Subscribe to topic with callback."""
        pass

    @abstractmethod
    async def get_status(self) -> Dict[str, Any]:
        """Get adapter connection status."""
        pass


class TuyaAdapterAsync(IMQTTAdapter):
    """Async wrapper for Tuya MQTT adapter (Year 1-2) using paho-mqtt."""

    def __init__(self, broker_url: str, client_id: str, username: str, password: str):
        self.broker_url = broker_url
        self.client_id = client_id
        self.username = username
        self.password = password
        self._connected = False
        self._callbacks: Dict[str, MessageCallback] = {}
        self._client = None
        self._connect_event: Optional[asyncio.Event] = None
        self._loop = None
        self._buffer: list = []

        # Parse broker URL
        parsed = urlparse(broker_url)
        self.broker_host = parsed.hostname or "localhost"
        self.broker_port = parsed.port or 1883

        logger.info(f"TuyaAdapterAsync initialized: {broker_url}")

    async def connect(self) -> None:
        """Connect to Tuya MQTT broker with retry logic."""
        import paho.mqtt.client as mqtt

        self._loop = asyncio.get_event_loop()
        self._connect_event = asyncio.Event()

        def on_connect(client, userdata, flags, rc, properties=None):
            if rc == 0:
                self._connected = True
                logger.info(f"TuyaAdapterAsync connected to {self.broker_url}")
                # Resubscribe to all topics
                for topic in self._callbacks.keys():
                    client.subscribe(topic, qos=1)
                # Flush buffered messages
                if self._buffer and self._loop:
                    asyncio.run_coroutine_threadsafe(self._flush_buffer(), self._loop)
                if self._connect_event:
                    self._connect_event.set()
            else:
                logger.error(f"Connection failed with code {rc}")
                self._connected = False

        def on_disconnect(client, userdata, flags, rc, properties=None):
            self._connected = False
            if rc != 0:
                logger.warning(f"Unexpected disconnection with code {rc}")

        def on_message(client, userdata, msg):
            topic = msg.topic
            if topic in self._callbacks:
                try:
                    # Run callback in asyncio context from paho-mqtt thread
                    asyncio.run_coroutine_threadsafe(self._callbacks[topic](topic, msg.payload), self._loop)
                except Exception as e:
                    logger.error(f"Error in message callback: {e}")

        try:
            self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, self.client_id)
            self._client.reconnect_delay_set(min_delay=1, max_delay=30)
            self._client.on_connect = on_connect
            self._client.on_disconnect = on_disconnect
            self._client.on_message = on_message

            if self.username:
                self._client.username_pw_set(self.username, self.password)

            self._client.connect(self.broker_host, self.broker_port, keepalive=60)
            self._client.loop_start()

            # Wait for connection with timeout
            await asyncio.wait_for(self._connect_event.wait(), timeout=10.0)

        except asyncio.TimeoutError:
            logger.error("Connection timeout to Tuya broker")
            self._connected = False
            if self._client:
                self._client.loop_stop()
            raise
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            self._connected = False
            if self._client:
                self._client.loop_stop()
            raise

    async def disconnect(self) -> None:
        """Disconnect from Tuya broker."""
        try:
            if self._client:
                self._client.disconnect()
                self._client.loop_stop()
            self._connected = False
            logger.info("TuyaAdapterAsync disconnected")
        except Exception as e:
            logger.error(f"Disconnect error: {e}")

    async def is_connected(self) -> bool:
        """Check connection status."""
        return self._connected and self._client is not None and self._client.is_connected()

    async def publish(self, topic: str, payload: bytes, qos: int = 1) -> None:
        """Publish message to topic."""
        if not self._connected or not self._client:
            logger.warning(f"Not connected, buffering message to {topic}")
            self._buffer.append((topic, payload, qos))
            return

        try:
            info = self._client.publish(topic, payload, qos=qos)
            if info.rc != 0:
                logger.warning(f"Publish returned code {info.rc}")
            logger.debug(f"Publishing to {topic}: {len(payload)} bytes")
        except Exception as e:
            logger.error(f"Publish error: {e}")

    async def _flush_buffer(self) -> None:
        """Flush buffered messages after reconnection."""
        while self._buffer and self._connected and self._client:
            try:
                topic, payload, qos = self._buffer.pop(0)
                info = self._client.publish(topic, payload, qos=qos)
                if info.rc != 0:
                    logger.warning(f"Flush publish returned code {info.rc}")
                logger.debug(f"Flushed message to {topic}")
            except Exception as e:
                logger.error(f"Error flushing buffer: {e}")
                break

    async def subscribe(self, topic: str, callback: MessageCallback) -> None:
        """Subscribe to topic."""
        self._callbacks[topic] = callback

        if self._connected and self._client:
            try:
                self._client.subscribe(topic, qos=1)
            except Exception as e:
                logger.error(f"Subscribe error: {e}")

        logger.info(f"Subscribed to {topic}")

    async def get_status(self) -> Dict[str, Any]:
        """Get adapter status."""
        return {
            "is_connected": self._connected,
            "broker_url": self.broker_url,
            "client_id": self.client_id,
            "buffered_messages": 0,
        }


class ESP32AdapterAsync(IMQTTAdapter):
    """Async wrapper for ESP32-S3 MQTT adapter (Year 3+) with local cache and BLE fallback."""

    def __init__(
        self,
        broker_url: str,
        client_id: str,
        ble_fallback_enabled: bool = False,
        local_cache_path: Optional[str] = None,
    ):
        self.broker_url = broker_url
        self.client_id = client_id
        self.ble_fallback_enabled = ble_fallback_enabled
        self.local_cache_path = local_cache_path or "/tmp/jfa_mqtt_cache.db"
        self._connected = False
        self._callbacks: Dict[str, MessageCallback] = {}
        self._client = None
        self._connect_event: Optional[asyncio.Event] = None
        self._ble_fallback_active = False
        self._loop = None

        # Parse broker URL
        parsed = urlparse(broker_url)
        self.broker_host = parsed.hostname or "localhost"
        self.broker_port = parsed.port or 1883

        logger.info(f"ESP32AdapterAsync initialized: {broker_url}")

    async def connect(self) -> None:
        """Connect to ESP32 local MQTT broker with fallback to BLE if enabled."""
        import paho.mqtt.client as mqtt

        self._loop = asyncio.get_event_loop()
        self._connect_event = asyncio.Event()

        def on_connect(client, userdata, flags, rc, properties=None):
            if rc == 0:
                self._connected = True
                self._ble_fallback_active = False
                logger.info(f"ESP32AdapterAsync connected to {self.broker_url}")
                # Resubscribe to all topics
                for topic in self._callbacks.keys():
                    client.subscribe(topic, qos=1)
                # Flush cached messages
                if self._loop:
                    asyncio.run_coroutine_threadsafe(self._flush_cache(), self._loop)
                if self._connect_event:
                    self._connect_event.set()
            else:
                logger.error(f"Connection failed with code {rc}")
                self._connected = False

        def on_disconnect(client, userdata, flags, rc, properties=None):
            self._connected = False
            if rc != 0:
                logger.warning(f"Unexpected disconnection with code {rc}")
                if self.ble_fallback_enabled:
                    logger.info("Triggering BLE fallback mode")
                    self._ble_fallback_active = True

        def on_message(client, userdata, msg):
            topic = msg.topic
            if topic in self._callbacks:
                try:
                    # Run callback in asyncio context from paho-mqtt thread
                    asyncio.run_coroutine_threadsafe(self._callbacks[topic](topic, msg.payload), self._loop)
                except Exception as e:
                    logger.error(f"Error in message callback: {e}")

        try:
            self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, self.client_id)
            self._client.on_connect = on_connect
            self._client.on_disconnect = on_disconnect
            self._client.on_message = on_message

            # No credentials for local ESP32 broker (typically)
            self._client.connect(self.broker_host, self.broker_port, keepalive=30)
            self._client.loop_start()

            # Wait for connection with shorter timeout for local network
            await asyncio.wait_for(self._connect_event.wait(), timeout=5.0)

        except asyncio.TimeoutError:
            logger.error("Connection timeout to ESP32 local broker")
            self._connected = False
            if self._client:
                self._client.loop_stop()
            if self.ble_fallback_enabled:
                logger.info("BLE fallback enabled, entering fallback mode")
                self._ble_fallback_active = True
            else:
                raise
        except Exception as e:
            logger.error(f"Failed to connect to ESP32: {e}")
            self._connected = False
            if self._client:
                self._client.loop_stop()
            if self.ble_fallback_enabled:
                logger.info("BLE fallback enabled, entering fallback mode")
                self._ble_fallback_active = True
            else:
                raise

    async def disconnect(self) -> None:
        """Disconnect from ESP32 broker."""
        try:
            if self._client:
                self._client.disconnect()
                self._client.loop_stop()
            self._connected = False
            self._ble_fallback_active = False
            logger.info("ESP32AdapterAsync disconnected")
        except Exception as e:
            logger.error(f"Disconnect error: {e}")

    async def is_connected(self) -> bool:
        """Check connection status."""
        return (
            (self._connected and self._client is not None and self._client.is_connected())
            or self._ble_fallback_active
        )

    async def publish(self, topic: str, payload: bytes, qos: int = 1) -> None:
        """Publish message to topic (or local cache if offline)."""
        if self._connected and self._client:
            try:
                info = self._client.publish(topic, payload, qos=qos)
                if info.rc != 0:
                    logger.warning(f"Publish returned code {info.rc}, caching")
                    await self._cache_message(topic, payload)
                else:
                    logger.debug(f"Publishing to {topic}: {len(payload)} bytes")
            except Exception as e:
                logger.error(f"Publish error: {e}")
                await self._cache_message(topic, payload)
        else:
            logger.warning(f"Not connected, caching to {self.local_cache_path}: {topic}")
            await self._cache_message(topic, payload)

    async def subscribe(self, topic: str, callback: MessageCallback) -> None:
        """Subscribe to topic."""
        self._callbacks[topic] = callback

        if self._connected and self._client:
            try:
                self._client.subscribe(topic, qos=1)
            except Exception as e:
                logger.error(f"Subscribe error: {e}")

        logger.info(f"Subscribed to {topic}")

    async def _cache_message(self, topic: str, payload: bytes) -> None:
        """Cache message to local SQLite database."""
        try:
            conn = sqlite3.connect(self.local_cache_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS cached_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    payload BLOB NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    retry_count INTEGER DEFAULT 0
                )
                """
            )
            cursor.execute(
                "INSERT INTO cached_messages (topic, payload) VALUES (?, ?)",
                (topic, payload),
            )
            conn.commit()
            conn.close()
            logger.debug(f"Cached message to {topic}")
        except Exception as e:
            logger.error(f"Error caching message: {e}")

    async def _flush_cache(self) -> None:
        """Flush cached messages from SQLite after reconnection."""
        try:
            if not self._connected or not self._client:
                return
            conn = sqlite3.connect(self.local_cache_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id, topic, payload FROM cached_messages ORDER BY timestamp ASC LIMIT 100")
            rows = cursor.fetchall()
            for msg_id, topic, payload in rows:
                try:
                    info = self._client.publish(topic, payload, qos=1)
                    if info.rc == 0:
                        cursor.execute("DELETE FROM cached_messages WHERE id = ?", (msg_id,))
                        logger.debug(f"Flushed cached message {msg_id} to {topic}")
                    else:
                        logger.warning(f"Failed to flush message {msg_id}, retrying later")
                except Exception as e:
                    logger.error(f"Error flushing message {msg_id}: {e}")
                    break
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error flushing cache: {e}")

    async def get_status(self) -> Dict[str, Any]:
        """Get adapter status."""
        return {
            "is_connected": self._connected,
            "ble_fallback_active": self._ble_fallback_active,
            "broker_url": self.broker_url,
            "client_id": self.client_id,
            "ble_fallback_enabled": self.ble_fallback_enabled,
            "buffered_messages": self._get_cached_message_count(),
        }

    def _get_cached_message_count(self) -> int:
        """Get count of cached messages."""
        try:
            conn = sqlite3.connect(self.local_cache_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM cached_messages")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception:
            return 0


class MQTTService:
    """MQTT service for FastAPI integration — handles events and storage."""

    def __init__(self, adapter: IMQTTAdapter, session_factory: type = SessionLocal):
        self.adapter = adapter
        self._running = False
        self.session_factory = session_factory
        logger.info("MQTTService initialized")

    async def startup(self) -> None:
        """Initialize MQTT connection and subscriptions (dual-mode: legacy + T3)."""
        try:
            await self.adapter.connect()

            # Subscribe to legacy topics (Year 1 firmware, pre-Phase 7)
            await self.adapter.subscribe("jfa/device/+/event/pin", self.on_pin_event)
            await self.adapter.subscribe("jfa/device/+/event/card", self.on_card_event)
            await self.adapter.subscribe("jfa/device/+/event/state", self.on_device_state)
            await self.adapter.subscribe("jfa/device/+/event/ota", self.on_ota_event)

            # Subscribe to T3 schema topics (Phase 7+, new firmware)
            await self.adapter.subscribe("jfa/unify/+/device/+/access/request", self.on_access_request)
            await self.adapter.subscribe("jfa/unify/+/device/+/heartbeat", self.on_heartbeat)
            await self.adapter.subscribe("jfa/unify/+/device/+/status", self.on_device_status)
            await self.adapter.subscribe("jfa/unify/admin/audit/access_log", self.on_audit_log)

            self._running = True
            logger.info("MQTTService started successfully (dual-mode: legacy + T3)")
        except Exception as e:
            logger.error(f"MQTTService startup failed: {e}")
            raise

    async def shutdown(self) -> None:
        """Gracefully shutdown MQTT service."""
        try:
            self._running = False
            await self.adapter.disconnect()
            logger.info("MQTTService shutdown complete")
        except Exception as e:
            logger.error(f"MQTTService shutdown error: {e}")

    async def on_pin_event(self, topic: str, payload: bytes) -> None:
        """Handle PIN authentication event."""
        try:
            event = json.loads(payload)
            logger.debug(f"PIN event: {event.get('event_id')}")
            await self.store_event(event)
        except Exception as e:
            logger.error(f"Error processing PIN event: {e}")

    async def on_card_event(self, topic: str, payload: bytes) -> None:
        """Handle card/NFC RFID event."""
        try:
            event = json.loads(payload)
            logger.debug(f"Card event: {event.get('event_id')}")
            await self.store_event(event)
        except Exception as e:
            logger.error(f"Error processing card event: {e}")

    async def on_device_state(self, topic: str, payload: bytes) -> None:
        """Handle device state/heartbeat event."""
        try:
            event = json.loads(payload)
            logger.debug(f"Device state: {event.get('device_id')}")
            await self.store_event(event)
        except Exception as e:
            logger.error(f"Error processing device state: {e}")

    async def on_ota_event(self, topic: str, payload: bytes) -> None:
        """Handle OTA firmware notification event (legacy)."""
        try:
            event = json.loads(payload)
            logger.debug(f"OTA notification: {event.get('event_id')}")
            await self.store_event(event)
        except Exception as e:
            logger.error(f"Error processing OTA event: {e}")

    async def on_access_request(self, topic: str, payload: bytes) -> None:
        """Handle T3 access request event (PIN/card from device)."""
        try:
            # Parse topic: jfa/unify/{tenant_id}/device/{device_id}/access/request
            parts = topic.split("/")
            if len(parts) != 7:
                logger.warning(f"Invalid T3 access request topic structure: {topic}")
                return

            tenant_id_str = parts[2]
            device_id_str = parts[4]

            event = json.loads(payload)
            event["tenant_id"] = tenant_id_str
            event["device_id"] = device_id_str
            # Extract access_result from payload and use it as event_type
            access_result = event.get("access_result", "access_request")
            event["event_type"] = access_result
            event["source"] = "t3"  # Mark as T3 schema

            logger.debug(f"T3 Access request: tenant={tenant_id_str}, device={device_id_str}, result={access_result}")
            await self.store_event(event)
        except Exception as e:
            logger.error(f"Error processing T3 access request: {e}")

    async def on_heartbeat(self, topic: str, payload: bytes) -> None:
        """Handle T3 device heartbeat event."""
        try:
            # Parse topic: jfa/unify/{tenant_id}/device/{device_id}/heartbeat
            parts = topic.split("/")
            if len(parts) != 6:
                logger.warning(f"Invalid T3 heartbeat topic structure: {topic}")
                return

            tenant_id_str = parts[2]
            device_id_str = parts[4]

            event = json.loads(payload)
            event["tenant_id"] = tenant_id_str
            event["device_id"] = device_id_str
            event["event_type"] = "heartbeat"
            event["source"] = "t3"

            logger.debug(f"T3 Heartbeat: tenant={tenant_id_str}, device={device_id_str}")
            await self.store_event(event)
        except Exception as e:
            logger.error(f"Error processing T3 heartbeat: {e}")

    async def on_device_status(self, topic: str, payload: bytes) -> None:
        """Handle T3 device status event (battery, signal, etc)."""
        try:
            # Parse topic: jfa/unify/{tenant_id}/device/{device_id}/status
            parts = topic.split("/")
            if len(parts) != 6:
                logger.warning(f"Invalid T3 status topic structure: {topic}")
                return

            tenant_id_str = parts[2]
            device_id_str = parts[4]

            event = json.loads(payload)
            event["tenant_id"] = tenant_id_str
            event["device_id"] = device_id_str
            event["event_type"] = "device_status"
            event["source"] = "t3"

            logger.debug(f"T3 Device status: tenant={tenant_id_str}, device={device_id_str}")
            await self.store_event(event)
        except Exception as e:
            logger.error(f"Error processing T3 device status: {e}")

    async def on_audit_log(self, topic: str, payload: bytes) -> None:
        """Handle T3 audit log event (admin-only)."""
        try:
            event = json.loads(payload)
            event["event_type"] = "audit_log"
            event["source"] = "t3"

            logger.debug("T3 Audit log received")
            await self.store_event(event)
        except Exception as e:
            logger.error(f"Error processing T3 audit log: {e}")

    async def store_event(self, event: Dict[str, Any]) -> None:
        """Store event in PostgreSQL with tenant isolation (RLS)."""
        db = None
        try:
            device_id_str = event.get("device_id", "")
            event_type = event.get("event_type", "unknown")
            event_id = event.get("event_id", "unknown")

            if not device_id_str:
                logger.warning("Event missing device_id, skipping storage")
                return

            db = self.session_factory()

            # Look up device to get tenant_id
            try:
                device_uuid = uuid.UUID(device_id_str)
            except (ValueError, TypeError):
                logger.warning(f"Invalid device_id format: {device_id_str}")
                return

            device = db.query(InputDevice).filter(InputDevice.id == device_uuid).first()
            if not device:
                logger.warning(f"Device not found: {device_id_str}")
                return

            # Map event_type to access_type and extract PIN/card data
            source = event.get("source", "legacy")
            access_type = self._map_event_type(event_type, source)
            pin_hash = event.get("pin_hash")
            card_uid = event.get("card_uid")
            success = event.get("success", False)

            # Create and store AccessLog entry
            access_log = AccessLog(
                tenant_id=device.tenant_id,
                device_id=device.id,
                access_type=access_type,
                pin_hash=pin_hash,
                card_uid=card_uid,
                success=success,
                ip_address=None,  # TODO: Extract from MQTT topic or event metadata
            )

            db.add(access_log)
            db.commit()

            logger.info(
                f"Event stored: device={device_id_str}, type={event_type}, "
                f"access_type={access_type}, id={event_id}"
            )

        except Exception as e:
            if db:
                db.rollback()
            logger.error(f"Failed to store event: {e}")
        finally:
            if db:
                db.close()

    def _map_event_type(self, event_type: str, source: str = "legacy") -> str:
        """Map MQTT event type to AccessLog access_type (legacy + T3)."""
        if source == "t3":
            mapping = {
                "pin_valid": "pin_valid",
                "pin_invalid": "pin_invalid",
                "card_valid": "card_read",
                "card_invalid": "card_read",
                "heartbeat": "device_heartbeat",
                "device_status": "device_status",
                "audit_log": "audit_log",
            }
        else:
            mapping = {
                "pin": "pin_valid",
                "pin_invalid": "pin_invalid",
                "card": "card_read",
                "card_invalid": "card_read",
                "state": "device_state",
                "ota": "firmware_update",
            }
        return mapping.get(event_type, "unknown")

    async def get_status(self) -> Dict[str, Any]:
        """Get MQTT service status."""
        return {
            "service_running": self._running,
            "adapter_status": await self.adapter.get_status(),
        }
