# T3: MQTT Abstraction Layer — DESIGN PHASE

**Data Início:** 2026-05-28 (Day 2, paralelo a T1+T2)  
**Owner:** CTO (arquitetura) + Product (schema design)  
**Objetivo:** Design interface MQTT swappable (Tuya Y1-2 ↔ ESP32-S3 Y3+)  
**Status:** INICIADO ✅  
**Dependência:** Nenhuma (paralelo) | **Bloqueador para:** T4 (Pilot data anonymization), T5 pricing  

---

## Visão Geral

**Problema:** Year 1-2 usa Tuya Hub 6E (cloud + local fallover), Year 3+ pode usar ESP32-S3 (local-first, BLE expansion). Ambos precisam MQTT mas com diferentes topologias.

**Solução:** Interface-based abstraction que desacopla backend (FastAPI + PostgreSQL) de MQTT broker físico. Permite:
- Trocar Tuya ↔ ESP32-S3 sem mudanças backend
- Multi-device suporte (Mix Tuya + ESP32 na transição Y2→Y3)
- Test doubles para unit tests (mock MQTT)
- Local fallover buffer (offline → sync on reconnect)

**Diagrama Conceitual:**

```
┌─────────────────────────────────────────┐
│   FastAPI Backend (PostgreSQL RLS)       │
│   ↑                                       │
│   │ MQTT.Publish(event)                  │
│   │ MQTT.Subscribe(topic)                │
│   │                                       │
└───┼──────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│   IMQTTAdapter Interface                 │
│  (abstract contract)                     │
└─────────────────────────────────────────┘
    ▲                     ▲
    │                     │
    │ Y1-2                │ Y3+
┌───┴─────────┐    ┌──────┴──────┐
│ TuyaAdapter │    │ ESP32Adapter │
│ (cloud)     │    │ (local)      │
└─────────────┘    └──────────────┘
    │                     │
    ▼                     ▼
┌──────────────┐   ┌──────────────┐
│ Tuya Cloud   │   │ ESP32-S3 Hub │
│ (Frankfurt)  │   │ (Local WiFi) │
└──────────────┘   └──────────────┘
```

---

## 1. Interface IMQTTAdapter (Contrato Abstrato)

**Linguagem:** Go (backend) | **Package:** `internal/mqtt/adapter`

```go
package adapter

import "context"

// IMQTTAdapter defines contract for MQTT broker backend.
// Implementations: TuyaAdapter (Year 1-2), ESP32Adapter (Year 3+)
type IMQTTAdapter interface {
	// Connect establishes connection to broker with retries + backoff
	Connect(ctx context.Context) error

	// Disconnect gracefully closes connection + flushes pending messages
	Disconnect(ctx context.Context) error

	// IsConnected returns true if connection is active
	IsConnected() bool

	// Publish sends event to topic, with local buffer fallback if offline
	// Topic format: "jfa/device/{deviceID}/event/{eventType}"
	// Returns: nil if sent immediately, or buffered for sync on reconnect
	Publish(ctx context.Context, topic string, payload []byte, qos uint8) error

	// Subscribe registers callback for topic with auto-resubscribe on reconnect
	// Callback must be non-blocking (spawn goroutine if heavy processing)
	Subscribe(ctx context.Context, topic string, callback MessageCallback) error

	// Unsubscribe removes callback for topic
	Unsubscribe(ctx context.Context, topic string) error

	// GetStatus returns connection metadata (broker, latency, buffered count)
	GetStatus() Status

	// LocalBuffer returns interface to offline buffer (fallover mechanism)
	LocalBuffer() ILocalBuffer
}

// MessageCallback is invoked when message arrives on subscribed topic
type MessageCallback func(ctx context.Context, topic string, payload []byte) error

// Status provides connection health info
type Status struct {
	IsConnected      bool          `json:"is_connected"`
	BrokerURL        string        `json:"broker_url"`
	LastPingLatency  time.Duration `json:"last_ping_latency_ms"`
	BufferedMessages int           `json:"buffered_messages"`
	ConnectedSince   time.Time     `json:"connected_since"`
	DisconnectCount  int           `json:"disconnect_count"`
}

// ILocalBuffer manages offline message queue
type ILocalBuffer interface {
	// Enqueue adds message to offline queue (max 1000 messages or 10MB)
	Enqueue(topic string, payload []byte) error

	// Flush sends all buffered messages on reconnect
	// Called automatically by adapter, but exposed for testing
	Flush(ctx context.Context) (flushed int, err error)

	// Size returns current buffered message count
	Size() int

	// Clear drains buffer (dangerous, for tests only)
	Clear()
}
```

