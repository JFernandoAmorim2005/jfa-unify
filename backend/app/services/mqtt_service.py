"""
Interface abstracta para cliente MQTT — JFA Unify.
Implementações concretas (Tuya, genérico) herdam desta classe base.
"""
import logging
from abc import ABC, abstractmethod
from typing import Callable

logger = logging.getLogger(__name__)

# Tipo de callback para mensagens recebidas: (tópico, payload)
MessageCallback = Callable[[str, bytes], None]


class MqttClient(ABC):
    """
    Interface genérica para cliente MQTT.
    Separa o contrato da implementação para permitir diferentes brokers.
    """

    def __init__(self, broker: str, port: int, client_id: str) -> None:
        self.broker = broker
        self.port = port
        self.client_id = client_id
        self._connected = False

    @abstractmethod
    def connect(self, username: str = "", password: str = "") -> None:
        """Estabelece ligação ao broker MQTT."""
        ...

    @abstractmethod
    def disconnect(self) -> None:
        """Termina a ligação ao broker."""
        ...

    @abstractmethod
    def publish(self, topic: str, payload: str | bytes, qos: int = 1) -> None:
        """
        Publica uma mensagem num tópico.

        Args:
            topic:   Tópico MQTT de destino.
            payload: Mensagem a publicar (str ou bytes).
            qos:     Quality of Service (0, 1 ou 2).
        """
        ...

    @abstractmethod
    def subscribe(self, topic: str, callback: MessageCallback, qos: int = 1) -> None:
        """
        Subscreve um tópico e regista o callback para mensagens recebidas.

        Args:
            topic:    Tópico MQTT (suporta wildcards + e #).
            callback: Função chamada com (tópico, payload) a cada mensagem.
            qos:      Quality of Service (0, 1 ou 2).
        """
        ...

    @property
    def is_connected(self) -> bool:
        """Indica se a ligação ao broker está activa."""
        return self._connected

    def _on_connect(self, result_code: int) -> None:
        """Callback interno de conexão — actualiza estado."""
        if result_code == 0:
            self._connected = True
            logger.info(
                "MQTT ligado: broker=%s port=%d client_id=%s",
                self.broker, self.port, self.client_id,
            )
        else:
            self._connected = False
            logger.error(
                "MQTT falhou a ligar: broker=%s código=%d",
                self.broker, result_code,
            )

    def _on_disconnect(self, result_code: int) -> None:
        """Callback interno de desconexão."""
        self._connected = False
        logger.warning(
            "MQTT desligado: broker=%s código=%d",
            self.broker, result_code,
        )
