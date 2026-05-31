"""
Implementação MQTT para Tuya Hub 6E — JFA Unify.
Segue o esquema de tópicos proprietário do hub Tuya.
"""
import json
import logging

import paho.mqtt.client as mqtt_paho

from app.services.mqtt_service import MqttClient, MessageCallback

logger = logging.getLogger(__name__)


# --- Esquema de tópicos Tuya Hub 6E ---
# Formato base: tuya/{access_id}/thing/{device_id}/{action}
TUYA_TOPIC_STATUS = "{prefix}thing/{device_id}/status"
TUYA_TOPIC_COMMAND = "{prefix}thing/{device_id}/command"
TUYA_TOPIC_HEARTBEAT = "{prefix}thing/{device_id}/heartbeat"
TUYA_TOPIC_WILDCARD_ALL = "{prefix}thing/+/status"


class TuyaMqttClient(MqttClient):
    """
    Cliente MQTT específico para o hub Tuya 6E.
    Encapsula o esquema de tópicos e o formato de mensagem Tuya.
    """

    def __init__(
        self,
        broker: str,
        port: int,
        client_id: str,
        topic_prefix: str,
        access_id: str = "",
        access_secret: str = "",
    ) -> None:
        super().__init__(broker, port, client_id)
        self.topic_prefix = topic_prefix
        self.access_id = access_id
        self.access_secret = access_secret
        self._subscriptions: dict[str, MessageCallback] = {}
        self._client = mqtt_paho.Client(client_id=client_id)
        self._setup_callbacks()

    # --- Configuração interna ---

    def _setup_callbacks(self) -> None:
        """Regista callbacks internos no cliente paho."""
        self._client.on_connect = self._handle_connect
        self._client.on_disconnect = self._handle_disconnect
        self._client.on_message = self._handle_message

    def _handle_connect(self, client, userdata, flags, rc) -> None:  # noqa: ANN001
        self._on_connect(rc)
        # Re-subscrever tópicos após reconexão
        for topic in self._subscriptions:
            self._client.subscribe(topic, qos=1)
            logger.debug("Re-subscrito: %s", topic)

    def _handle_disconnect(self, client, userdata, rc) -> None:  # noqa: ANN001
        self._on_disconnect(rc)

    def _handle_message(self, client, userdata, msg) -> None:  # noqa: ANN001
        """Encaminha mensagem recebida para o callback registado."""
        callback = self._subscriptions.get(msg.topic)
        if callback:
            callback(msg.topic, msg.payload)
        else:
            # Tentar correspondência por wildcard (prefixo)
            for pattern, cb in self._subscriptions.items():
                if pattern.endswith("#") and msg.topic.startswith(pattern[:-1]):
                    cb(msg.topic, msg.payload)
                    return

    # --- Interface MqttClient ---

    def connect(self, username: str = "", password: str = "") -> None:
        """Liga ao broker MQTT Tuya Hub."""
        if username:
            self._client.username_pw_set(username, password)
        try:
            self._client.connect(self.broker, self.port, keepalive=60)
            self._client.loop_start()
            logger.info("TuyaMqttClient a ligar: %s:%d", self.broker, self.port)
        except Exception as exc:
            logger.error("Erro ao ligar ao broker Tuya: %s", exc)
            raise

    def disconnect(self) -> None:
        """Termina a ligação ao broker Tuya."""
        self._client.loop_stop()
        self._client.disconnect()
        logger.info("TuyaMqttClient desligado.")

    def publish(self, topic: str, payload: str | bytes, qos: int = 1) -> None:
        """Publica mensagem num tópico Tuya."""
        if not self._connected:
            logger.warning("Tentativa de publicação sem ligação activa: %s", topic)
        if isinstance(payload, str):
            payload = payload.encode("utf-8")
        result = self._client.publish(topic, payload, qos=qos)
        if result.rc != mqtt_paho.MQTT_ERR_SUCCESS:
            logger.error("Falha ao publicar em %s: rc=%d", topic, result.rc)
        else:
            logger.debug("Publicado em %s (%d bytes)", topic, len(payload))

    def subscribe(self, topic: str, callback: MessageCallback, qos: int = 1) -> None:
        """Subscreve tópico Tuya e regista callback."""
        self._subscriptions[topic] = callback
        if self._connected:
            self._client.subscribe(topic, qos=qos)
        logger.debug("Subscrito: %s", topic)

    # --- Helpers Tuya específicos ---

    def topic_status(self, device_id: str) -> str:
        """Tópico de estado para um dispositivo Tuya."""
        return TUYA_TOPIC_STATUS.format(prefix=self.topic_prefix, device_id=device_id)

    def topic_command(self, device_id: str) -> str:
        """Tópico de comando para um dispositivo Tuya."""
        return TUYA_TOPIC_COMMAND.format(prefix=self.topic_prefix, device_id=device_id)

    def send_command(self, device_id: str, commands: list[dict]) -> None:
        """
        Envia comandos para um dispositivo Tuya.

        Args:
            device_id: ID do dispositivo no hub Tuya.
            commands:  Lista de dicts com {code, value}, ex: [{"code": "switch_1", "value": True}]
        """
        topic = self.topic_command(device_id)
        payload = json.dumps({"commands": commands})
        self.publish(topic, payload)
