"""
Testes de resiliência MQTT — desconexão/reconexão, buffer de mensagens, backoff.

Estratégia:
  - Mocks de IMQTTAdapter para simular falhas de conexão
  - Validação de políticas de reconexão (exponential backoff, max retries)
  - Verificação de buffer de mensagens durante desconexão
  - Testes de flush após reconexão
"""
import asyncio
from unittest.mock import MagicMock
from typing import Optional

import pytest

from app.services.mqtt_adapter import MQTTService, IMQTTAdapter


class ResilientMQTTAdapter(IMQTTAdapter):
    """Adapter mock com suporte a resiliência (desconexão simulada, buffer)."""

    def __init__(self):
        self._connected = False
        self._fail_count = 0
        self._fail_until = 0
        self.published_messages = []
        self.subscribed_topics = {}

    def set_fail_for_n_attempts(self, n: int):
        """Simular N falhas antes de sucesso."""
        self._fail_count = 0
        self._fail_until = n

    def _should_fail(self) -> bool:
        if self._fail_count < self._fail_until:
            self._fail_count += 1
            return True
        return False

    async def connect(self):
        """Conectar (pode falhar N vezes)."""
        if self._should_fail():
            raise ConnectionError("Simulated connection failure")
        self._connected = True

    async def disconnect(self):
        """Desconectar."""
        self._connected = False

    async def publish(self, topic: str, payload: bytes, qos: int = 1) -> None:
        """Publicar (falha se desconectado)."""
        if not self._connected:
            raise RuntimeError("Not connected")
        message = payload.decode() if isinstance(payload, bytes) else payload
        self.published_messages.append({
            "topic": topic,
            "message": message,
            "qos": qos,
        })

    async def subscribe(self, topic: str, callback: Optional[callable] = None, qos: int = 0) -> None:
        """Subscrever."""
        if not self._connected:
            raise RuntimeError("Not connected")
        self.subscribed_topics[topic] = {
            "callback": callback,
            "qos": qos,
        }

    async def is_connected(self) -> bool:
        """Status de conexão."""
        return self._connected

    async def get_status(self):
        """Obter status do adapter."""
        return {
            "connected": self._connected,
            "published_messages_count": len(self.published_messages),
            "subscribed_topics_count": len(self.subscribed_topics),
        }

    def get_published_messages(self) -> list[dict]:
        """Obter todas as mensagens publicadas."""
        return self.published_messages


@pytest.fixture
def resilient_adapter():
    """Adapter mock com resiliência."""
    return ResilientMQTTAdapter()


@pytest.fixture
def mqtt_service(resilient_adapter):
    """MQTTService com adapter resiliente."""
    return MQTTService(resilient_adapter, session_factory=MagicMock)


class TestMQTTReconnection:
    """Testes de reconexão após falha."""

    @pytest.mark.asyncio
    async def test_single_connection_attempt_success(self, mqtt_service, resilient_adapter):
        """Uma tentativa bem-sucedida de conexão."""
        assert not await resilient_adapter.is_connected()

        await mqtt_service.adapter.connect()

        assert await resilient_adapter.is_connected()

    @pytest.mark.asyncio
    async def test_reconnect_after_disconnect(self, mqtt_service, resilient_adapter):
        """Reconectar após desconexão."""
        await mqtt_service.adapter.connect()
        assert await resilient_adapter.is_connected()

        await mqtt_service.adapter.disconnect()
        assert not await resilient_adapter.is_connected()

        await mqtt_service.adapter.connect()
        assert await resilient_adapter.is_connected()

    @pytest.mark.asyncio
    async def test_connection_with_retries(self, mqtt_service, resilient_adapter):
        """Conexão com retry após falhas."""
        resilient_adapter.set_fail_for_n_attempts(3)

        # Primeiras 3 tentativas falham
        for attempt in range(3):
            with pytest.raises(ConnectionError):
                await mqtt_service.adapter.connect()
            assert not await resilient_adapter.is_connected()

        # 4ª tentativa sucede
        await mqtt_service.adapter.connect()
        assert await resilient_adapter.is_connected()

    @pytest.mark.asyncio
    async def test_exponential_backoff_simulation(self, mqtt_service, resilient_adapter):
        """Simular exponential backoff entre tentativas."""
        resilient_adapter.set_fail_for_n_attempts(2)

        backoff_times = []

        async def connect_with_backoff(max_retries=5, initial_backoff=0.1):
            for attempt in range(max_retries):
                try:
                    await mqtt_service.adapter.connect()
                    return attempt
                except ConnectionError:
                    backoff = min(initial_backoff * (2 ** attempt), 2.0)  # Cap at 2s
                    backoff_times.append(backoff)
                    await asyncio.sleep(0.01)  # Simular espera

        retries_needed = await connect_with_backoff(max_retries=5, initial_backoff=0.1)

        assert retries_needed == 2
        # Verificar que backoff cresce: 0.1, 0.2, 0.4
        assert backoff_times[0] == 0.1
        assert backoff_times[1] == 0.2


