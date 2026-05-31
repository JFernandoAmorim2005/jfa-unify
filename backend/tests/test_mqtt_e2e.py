"""
Testes end-to-end para MQTT — uso de broker Mosquitto real.

Requisitos:
  - Mosquitto rodando em localhost:1883 (via docker-compose up ou instalação local)
  - paho-mqtt instalado
  - Testes marcados com @pytest.mark.e2e (para executar separadamente)

Estratégia:
  - Conexão real ao broker MQTT
  - Testes de pub/sub, QoS, reconexão
  - Sem mocks — validação real de protocolo MQTT
"""
import asyncio
import time
import uuid
from typing import Optional

import pytest

try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None

from app.services.mqtt_adapter import IMQTTAdapter


MQTT_BROKER_HOST = "localhost"
MQTT_BROKER_PORT = 1883
MQTT_TIMEOUT = 5


pytestmark = pytest.mark.e2e  # Marca todos os testes como E2E


@pytest.fixture(scope="module")
def mqtt_broker_available():
    """Verifica se Mosquitto está disponível em localhost:1883."""
    if mqtt is None:
        pytest.skip("paho-mqtt não instalado")

    client = mqtt.Client()
    try:
        client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, keepalive=1)
        client.disconnect()
        return True
    except (ConnectionRefusedError, OSError):
        pytest.skip(f"Mosquitto não disponível em {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")


@pytest.fixture
def mqtt_client_direct():
    """Cliente MQTT direto (paho-mqtt) para testes E2E."""
    if mqtt is None:
        pytest.skip("paho-mqtt não instalado")

    client = mqtt.Client()
    yield client
    try:
        if client.is_connected():
            client.disconnect()
    except Exception:
        pass


class MockMQTTAdapter(IMQTTAdapter):
    """Adapter MQTT simples baseado em paho-mqtt para testes E2E."""

    def __init__(self, broker_host: str = MQTT_BROKER_HOST, broker_port: int = MQTT_BROKER_PORT):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client = mqtt.Client()
        self._connected = False
        self._subscriptions: dict[str, callable] = {}
        self._messages_received: list[dict] = []

        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._connected = True
        else:
            self._connected = False

    def _on_message(self, client, userdata, msg):
        payload = msg.payload.decode() if isinstance(msg.payload, bytes) else msg.payload
        self._messages_received.append({
            "topic": msg.topic,
            "payload": payload,
            "qos": msg.qos,
            "timestamp": time.time(),
        })

        # Chamar callback se registrado
        if msg.topic in self._subscriptions:
            self._subscriptions[msg.topic](payload)

    def _on_disconnect(self, client, userdata, rc):
        self._connected = False

    async def connect(self):
        """Conectar ao broker MQTT."""
        self.client.connect(self.broker_host, self.broker_port, keepalive=60)
        self.client.loop_start()
        # Aguardar conexão
        timeout = time.time() + MQTT_TIMEOUT
        while not self._connected and time.time() < timeout:
            await asyncio.sleep(0.1)
        if not self._connected:
            raise ConnectionError(f"Falha ao conectar em {self.broker_host}:{self.broker_port}")

    async def disconnect(self):
        """Desconectar do broker."""
        self.client.loop_stop()
        self.client.disconnect()
        self._connected = False

    async def publish(self, topic: str, message: str, qos: int = 0):
        """Publicar mensagem no topic."""
        if not self._connected:
            raise RuntimeError("MQTT não conectado")
        result = self.client.publish(topic, message, qos=qos)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(f"Erro ao publicar: {result.rc}")

    async def subscribe(self, topic: str, callback: Optional[callable] = None, qos: int = 0):
        """Subscrever a um topic."""
        if not self._connected:
            raise RuntimeError("MQTT não conectado")
        if callback:
            self._subscriptions[topic] = callback
        self.client.subscribe(topic, qos=qos)

    def is_connected(self) -> bool:
        """Retornar status de conexão."""
        return self._connected

    def get_messages(self, topic: str = None) -> list[dict]:
        """Obter mensagens recebidas (para testes)."""
        if topic is None:
            return self._messages_received
        return [m for m in self._messages_received if m["topic"] == topic]