---

## 2. TuyaAdapter Implementation (Year 1-2)

**Path:** `internal/mqtt/adapter/tuya_adapter.go`

### Constructor & Lifecycle

```go
package adapter

import (
	"context"
	"fmt"
	"time"

	mqtt "github.com/eclipse/paho.mqtt.golang"
)

// TuyaAdapter implements IMQTTAdapter for Tuya Cloud Hub 6E
type TuyaAdapter struct {
	config      TuyaConfig
	client      mqtt.Client
	buffer      *LocalBuffer
	subscribers map[string]MessageCallback
	status      Status
	mu          sync.RWMutex
}

type TuyaConfig struct {
	BrokerURL    string        // e.g., "mqtt://tuya-emea.mqtt.tuya.eu:1883"
	ClientID     string        // Device ID from Tuya Hub
	Username     string        // Tuya auth token
	Password     string        // Tuya key
	KeepAlive    time.Duration // Default 60s
	MaxRetries   int           // Default 5
	RetryBackoff time.Duration // Default 2s exponential
}

// NewTuyaAdapter creates Tuya MQTT adapter
func NewTuyaAdapter(cfg TuyaConfig) *TuyaAdapter {
	return &TuyaAdapter{
		config:      cfg,
		buffer:      NewLocalBuffer(1000, 10*1024*1024), // 1000 msgs or 10MB max
		subscribers: make(map[string]MessageCallback),
		status: Status{
			IsConnected: false,
			BrokerURL:   cfg.BrokerURL,
		},
	}
}

// Connect establishes MQTT connection with exponential backoff
func (ta *TuyaAdapter) Connect(ctx context.Context) error {
	ta.mu.Lock()
	defer ta.mu.Unlock()

	opts := mqtt.NewClientOptions()
	opts.AddBroker(ta.config.BrokerURL)
	opts.SetClientID(ta.config.ClientID)
	opts.SetUsername(ta.config.Username)
	opts.SetPassword(ta.config.Password)
	opts.SetKeepAlive(ta.config.KeepAlive)
	opts.SetAutoReconnect(true)
	opts.SetMaxReconnectInterval(time.Minute)

	// Connection callback
	opts.SetOnConnect(func(c mqtt.Client) {
		ta.mu.Lock()
		ta.status.IsConnected = true
		ta.status.ConnectedSince = time.Now()
		ta.mu.Unlock()

		// Resubscribe to all topics
		ta.resubscribeAll()

		// Flush offline buffer
		if _, err := ta.buffer.Flush(ctx); err != nil {
			// Log: buffer flush error (non-fatal)
		}
	})

	// Disconnect callback
	opts.SetConnectionLostHandler(func(c mqtt.Client, err error) {
		ta.mu.Lock()
		ta.status.IsConnected = false
		ta.status.DisconnectCount++
		ta.mu.Unlock()
		// Automatic reconnect handled by SetAutoReconnect(true)
	})

	ta.client = mqtt.NewClient(opts)

	// Retry loop with exponential backoff
	var lastErr error
	for attempt := 0; attempt < ta.config.MaxRetries; attempt++ {
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
		}

		token := ta.client.Connect()
		if token.Wait() && token.Error() == nil {
			ta.status.IsConnected = true
			ta.status.ConnectedSince = time.Now()
			return nil
		}

		lastErr = token.Error()
		backoff := ta.config.RetryBackoff * time.Duration(1<<uint(attempt)) // 2s, 4s, 8s, 16s, 32s
		select {
		case <-time.After(backoff):
		case <-ctx.Done():
			return ctx.Err()
		}
	}

	return fmt.Errorf("failed to connect to Tuya broker after %d retries: %w", ta.config.MaxRetries, lastErr)
}

// Disconnect gracefully closes connection
func (ta *TuyaAdapter) Disconnect(ctx context.Context) error {
	ta.mu.Lock()
	defer ta.mu.Unlock()

	if ta.client == nil || !ta.status.IsConnected {
		return nil
	}

	// Flush pending buffer before disconnect
	ta.buffer.Flush(ctx) // Best effort, ignore error

	ta.client.Disconnect(250) // 250ms grace period
	ta.status.IsConnected = false

	return nil
}

// IsConnected returns connection status
func (ta *TuyaAdapter) IsConnected() bool {
	ta.mu.RLock()
	defer ta.mu.RUnlock()
	return ta.status.IsConnected && ta.client.IsConnected()
}

// Publish sends MQTT message or buffers if offline
func (ta *TuyaAdapter) Publish(ctx context.Context, topic string, payload []byte, qos uint8) error {
	ta.mu.RLock()
	connected := ta.status.IsConnected
	ta.mu.RUnlock()

	if connected && ta.client.IsConnected() {
		// Send immediately
		token := ta.client.Publish(topic, qos, false, payload)
		if token.Wait() && token.Error() != nil {
			// If publish fails, buffer for later
			return ta.buffer.Enqueue(topic, payload)
		}
		return nil
	}

	// Offline: buffer for reconnect
	return ta.buffer.Enqueue(topic, payload)
}

// Subscribe registers callback for topic
func (ta *TuyaAdapter) Subscribe(ctx context.Context, topic string, callback MessageCallback) error {
	ta.mu.Lock()
	ta.subscribers[topic] = callback
	ta.mu.Unlock()

	if ta.IsConnected() {
		token := ta.client.Subscribe(topic, 1, func(_ mqtt.Client, msg mqtt.Message) {
			if err := callback(ctx, msg.Topic(), msg.Payload()); err != nil {
				// Log: callback error (non-fatal)
			}
		})
		if token.Wait() && token.Error() != nil {
			return token.Error()
		}
	}

	return nil
}

// Unsubscribe removes callback
func (ta *TuyaAdapter) Unsubscribe(ctx context.Context, topic string) error {
	ta.mu.Lock()
	delete(ta.subscribers, topic)
	ta.mu.Unlock()

	if ta.IsConnected() {
		token := ta.client.Unsubscribe(topic)
		if token.Wait() && token.Error() != nil {
			return token.Error()
		}
	}

	return nil
}

// GetStatus returns connection metadata
func (ta *TuyaAdapter) GetStatus() Status {
	ta.mu.RLock()
	defer ta.mu.RUnlock()
	ta.status.BufferedMessages = ta.buffer.Size()
	return ta.status
}

// LocalBuffer exposes offline buffer
func (ta *TuyaAdapter) LocalBuffer() ILocalBuffer {
	return ta.buffer
}

// resubscribeAll re-registers all callbacks after reconnect
func (ta *TuyaAdapter) resubscribeAll() {
	ta.mu.RLock()
	subs := ta.subscribers
	ta.mu.RUnlock()

	for topic, callback := range subs {
		token := ta.client.Subscribe(topic, 1, func(_ mqtt.Client, msg mqtt.Message) {
			if err := callback(context.Background(), msg.Topic(), msg.Payload()); err != nil {
				// Log: callback error
			}
		})
		token.Wait()
	}
}
```