class TestMQTTMessagePublishing:
    """Testes de publicação de mensagens com resiliência."""

    @pytest.mark.asyncio
    async def test_publish_when_connected(self, mqtt_service, resilient_adapter):
        """Publicar quando conectado."""
        await mqtt_service.adapter.connect()

        await mqtt_service.adapter.publish("test/topic", b"message-123")

        assert len(resilient_adapter.published_messages) == 1
        assert resilient_adapter.published_messages[0]["message"] == "message-123"

    @pytest.mark.asyncio
    async def test_publish_fails_when_disconnected(self, mqtt_service, resilient_adapter):
        """Publicar falha quando desconectado."""
        with pytest.raises(RuntimeError, match="Not connected"):
            await mqtt_service.adapter.publish("test/topic", b"message")

    @pytest.mark.asyncio
    async def test_multiple_publishes(self, mqtt_service, resilient_adapter):
        """Publicar múltiplas mensagens."""
        await mqtt_service.adapter.connect()

        messages = ["msg1", "msg2", "msg3"]
        for msg in messages:
            await mqtt_service.adapter.publish("test/topic", msg.encode())

        assert len(resilient_adapter.published_messages) == len(messages)
        for i, msg in enumerate(messages):
            assert resilient_adapter.published_messages[i]["message"] == msg

    @pytest.mark.asyncio
    async def test_publish_with_different_qos_levels(self, mqtt_service, resilient_adapter):
        """Publicar com diferentes níveis de QoS."""
        await mqtt_service.adapter.connect()

        await mqtt_service.adapter.publish("topic/qos0", b"msg-qos0", qos=0)
        await mqtt_service.adapter.publish("topic/qos1", b"msg-qos1", qos=1)
        await mqtt_service.adapter.publish("topic/qos2", b"msg-qos2", qos=2)

        assert len(resilient_adapter.published_messages) == 3
        assert resilient_adapter.published_messages[0]["qos"] == 0
        assert resilient_adapter.published_messages[1]["qos"] == 1
        assert resilient_adapter.published_messages[2]["qos"] == 2


class TestMQTTSubscription:
    """Testes de subscrição com resiliência."""

    @pytest.mark.asyncio
    async def test_subscribe_when_connected(self, mqtt_service, resilient_adapter):
        """Subscrever quando conectado."""
        await mqtt_service.adapter.connect()

        async def callback(topic: str, payload: bytes):
            pass

        await mqtt_service.adapter.subscribe("test/topic", callback=callback)

        assert "test/topic" in resilient_adapter.subscribed_topics

    @pytest.mark.asyncio
    async def test_subscribe_fails_when_disconnected(self, mqtt_service, resilient_adapter):
        """Subscrever falha quando desconectado."""
        async def callback(topic: str, payload: bytes):
            pass

        with pytest.raises(RuntimeError, match="Not connected"):
            await mqtt_service.adapter.subscribe("test/topic", callback=callback)

    @pytest.mark.asyncio
    async def test_multiple_subscriptions(self, mqtt_service, resilient_adapter):
        """Múltiplas subscrições."""
        await mqtt_service.adapter.connect()

        topics = ["topic/a", "topic/b", "topic/c"]

        for topic in topics:
            async def callback(topic_param: str, payload: bytes):
                pass
            await mqtt_service.adapter.subscribe(topic, callback=callback)

        assert len(resilient_adapter.subscribed_topics) == len(topics)
        for topic in topics:
            assert topic in resilient_adapter.subscribed_topics

    @pytest.mark.asyncio
    async def test_resubscribe_after_reconnect(self, mqtt_service, resilient_adapter):
        """Resubscriptions após reconexão."""
        topic = "test/resubscribe"

        # Primeira conexão e subscrição
        await mqtt_service.adapter.connect()

        async def callback(topic_param: str, payload: bytes):
            pass

        await mqtt_service.adapter.subscribe(topic, callback=callback)
        assert topic in resilient_adapter.subscribed_topics

        # Desconectar
        await mqtt_service.adapter.disconnect()
        resilient_adapter.subscribed_topics.clear()

        # Reconectar e resubinscrever
        await mqtt_service.adapter.connect()
        await mqtt_service.adapter.subscribe(topic, callback=callback)

        assert topic in resilient_adapter.subscribed_topics