@pytest.fixture
def mqtt_adapter_e2e(mqtt_broker_available):
    """Adapter MQTT para testes E2E com broker real."""
    adapter = MockMQTTAdapter()
    yield adapter


class TestMQTTBrokerConnectivity:
    """Testes de conectividade básica com broker Mosquitto."""

    @pytest.mark.asyncio
    async def test_connect_to_broker(self, mqtt_adapter_e2e):
        """Conectar ao broker Mosquitto."""
        await mqtt_adapter_e2e.connect()
        assert mqtt_adapter_e2e.is_connected()
        await mqtt_adapter_e2e.disconnect()

    @pytest.mark.asyncio
    async def test_connect_disconnect_cycle(self, mqtt_adapter_e2e):
        """Ciclo de conexão/desconexão."""
        assert not mqtt_adapter_e2e.is_connected()

        await mqtt_adapter_e2e.connect()
        assert mqtt_adapter_e2e.is_connected()

        await mqtt_adapter_e2e.disconnect()
        assert not mqtt_adapter_e2e.is_connected()

    @pytest.mark.asyncio
    async def test_multiple_connect_cycles(self, mqtt_adapter_e2e):
        """Múltiplos ciclos de conectar/desconectar."""
        for i in range(3):
            await mqtt_adapter_e2e.connect()
            assert mqtt_adapter_e2e.is_connected()

            await mqtt_adapter_e2e.disconnect()
            assert not mqtt_adapter_e2e.is_connected()


class TestMQTTPublishSubscribe:
    """Testes de pub/sub com broker real."""

    @pytest.mark.asyncio
    async def test_publish_message(self, mqtt_adapter_e2e):
        """Publicar mensagem em um topic."""
        await mqtt_adapter_e2e.connect()

        topic = f"test/publish/{uuid.uuid4()}"
        message = "test-payload-1234"

        await mqtt_adapter_e2e.publish(topic, message, qos=0)

        await mqtt_adapter_e2e.disconnect()

    @pytest.mark.asyncio
    async def test_subscribe_and_receive(self, mqtt_adapter_e2e):
        """Subscrever a um topic e receber mensagens."""
        await mqtt_adapter_e2e.connect()

        topic = f"test/pubsub/{uuid.uuid4()}"

        # Subscrever
        messages_received = []

        async def on_message(payload):
            messages_received.append(payload)

        await mqtt_adapter_e2e.subscribe(topic, callback=on_message)

        # Dar tempo para subscrição ser processada
        await asyncio.sleep(0.5)

        # Publicar
        test_message = "test-hello-world"
        await mqtt_adapter_e2e.publish(topic, test_message)

        # Aguardar recebimento
        timeout = time.time() + MQTT_TIMEOUT
        while not messages_received and time.time() < timeout:
            await asyncio.sleep(0.1)

        assert len(messages_received) >= 1
        assert test_message in messages_received

        await mqtt_adapter_e2e.disconnect()

    @pytest.mark.asyncio
    async def test_multiple_messages(self, mqtt_adapter_e2e):
        """Publicar e receber múltiplas mensagens."""
        await mqtt_adapter_e2e.connect()

        topic = f"test/multiple/{uuid.uuid4()}"
        test_messages = ["msg1", "msg2", "msg3"]

        received = []

        async def on_message(payload):
            received.append(payload)

        await mqtt_adapter_e2e.subscribe(topic, callback=on_message)
        await asyncio.sleep(0.5)

        # Publicar múltiplas
        for msg in test_messages:
            await mqtt_adapter_e2e.publish(topic, msg)
            await asyncio.sleep(0.1)

        # Aguardar todos os mensagens
        timeout = time.time() + MQTT_TIMEOUT
        while len(received) < len(test_messages) and time.time() < timeout:
            await asyncio.sleep(0.1)

        assert len(received) >= len(test_messages)
        for msg in test_messages:
            assert msg in received

        await mqtt_adapter_e2e.disconnect()

    @pytest.mark.asyncio
    async def test_wildcard_subscription(self, mqtt_adapter_e2e):
        """Subscrever com wildcard (#) e receber de múltiplos topics."""
        await mqtt_adapter_e2e.connect()

        base_topic = f"test/wildcard/{uuid.uuid4()}"
        wildcard_topic = f"{base_topic}/#"

        received = []

        async def on_message(payload):
            received.append(payload)

        await mqtt_adapter_e2e.subscribe(wildcard_topic, callback=on_message)
        await asyncio.sleep(0.5)

        # Publicar em múltiplos subtopics
        subtopics = [
            f"{base_topic}/device/001",
            f"{base_topic}/device/002",
            f"{base_topic}/status",
        ]

        for topic in subtopics:
            await mqtt_adapter_e2e.publish(topic, f"message-for-{topic.split('/')[-1]}")
            await asyncio.sleep(0.1)

        # Aguardar recebimento
        timeout = time.time() + MQTT_TIMEOUT
        while len(received) < len(subtopics) and time.time() < timeout:
            await asyncio.sleep(0.1)

        assert len(received) >= len(subtopics)

        await mqtt_adapter_e2e.disconnect()