---

## 3. LocalBuffer Implementation (Offline Queue)

**Path:** `internal/mqtt/adapter/local_buffer.go`

```go
package adapter

import (
	"context"
	"fmt"
	"sync"
	"time"
)

// LocalBuffer manages offline message queue during network outage
type LocalBuffer struct {
	messages []*BufferedMessage
	maxSize  int           // Max message count
	maxBytes int           // Max total size in bytes
	mu       sync.Mutex
	onFlush  func(topic string, payload []byte) error // Callback for flush
}

type BufferedMessage struct {
	Topic     string
	Payload   []byte
	QueuedAt  time.Time
	RetryCount int
}

// NewLocalBuffer creates offline queue with size limits
func NewLocalBuffer(maxMessages, maxBytes int) *LocalBuffer {
	return &LocalBuffer{
		messages: make([]*BufferedMessage, 0, maxMessages),
		maxSize:  maxMessages,
		maxBytes: maxBytes,
	}
}

// Enqueue adds message to offline queue
func (lb *LocalBuffer) Enqueue(topic string, payload []byte) error {
	lb.mu.Lock()
	defer lb.mu.Unlock()

	// Check size limits
	if len(lb.messages) >= lb.maxSize {
		return fmt.Errorf("offline buffer full: %d/%d messages", len(lb.messages), lb.maxSize)
	}

	totalBytes := 0
	for _, msg := range lb.messages {
		totalBytes += len(msg.Payload)
	}
	if totalBytes+len(payload) > lb.maxBytes {
		return fmt.Errorf("offline buffer full: %d/%d bytes", totalBytes, lb.maxBytes)
	}

	lb.messages = append(lb.messages, &BufferedMessage{
		Topic:      topic,
		Payload:    payload,
		QueuedAt:   time.Now(),
		RetryCount: 0,
	})

	return nil
}

// Flush sends all buffered messages (called on reconnect)
func (lb *LocalBuffer) Flush(ctx context.Context) (flushed int, err error) {
	lb.mu.Lock()
	msgs := lb.messages
	lb.messages = nil
	lb.mu.Unlock()

	for _, msg := range msgs {
		select {
		case <-ctx.Done():
			// Return unprocessed messages to buffer
			lb.mu.Lock()
			lb.messages = append(msgs[flushed:], lb.messages...)
			lb.mu.Unlock()
			return flushed, ctx.Err()
		default:
		}

		// Call flush callback (typically MQTT Publish)
		if lb.onFlush != nil {
			if err := lb.onFlush(msg.Topic, msg.Payload); err != nil {
				msg.RetryCount++
				if msg.RetryCount < 3 {
					// Retry a few times, then discard
					lb.mu.Lock()
					lb.messages = append(lb.messages, msg)
					lb.mu.Unlock()
				}
				continue
			}
		}

		flushed++
	}

	return flushed, nil
}

// Size returns buffered message count
func (lb *LocalBuffer) Size() int {
	lb.mu.Lock()
	defer lb.mu.Unlock()
	return len(lb.messages)
}

// Clear drains buffer (test only)
func (lb *LocalBuffer) Clear() {
	lb.mu.Lock()
	defer lb.mu.Unlock()
	lb.messages = nil
}
```

