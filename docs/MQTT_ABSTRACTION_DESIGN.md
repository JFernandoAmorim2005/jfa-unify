# MQTT Abstraction Design — JFA Unify Phase 7

**Author:** CTO + Product Lead  
**Date:** 2026-05-27  
**Status:** Approved (Phase 7, Day 2-3)  
**Target Merge:** 2026-06-02 (Day 7)

---

## Executive Summary

This document codifies the MQTT abstraction pattern for JFA Unify, enabling Year 1-2 deployment on Tuya Cloud + local hub MQTT, with clear upgrade path to Year 3+ ESP32-S3 custom hardware without application changes.

**Key Achievement:** Backend MQTT logic is now decoupled from broker implementation via `IMQTTAdapter` interface.

---

## Architecture Overview

### Abstract Interface (Python ABC)

```python
# app/services/mqtt_adapter.py
class IMQTTAdapter(ABC):
    """Async MQTT adapter interface for FastAPI integration."""
    
    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to MQTT broker."""
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Gracefully close MQTT connection."""
    
    @abstractmethod
    async def is_connected(self) -> bool:
        """Check if adapter is connected."""
    
    @abstractmethod
    async def publish(self, topic: str, payload: bytes, qos: int = 1) -> None:
        """Publish message to topic."""
    
    @abstractmethod
    async def subscribe(self, topic: str, callback: MessageCallback) -> None:
        """Subscribe to topic with callback."""
    
    @abstractmethod
    async def get_status(self) -> Dict[str, Any]:
        """Get adapter connection status."""
```

### Implementations

#### Year 1-2: Tuya Cloud MQTT (Primary)

```python
class TuyaAdapterAsync(IMQTTAdapter):
    """
    Async wrapper for Tuya MQTT adapter.
    - Broker: Tuya IoT Hub (cloud)
    - Authentication: Username + Password (Tuya API credentials)
    - Failover: Local hub fallback (if available)
    - Library: paho-mqtt
    """
    def __init__(self, broker_url: str, client_id: str, username: str, password: str):
        # Connects to Tuya Cloud MQTT broker with 10s timeout
        # Implements paho-mqtt CallbackAPIVersion.VERSION2 pattern
```

#### Year 3+: ESP32-S3 Local + BLE Fallback

```python
class ESP32AdapterAsync(IMQTTAdapter):
    """
    Async wrapper for ESP32-S3 local MQTT + BLE fallback.
    - Broker: Local MQTT hub (LAN)
    - Authentication: None (local network trust)
    - Failover: BLE fallback when local MQTT offline
    - Library: paho-mqtt (local) + asyncio (fallback coordination)
    - Cache: SQLite for message buffering during BLE fallback
    """
    def __init__(
        self,
        broker_url: str,
        client_id: str,
        ble_fallback_enabled: bool = False,
        local_cache_path: Optional[str] = None,
    ):
        # Connects to local ESP32 MQTT hub with 5s timeout
        # Activates BLE fallback on connection failure if enabled
```

### Dependency Injection

```python
# app/main.py (FastAPI lifespan)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Choose adapter based on configuration
    if settings.mqtt_backend == "tuya":
        adapter = TuyaAdapterAsync(
            broker_url=settings.mqtt_broker_url,
            client_id=settings.mqtt_client_id,
            username=settings.mqtt_username,
            password=settings.mqtt_password,
        )
    elif settings.mqtt_backend == "esp32":
        adapter = ESP32AdapterAsync(
            broker_url=settings.mqtt_broker_url,
            client_id=settings.mqtt_client_id,
            ble_fallback_enabled=True,
        )
    
    service = MQTTService(adapter)
    await service.startup()
    
    yield  # App runs here
    
    await service.shutdown()

app = FastAPI(lifespan=lifespan)
```

---

## Topic Naming Convention (Locked)

### JFA Unify Topic Schema

Defined in `app/services/mqtt_topics.py`:

| Topic | Direction | Payload | QoS | Max Size |
|-------|-----------|---------|-----|----------|
| `jfa/unify/{tenant_id}/device/{device_id}/access/request` | Device → Backend | JSON (PIN/card) | 1 | 512B |
| `jfa/unify/{tenant_id}/device/{device_id}/access/response` | Backend → Device | JSON (granted/denied) | 1 | 256B |
| `jfa/unify/{tenant_id}/device/{device_id}/heartbeat` | Device → Backend | JSON (keepalive) | 1 | 128B |
| `jfa/unify/{tenant_id}/device/{device_id}/status` | Device → Backend | JSON (battery, signal) | 1 | 256B |
| `jfa/unify/admin/audit/access_log` | Backend → Admin | JSON (audit trail) | 1 | 1KB |