class TestMQTTQoS:
    """Testes de QoS (Quality of Service)."""

    @pytest.mark.asyncio
    async def test_publish_qos0(self, mqtt_adapter_e2e):
        """Publicar com QoS 0 (at most once)."""
        await mqtt_adapter_e2e.connect()

        topic = f"test/qos0/{uuid.uuid4()}"
        await mqtt_adapter_e2e.publish(topic, "message-qos0", qos=0)

        await mqtt_adapter_e2e.disconnect()

    @pytest.mark.asyncio
    async def test_publish_qos1(self, mqtt_adapter_e2e):
        """Publicar com QoS 1 (at least once)."""
        await mqtt_adapter_e2e.connect()

        topic = f"test/qos1/{uuid.uuid4()}"
        await mqtt_adapter_e2e.publish(topic, "message-qos1", qos=1)

        await mqtt_adapter_e2e.disconnect()

    @pytest.mark.asyncio
    async def test_subscribe_qos0(self, mqtt_adapter_e2e):
        """Subscrever com QoS 0."""
        await mqtt_adapter_e2e.connect()

        topic = f"test/sub-qos0/{uuid.uuid4()}"
        received = []

        async def on_message(payload):
            received.append(payload)

        await mqtt_adapter_e2e.subscribe(topic, callback=on_message, qos=0)
        await asyncio.sleep(0.3)

        await mqtt_adapter_e2e.publish(topic, "test-qos0-message")

        timeout = time.time() + MQTT_TIMEOUT
        while not received and time.time() < timeout:
            await asyncio.sleep(0.1)

        assert len(received) >= 1

        await mqtt_adapter_e2e.disconnect()


class TestMQTTErrorHandling:
    """Testes de tratamento de erros."""

    @pytest.mark.asyncio
    async def test_publish_without_connect_raises_error(self, mqtt_adapter_e2e):
        """Publicar sem estar conectado levanta erro."""
        with pytest.raises(RuntimeError, match="não conectado"):
            await mqtt_adapter_e2e.publish("test/topic", "message")

    @pytest.mark.asyncio
    async def test_subscribe_without_connect_raises_error(self, mqtt_adapter_e2e):
        """Subscrever sem estar conectado levanta erro."""
        with pytest.raises(RuntimeError, match="não conectado"):
            await mqtt_adapter_e2e.subscribe("test/topic")

    @pytest.mark.asyncio
    async def test_disconnect_cleans_up(self, mqtt_adapter_e2e):
        """Desconectar limpa o estado interno."""
        await mqtt_adapter_e2e.connect()
        assert mqtt_adapter_e2e.is_connected()

        await mqtt_adapter_e2e.disconnect()
        assert not mqtt_adapter_e2e.is_connected()

        # Não deve ser possível publicar após desconectar
        with pytest.raises(RuntimeError):
            await mqtt_adapter_e2e.publish("test/topic", "message")