---

## 4. MQTT Event Schema (Tuya ↔ ESP32-S3)

Both adapters use same event schema. Enforces consistency for backend parsing.

### Pin Hash Event (Authentication)

```json
{
  "event_id": "evt_20260529_120530_abc123",
  "device_id": "hub_001",
  "event_type": "pin_attempt",
  "timestamp": "2026-05-29T12:05:30Z",
  "data": {
    "pin_hash": "sha256:abc123def456...",
    "card_uid": "04A1B2C3D4E5F6G7",
    "access_result": "granted|denied|invalid",
    "tenant_id": "tenant_123"
  },
  "source": "tuya|esp32"
}
```

### Card UID Event (NFC/RFID Read)

```json
{
  "event_id": "evt_20260529_120531_xyz789",
  "device_id": "hub_001",
  "event_type": "card_read",
  "timestamp": "2026-05-29T12:05:31Z",
  "data": {
    "card_uid": "04A1B2C3D4E5F6G7",
    "card_type": "nfc_iso14443a|iso15693|mifare",
    "signal_strength": -75,
    "access_result": "granted|denied|unknown"
  },
  "source": "tuya|esp32"
}
```

### Device State Event (Heartbeat)

```json
{
  "event_id": "evt_20260529_120532_state001",
  "device_id": "hub_001",
  "event_type": "device_state",
  "timestamp": "2026-05-29T12:05:32Z",
  "data": {
    "uptime_seconds": 86400,
    "wifi_signal": -65,
    "memory_free": 512000,
    "local_buffer_size": 0,
    "firmware_version": "6.1.2",
    "is_fallover_mode": false
  },
  "source": "tuya|esp32"
}
```

