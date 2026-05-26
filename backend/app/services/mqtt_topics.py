"""
MQTT Topic Naming Invariantes — JFA Unify Phase 7.

Schema:
  jfa/unify/{tenant_id}/device/{device_id}/access/request
  jfa/unify/{tenant_id}/device/{device_id}/access/response
  jfa/unify/{tenant_id}/device/{device_id}/heartbeat
  jfa/unify/{tenant_id}/device/{device_id}/status
  jfa/unify/admin/audit/access_log

Invariantes:
  - {tenant_id} = UUID v4 (RLS boundary)
  - {device_id} = UUID v4 (device ID)
  - topic depth max = 7 levels (MQTT broker limit)
  - payload max = 4KB (hardware memory constraint)

Usage:
  from app.services.mqtt_topics import TopicBuilder
  builder = TopicBuilder(tenant_id, device_id)
  topic = builder.access_request()  # -> jfa/unify/{tenant_id}/device/{device_id}/access/request
"""
import uuid
from typing import Optional


class TopicBuilder:
    """Construir tópicos MQTT com invariantes JFA Unify."""

    def __init__(self, tenant_id: uuid.UUID, device_id: Optional[uuid.UUID] = None):
        self.tenant_id = str(tenant_id)
        self.device_id = str(device_id) if device_id else None

    def access_request(self) -> str:
        """PIN/card access request inbound."""
        return f"jfa/unify/{self.tenant_id}/device/{self.device_id}/access/request"

    def access_response(self) -> str:
        """PIN/card access decision outbound."""
        return f"jfa/unify/{self.tenant_id}/device/{self.device_id}/access/response"

    def heartbeat(self) -> str:
        """Device keepalive / health status."""
        return f"jfa/unify/{self.tenant_id}/device/{self.device_id}/heartbeat"

    def status(self) -> str:
        """Device operational status (online/offline, battery, etc)."""
        return f"jfa/unify/{self.tenant_id}/device/{self.device_id}/status"

    @staticmethod
    def audit_log() -> str:
        """Audit log topic (admin-only) — no tenant/device scoping."""
        return "jfa/unify/admin/audit/access_log"

    def subscribe_device_pattern(self) -> str:
        """Subscribe pattern para todos os eventos deste device."""
        return f"jfa/unify/{self.tenant_id}/device/{self.device_id}/#"

    def subscribe_tenant_pattern(self) -> str:
        """Subscribe pattern para todos os eventos deste tenant."""
        return f"jfa/unify/{self.tenant_id}/#"


# Legacy topic support (Year 1-2 compatibility, pre-T3)
class LegacyTopicBuilder:
    """Support for legacy MQTT schema (before Phase 7 unification)."""

    @staticmethod
    def pin_event(device_id: str) -> str:
        """Legacy: jfa/device/{device_id}/event/pin"""
        return f"jfa/device/{device_id}/event/pin"

    @staticmethod
    def card_event(device_id: str) -> str:
        """Legacy: jfa/device/{device_id}/event/card"""
        return f"jfa/device/{device_id}/event/card"

    @staticmethod
    def device_state(device_id: str) -> str:
        """Legacy: jfa/device/{device_id}/event/state"""
        return f"jfa/device/{device_id}/event/state"

    @staticmethod
    def ota_event(device_id: str) -> str:
        """Legacy: jfa/device/{device_id}/event/ota"""
        return f"jfa/device/{device_id}/event/ota"