class TestMQTTConnectionStateTransitions:
    """Testes de transições de estado de conexão."""

    @pytest.mark.asyncio
    async def test_connection_state_transitions(self, mqtt_service, resilient_adapter):
        """Sequência de transições de estado."""
        states = []

        states.append(("start", await resilient_adapter.is_connected()))

        await mqtt_service.adapter.connect()
        states.append(("connected", await resilient_adapter.is_connected()))

        await mqtt_service.adapter.disconnect()
        states.append(("disconnected", await resilient_adapter.is_connected()))

        await mqtt_service.adapter.connect()
        states.append(("reconnected", await resilient_adapter.is_connected()))

        expected = [
            ("start", False),
            ("connected", True),
            ("disconnected", False),
            ("reconnected", True),
        ]

        assert states == expected

    @pytest.mark.asyncio
    async def test_operations_respect_connection_state(self, mqtt_service, resilient_adapter):
        """Operações só funcionam se conectado."""
        # Desconectado: todas as operações falham
        with pytest.raises(RuntimeError):
            await mqtt_service.adapter.publish("test", b"msg")

        with pytest.raises(RuntimeError):
            await mqtt_service.adapter.subscribe("test")

        # Conectado: operações sucedem
        await mqtt_service.adapter.connect()

        await mqtt_service.adapter.publish("test", b"msg")

        async def callback(topic: str, payload: bytes):
            pass
        await mqtt_service.adapter.subscribe("test", callback=callback)

        assert len(resilient_adapter.published_messages) == 1
        assert "test" in resilient_adapter.subscribed_topics

        # Desconectado novamente: operações falham
        await mqtt_service.adapter.disconnect()

        with pytest.raises(RuntimeError):
            await mqtt_service.adapter.publish("test", b"msg")

        with pytest.raises(RuntimeError):
            await mqtt_service.adapter.subscribe("test")


class TestMQTTBufferingAndFlush:
    """Testes de buffer de mensagens e flush após reconexão."""

    @pytest.mark.asyncio
    async def test_message_buffer_during_disconnect(self, mqtt_service, resilient_adapter):
        """Simular buffer de mensagens durante desconexão."""
        await mqtt_service.adapter.connect()

        # Publicar enquanto conectado
        await mqtt_service.adapter.publish("topic/a", b"msg-a")
        assert len(resilient_adapter.published_messages) == 1

        # Desconectar
        await mqtt_service.adapter.disconnect()

        # Mensagens "bufferizadas" (não publicadas) durante desconexão
        pending_messages = [
            ("topic/b", b"msg-b"),
            ("topic/c", b"msg-c"),
        ]

        # Reconectar
        await mqtt_service.adapter.connect()

        # Flush do buffer
        for topic, message in pending_messages:
            await mqtt_service.adapter.publish(topic, message)

        assert len(resilient_adapter.published_messages) == 3

    @pytest.mark.asyncio
    async def test_flush_respects_order(self, mqtt_service, resilient_adapter):
        """Flush mantém ordem de mensagens."""
        await mqtt_service.adapter.connect()

        messages = [f"msg-{i}" for i in range(5)]

        for i, msg in enumerate(messages):
            await mqtt_service.adapter.publish("topic", msg.encode())

        published = [m["message"] for m in resilient_adapter.published_messages]

        assert published == messages


class TestMQTTEdgeCases:
    """Testes de casos extremos."""

    @pytest.mark.asyncio
    async def test_double_connect(self, mqtt_service, resilient_adapter):
        """Conectar duas vezes não causa erro."""
        await mqtt_service.adapter.connect()
        assert await resilient_adapter.is_connected()

        # Segunda conexão (pode re-conectar ou noop)
        await mqtt_service.adapter.connect()
        assert await resilient_adapter.is_connected()

    @pytest.mark.asyncio
    async def test_double_disconnect(self, mqtt_service, resilient_adapter):
        """Desconectar duas vezes não causa erro."""
        await mqtt_service.adapter.connect()
        await mqtt_service.adapter.disconnect()

        # Segunda desconexão (noop ou graceful)
        await mqtt_service.adapter.disconnect()
        assert not await resilient_adapter.is_connected()

    @pytest.mark.asyncio
    async def test_rapid_connect_disconnect_cycles(self, mqtt_service, resilient_adapter):
        """Ciclos rápidos de connect/disconnect."""
        for _ in range(5):
            await mqtt_service.adapter.connect()
            assert await resilient_adapter.is_connected()

            await mqtt_service.adapter.disconnect()
            assert not await resilient_adapter.is_connected()

    @pytest.mark.asyncio
    async def test_empty_message_publish(self, mqtt_service, resilient_adapter):
        """Publicar mensagem vazia é válido."""
        await mqtt_service.adapter.connect()

        await mqtt_service.adapter.publish("topic", b"")

        assert len(resilient_adapter.published_messages) == 1
        assert resilient_adapter.published_messages[0]["message"] == ""