### Invariantes

- `{tenant_id}` = UUID v4 (RLS boundary) — e.g., `f47ac10b-58cc-4372-a567-0e02b2c3d479`
- `{device_id}` = UUID v4 (device ID) — e.g., `1f9f2e7a-8d45-4c3b-9e1a-5f2c8d9b3a1c`
- Topic depth max = 7 levels (MQTT broker standard limit)
- Payload max = 4KB (ESP32 SRAM constraint)
- Encoding: UTF-8 JSON (no binary payloads in Year 1-2)

### Topic Builder Utility

```python
from app.services.mqtt_topics import TopicBuilder

# Usage
builder = TopicBuilder(tenant_id=uuid.uuid4(), device_id=uuid.uuid4())
request_topic = builder.access_request()     # Full topic path
response_topic = builder.access_response()
heartbeat_topic = builder.heartbeat()
status_topic = builder.status()
audit_topic = TopicBuilder.audit_log()

# Subscribe patterns
device_pattern = builder.subscribe_device_pattern()  # jfa/unify/{tenant_id}/device/{device_id}/#
tenant_pattern = builder.subscribe_tenant_pattern()  # jfa/unify/{tenant_id}/#
```

---

## Failover Strategy

### Scenario 1: Tuya Hub Online (Primary Path)

```
Device → [Local Tuya Hub] ─(LAN)─→ [Tuya Cloud] → [JFA Backend]
                            (instant)
```

- **Latency:** <100ms local hub → cloud relay
- **Reliability:** LAN + cloud redundancy
- **Failover Trigger:** None (always preferred)

### Scenario 2: Tuya Hub Offline → Cloud Only

```
Device → [Tuya Cloud Direct] → [JFA Backend]
         (connect timeout 30s)
```

- **Latency:** <500ms direct cloud connection (if local hub unavailable)
- **Reliability:** Cloud-only (single point of failure)
- **Failover Trigger:** Local hub unreachable after 30s retry

### Scenario 3: Cloud Offline → SQLite Local Cache (ESP32 only)

```
Device → [ESP32 Local MQTT] → [JFA Backend Cache (SQLite)]
         (offline detection after 30s timeout)
              ↓
        [BLE Fallback] (if enabled)
```

- **Cache Strategy:** SQLite on ESP32 (512MB internal storage capacity)
- **Timeout:** 30s to detect cloud unreachability
- **Retry:** Exponential backoff (1s, 2s, 5s, 10s, stop)
- **Sync:** Batch upload from SQLite when cloud online

### Timeout Configuration

```python
# app/config.py
MQTT_CONNECT_TIMEOUT = 10.0  # Tuya Cloud (seconds)
MQTT_LOCAL_TIMEOUT = 5.0     # ESP32 Local Hub (seconds)
MQTT_FALLBACK_TIMEOUT = 30.0 # Detect offline → SQLite cache (seconds)
MQTT_BACKOFF = [1, 2, 5, 10]  # Exponential backoff (seconds)
```

---

## Phase 2/3 Swap Triggers

Criteria to justify switching from Tuya → ESP32-S3 in Year 3+:

### Trigger T1: Volume Threshold
- **Metric:** >500 devices/month production deployment
- **Rationale:** NRE (Non-Recurring Engineering) cost <€50k amortized at scale
- **Timeline:** Expected Q4 2026 (Month 8 of pilot)

### Trigger T2: Tuya API Breaking Change
- **Event:** Tuya announces MQTT protocol version change or retirement
- **Cost Avoidance:** Switch cost <€50k < rewrite cost on deprecated vendor API
- **Timeline:** If triggered, 6-week sprint to implement ESP32 swap

### Trigger T3: Margin Compression
- **Metric:** Tuya royalty exceeds 15% of gross margin
- **Calculation:** Current ~10% (320 units @ €8 royalty/unit) → 15% threshold = €24k/year cost
- **Action:** Own hardware (ESP32-S3) saves €6k/year after Year 1 NRE
- **Timeline:** Evaluate Q2 2027 (Month 15 of pilot)

---

## Implementation Status

### ✅ Completed (Phase 7, Day 1)

- [x] `IMQTTAdapter` abstract interface (async)
- [x] `TuyaAdapterAsync` implementation
- [x] `ESP32AdapterAsync` implementation (with BLE fallback skeleton)
- [x] `MQTTService` integration layer (FastAPI lifespan)
- [x] Topic naming schema (`mqtt_topics.py`)
- [x] Test suite: 35 tests covering both adapters

