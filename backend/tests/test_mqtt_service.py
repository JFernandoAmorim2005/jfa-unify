"""
Testes unitários para TuyaMqttClient e interface MqttClient.
Usa mocks — sem broker MQTT real.
"""
from unittest.mock import MagicMock, patch, call
import pytest

from app.services.mqtt_service import MqttClient
from app.services.tuya_mqtt import TuyaMqttClient, TUYA_TOPIC_STATUS, TUYA_TOPIC_COMMAND


# --- Implementação mínima para testar a classe abstracta ---
class ConcreteMqttClient(MqttClient):
    """Implementação de teste da interface abstracta."""

    def connect(self, username="", password=""):
        self._connected = True

    def disconnect(self):
        self._connected = False

    def publish(self, topic, payload, qos=1):
        pass

    def subscribe(self, topic, callback, qos=1):
        pass


class TestMqttClientAbstract:
    """Testes da classe base MqttClient."""

    def test_is_connected_inicial_false(self):
        client = ConcreteMqttClient("localhost", 1883, "test-client")
        assert client.is_connected is False

    def test_on_connect_sucesso(self):
        client = ConcreteMqttClient("localhost", 1883, "test-client")
        client._on_connect(0)
        assert client.is_connected is True

    def test_on_connect_falha(self):
        client = ConcreteMqttClient("localhost", 1883, "test-client")
        client._on_connect(1)
        assert client.is_connected is False

    def test_on_disconnect(self):
        client = ConcreteMqttClient("localhost", 1883, "test-client")
        client._connected = True
        client._on_disconnect(0)
        assert client.is_connected is False


class TestTuyaMqttClient:
    """Testes do cliente MQTT Tuya."""

    @pytest.fixture
    def tuya_client(self):
        """Cria TuyaMqttClient com paho mockado."""
        with patch("app.services.tuya_mqtt.mqtt_paho.Client") as mock_paho_class:
            mock_paho = MagicMock()
            mock_paho_class.return_value = mock_paho
            client = TuyaMqttClient(
                broker="localhost",
                port=1883,
                client_id="test-tuya",
                topic_prefix="tuya/",
            )
            client._mock_paho = mock_paho
            yield client

    def test_topic_status_formato_correcto(self, tuya_client):
        topic = tuya_client.topic_status("device123")
        assert topic == "tuya/thing/device123/status"

    def test_topic_command_formato_correcto(self, tuya_client):
        topic = tuya_client.topic_command("device123")
        assert topic == "tuya/thing/device123/command"

    def test_connect_chama_paho_connect(self, tuya_client):
        tuya_client.connect()
        tuya_client._mock_paho.connect.assert_called_once_with(
            "localhost", 1883, keepalive=60
        )
        tuya_client._mock_paho.loop_start.assert_called_once()

    def test_connect_com_credenciais(self, tuya_client):
        tuya_client.connect(username="user", password="pass")
        tuya_client._mock_paho.username_pw_set.assert_called_once_with("user", "pass")

    def test_publish_encode_str(self, tuya_client):
        tuya_client._connected = True
        tuya_client._mock_paho.publish.return_value = MagicMock(
            rc=0  # MQTT_ERR_SUCCESS
        )
        tuya_client.publish("tuya/test", "mensagem")
        tuya_client._mock_paho.publish.assert_called_once()
        args = tuya_client._mock_paho.publish.call_args
        assert args[0][1] == b"mensagem"

    def test_subscribe_regista_callback(self, tuya_client):
        tuya_client._connected = True
        callback = MagicMock()
        tuya_client.subscribe("tuya/thing/+/status", callback)
        assert "tuya/thing/+/status" in tuya_client._subscriptions
        assert tuya_client._subscriptions["tuya/thing/+/status"] == callback

    def test_send_command_publica_json(self, tuya_client):
        tuya_client._connected = True
        tuya_client._mock_paho.publish.return_value = MagicMock(rc=0)
        tuya_client.send_command("device123", [{"code": "switch_1", "value": True}])
        tuya_client._mock_paho.publish.assert_called_once()
        topic_arg = tuya_client._mock_paho.publish.call_args[0][0]
        assert topic_arg == "tuya/thing/device123/command"

    def test_disconnect_para_loop(self, tuya_client):
        tuya_client.disconnect()
        tuya_client._mock_paho.loop_stop.assert_called_once()
        tuya_client._mock_paho.disconnect.assert_called_once()

    def test_handle_message_chama_callback(self, tuya_client):
        """Mensagem recebida deve invocar o callback registado."""
        received = []
        callback = lambda t, p: received.append((t, p))
        tuya_client._subscriptions["tuya/thing/dev1/status"] = callback

        msg = MagicMock()
        msg.topic = "tuya/thing/dev1/status"
        msg.payload = b'{"status": "online"}'
        tuya_client._handle_message(None, None, msg)

        assert len(received) == 1
        assert received[0] == ("tuya/thing/dev1/status", b'{"status": "online"}')