### OTA Notification Event

```json
{
  "event_id": "evt_20260529_120533_ota001",
  "device_id": "hub_001",
  "event_type": "ota_notification",
  "timestamp": "2026-05-29T12:05:33Z",
  "data": {
    "firmware_version_available": "6.2.0",
    "download_url": "https://tuya-emea.cdn.tuya.com/firmware/...",
    "checksum": "md5:abc123...",
    "is_critical": false
  },
  "source": "tuya|esp32"
}
```

---

## 5. ESP32Adapter Implementation (Year 3+)

**Path:** `internal/mqtt/adapter/esp32_adapter.go`

### Key Differences vs TuyaAdapter

```go
// ESP32Adapter implements IMQTTAdapter for local ESP32-S3 hub
type ESP32Adapter struct {
	config      ESP32Config
	client      mqtt.Client        // Paho MQTT (same as Tuya)
	buffer      *LocalBuffer
	subscribers map[string]MessageCallback
	status      Status
	mu          sync.RWMutex
}

type ESP32Config struct {
	BrokerURL    string        // e.g., "mqtt://192.168.1.100:1883" (local IP)
	ClientID     string        // Device ID (UUID)
	KeepAlive    time.Duration // Shorter for local (30s)
	MaxRetries   int           // Default 3 (faster fail-over to BLE fallback)
	RetryBackoff time.Duration // Default 500ms (faster local recovery)
	
	// ESP32-specific
	BLEFallbackEnabled bool   // Use BLE if WiFi drops
	LocalCachePath     string // Path to local SQLite cache
	SyncInterval       time.Duration // Sync to cloud broker interval (300s)
}

// Connect: Similar to TuyaAdapter but with local fallback logic
// - If WiFi fails N times, trigger BLE fallback mode
// - Local SQLite cache for events during cloud disconnect
// - Periodic sync with cloud broker when WiFi recovers

// Publish: Writes to local SQLite first, then MQTT immediately if connected
// - On reconnect, SQLite events pushed to MQTT
// - Tuya adapter: MQTT → buffer → retry
// - ESP32 adapter: MQTT → SQLite cache → cloud sync
```

---

## 6. Backend Integration (FastAPI)

**Path:** `backend/mqtt/service.py`

```python
from typing import Protocol, Optional
from abc import ABC, abstractmethod

class IMQTTAdapter(ABC):
    @abstractmethod
    async def connect(self) -> None: pass

    @abstractmethod
    async def disconnect(self) -> None: pass

    @abstractmethod
    async def is_connected(self) -> bool: pass

    @abstractmethod
    async def publish(self, topic: str, payload: bytes, qos: int = 1) -> None: pass

    @abstractmethod
    async def subscribe(self, topic: str, callback) -> None: pass

    @abstractmethod
    async def get_status(self) -> dict: pass


class MQTTService:
    def __init__(self, adapter: IMQTTAdapter):
        self.adapter = adapter
    
    async def startup(self):
        await self.adapter.connect()
        # Subscribe to device events
        await self.adapter.subscribe("jfa/device/+/event/+", self.on_device_event)
    
    async def on_device_event(self, topic: str, payload: bytes):
        event = json.loads(payload)
        # Parse and store in PostgreSQL RLS
        await self.store_event(event)
    
    async def store_event(self, event: dict):
        # Insert into access_logs table with tenant isolation (RLS)
        async with self.db.transaction():
            await self.db.execute(
                """
                INSERT INTO access_logs (event_id, device_id, event_type, data)
                VALUES ($1, $2, $3, $4)
                """,
                event["event_id"], event["device_id"], event["event_type"], event
            )

# Dependency injection in FastAPI
app = FastAPI()

@app.on_event("startup")
async def startup():
    adapter = TuyaAdapter(config)  # Swap: ESP32Adapter(config) in Year 3+
    mqtt_service = MQTTService(adapter)
    await mqtt_service.startup()
    app.state.mqtt = mqtt_service

@app.on_event("shutdown")
async def shutdown():
    await app.state.mqtt.adapter.disconnect()
```