### 🔄 In Progress (Phase 7, Day 2-3)

- [ ] Topic schema migration (legacy `jfa/device/{id}/event/*` → new schema)
- [ ] Failover strategy implementation (SQLite cache on ESP32)
- [ ] Documentation review + locking

### 📋 Pending (Phase 7, Day 4-7)

- [ ] Code review (CTO self-review)
- [ ] Pull request merge to `main`
- [ ] CI/CD pipeline validation (if new dependencies)
- [ ] Linear issue: `T3-MQTT-ABSTRACTION-MERGED` (labels: architecture, completed, t3)

---

## Testing Strategy

### Unit Tests (IMQTTAdapter)

| Test | Adapter | Coverage |
|------|---------|----------|
| Initialization + config parsing | Tuya | ✅ |
| Connect success (mocked paho-mqtt) | Tuya | ✅ |
| Connect failure + retry | Tuya | ✅ |
| Publish + QoS handling | Tuya | ✅ |
| Subscribe + callback dispatch | Tuya | ✅ |
| Disconnect + cleanup | Tuya | ✅ |
| is_connected state transitions | Both | ✅ |
| get_status reporting | Both | ✅ |

**Target Coverage:** ≥95% (both adapters combined)

### Integration Tests (Optional, Year 2)

- Mosquitto local broker (docker-compose)
- Tuya hub hardware (staging environment)
- End-to-end PIN validation flow

---

## Backward Compatibility & Migration

### Legacy Topic Support

`app/services/mqtt_topics.py` includes `LegacyTopicBuilder` for Year 1 firmware compatibility:

```python
# Legacy topics (will be deprecated Year 2)
jfa/device/{device_id}/event/pin
jfa/device/{device_id}/event/card
jfa/device/{device_id}/event/state
jfa/device/{device_id}/event/ota
```

**Migration Plan:**
1. Phase 7: Dual-mode support (both schemas accepted)
2. Phase 8 (Week 3-4): Firmware OTA push to new schema
3. Phase 9 (Week 5-6): Deprecation period (90 days)
4. Phase 10: Legacy schema removal

---

## Configuration Example

### Environment Variables (`.env`)

```bash
MQTT_BACKEND=tuya
MQTT_BROKER_URL=mqtt://mqtt.tuyaeu.com:1883
MQTT_CLIENT_ID=jfa-backend-prod-001
MQTT_USERNAME=your_tuya_api_key
MQTT_PASSWORD=your_tuya_api_secret
MQTT_RECONNECT_TIMEOUT=30
MQTT_ENABLE_BLE_FALLBACK=false
MQTT_CACHE_PATH=/data/jfa_mqtt_cache.db
```

### Database Schema (access_logs)

```sql
CREATE TABLE access_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    device_id UUID NOT NULL REFERENCES input_devices(id) ON DELETE CASCADE,
    access_type TEXT NOT NULL,
    pin_hash TEXT,
    card_uid TEXT,
    success BOOLEAN NOT NULL,
    ip_address INET,
    mqtt_topic TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

---

## Success Criteria ✅

- [x] MQTT interface abstraction defined + documented
- [x] Topic naming invariants locked (prod-safe)
- [x] Failover strategy codified (local + cloud + cache)
- [x] Phase 2/3 swap triggers identified + documented
- [ ] Pull request merged to main
- [ ] Tests: 8/8 passing, coverage ≥95%
- [ ] CI/CD pipeline updated (if dependencies changed)

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Abstraction over-engineered | MVP slowdown | MVP uses TuyaMqttBackend only; interface ready for Year 3 |
| Topic schema changed later | Firmware reflash required | Schema locked in this document; rebase point for firmware |
| Tuya API breaking change | Business continuity | ESP32 swap triggers at <€50k cost; 6-week implementation |
| BLE fallback complexity | Missed release | BLE skeleton only (Year 3 implementation); MVP skips BLE |

---

## Next Steps

1. **Day 3 (2026-05-29):** Code review + final schema validation
2. **Day 4-5 (2026-05-30 to 2026-05-31):** Pull request (draft) + CI validation
3. **Day 5 (2026-05-31):** Go/No-Go checkpoint (T1-T5 prerequisites validated)
4. **Day 6-7 (2026-06-01 to 2026-06-02):** Approval + merge to main
5. **Week 2 (2026-06-03+):** T4 (Data Anonymization) unblocked; T5 (Pricing Lock) proceeds in parallel

---

**Document Status:** Locked (Phase 7, Day 2-3)  
**Last Updated:** 2026-05-27  
**Branch:** `feature/mqtt-abstraction-phase7`