---

## 7. Unit Testing Strategy

**Path:** `internal/mqtt/adapter/adapter_test.go`

```go
// MockAdapter implements IMQTTAdapter for testing
type MockAdapter struct {
	published     []PublishedMessage
	subscribers   map[string]MessageCallback
	isConnected   bool
	connectErr    error
}

func (m *MockAdapter) Publish(ctx context.Context, topic string, payload []byte, qos uint8) error {
	m.published = append(m.published, PublishedMessage{topic, payload})
	return nil
}

// Test case: Offline buffer + reconnect flush
func TestLocalBufferFlush(t *testing.T) {
	adapter := NewTuyaAdapter(TuyaConfig{...})
	adapter.status.IsConnected = false
	
	// Publish 5 messages offline
	for i := 0; i < 5; i++ {
		adapter.Publish(context.Background(), "jfa/device/hub_001/event/pin", []byte("test"), 1)
	}
	
	assert.Equal(t, 5, adapter.LocalBuffer().Size())
	
	// Simulate reconnect
	adapter.status.IsConnected = true
	flushed, err := adapter.LocalBuffer().Flush(context.Background())
	
	assert.NoError(t, err)
	assert.Equal(t, 5, flushed)
	assert.Equal(t, 0, adapter.LocalBuffer().Size())
}
```

---

## 8. Timeline & Deliverables (Week 1)

| Dia | Tarefa | Owner | Status |
|-----|--------|-------|--------|
| Day 2-3 (2026-05-28/29) | Interface IMQTTAdapter (Go) + TuyaAdapter | CTO | TODO |
| Day 3-4 (2026-05-29/30) | LocalBuffer + reconnect logic | CTO | TODO |
| Day 4-5 (2026-05-30/31) | ESP32Adapter skeleton + config | CTO | TODO |
| Day 5-6 (2026-05-31/06-01) | FastAPI integration + dependency injection | Backend | TODO |
| Day 6-7 (2026-06-01/02) | Unit tests (85% coverage target) | QA | TODO |
| Day 7 (2026-06-02) | **Schema lock + approval** (Freeze for T4) | Product | TODO |

---

## 9. Design Decisions & Rationale

| Decisão | Opção | Rationale |
|---------|-------|-----------|
| Language | Go interface (backend), Python async (FastAPI) | Type-safe, testable; FastAPI is async-native |
| Queue mechanism | In-memory + Local SQLite (ESP32 only) | Fast, bounded, survives hub restart |
| QoS level | 1 (at-least-once) | Trade-off: reliability vs latency (0 = none, 2 = slow) |
| Resubscribe | Auto on reconnect | Prevents subscription loss on network flap |
| Buffer flush | On reconnect + periodic sync | Ensures eventual consistency |
| Test doubles | MockAdapter (inmem) | Fast, deterministic, no external dependency |

---

## 10. Schema Lock Criteria (Day 7 Checkpoint)

**Before T4 can start, T3 must deliver:**

- ✅ IMQTTAdapter interface documented + approved
- ✅ Event schema (PIN, Card UID, Device State, OTA) frozen
- ✅ TuyaAdapter functional + tested (85% coverage)
- ✅ FastAPI integration (dependency injection pattern)
- ✅ LocalBuffer behavior specified + tested
- ✅ ESP32Adapter constructor + Connect() skeleton
- ✅ No breaking changes to schema after freeze

**Go/No-Go:** Day 7 (2026-06-02) schema approval unlocks T4 (Pilot data anonymization) Day 8-10.

---

**Versão:** 1.0  
**Last Updated:** 2026-05-28 (iniciado)  
**Owner:** CTO (Rafael Martins — assumido)  
**Next Checkpoint:** 2026-05-31 (Interface review + TuyaAdapter MVP)  
**Critical Dependency:** Schema lock by 2026-06-02 (prerequisite T4)
