# JFA_Unify — Plano de Testes Detalhado

## Visão Geral

Teste coverage target: **85% (dev-only modules)** → 95%+ (critical paths)

Matriz de testes: Unit + Integration + E2E + Load + Security + Compliance

---

## 1. Unit Tests (Jest/Pytest)

### PIN Validation Module
```python
# tests/unit/test_pin_validation.py
class TestPINValidation(TestCase):
    def test_pin_4digit_valid(self):
        assert validate_pin("1234") == True
    
    def test_pin_12digit_valid(self):
        assert validate_pin("123456789012") == True
    
    def test_pin_3digit_invalid(self):
        assert validate_pin("123") == False
    
    def test_pin_13digit_invalid(self):
        assert validate_pin("1234567890123") == False
    
    def test_pin_hash_bcrypt(self):
        pin_hash = hash_pin("1234")
        assert verify_pin("1234", pin_hash) == True
        assert verify_pin("5678", pin_hash) == False
    
    def test_rate_limiting_3attempts(self):
        # 3 failed attempts = 60s lockout
        for i in range(3):
            attempt_pin("1234", "wrong")
        assert is_locked("1234") == True
        assert get_lockout_seconds("1234") == 60
    
    def test_rate_limiting_reset(self):
        # Successful PIN = reset lockout
        set_lockout("1234", 60)
        verify_pin_success("1234")
        assert is_locked("1234") == False

    Coverage target: 100%
    Critical paths: PIN hashing, rate-limiting, lockout
```

### Card UID Parsing (PN532)
```python
# tests/unit/test_card_uid.py
class TestCardUID(TestCase):
    def test_uid_parsing_4bytes(self):
        # PN532 returns 4-byte UID (standard)
        raw_data = bytes([0x04, 0x5A, 0xCD, 0x12])
        uid = parse_card_uid(raw_data)
        assert uid == "045ACD12"
    
    def test_uid_parsing_7bytes(self):
        # Some cards return 7-byte UID
        raw_data = bytes([0x08, 0x04, 0x5A, 0xCD, 0x12, 0xFF, 0xAA, 0xBB])
        uid = parse_card_uid(raw_data)
        assert uid == "08045ACD12FFAABB"
    
    def test_crc_validation(self):
        # Validate CRC-16 checksum
        uid_with_crc = "045ACD12" + crc16("045ACD12")
        assert validate_card_crc(uid_with_crc) == True
    
    def test_malformed_uid_rejected(self):
        # Reject < 4 bytes or invalid hex
        assert parse_card_uid(bytes([0x04, 0x5A])) == None
        assert parse_card_uid("invalid_hex") == None

    Coverage target: 100%
```

### MQTT Topic Validation
```python
# tests/unit/test_mqtt_topics.py
class TestMQTTTopics(TestCase):
    def test_topic_format_tuya_device(self):
        topic = "jfa/tuya/device/abc123/command"
        assert is_valid_topic(topic) == True
    
    def test_topic_device_id_extraction(self):
        topic = "jfa/tuya/device/abc123/command"
        device_id = extract_device_id(topic)
        assert device_id == "abc123"
    
    def test_invalid_topic_structure(self):
        invalid = "jfa/invalid/structure"
        assert is_valid_topic(invalid) == False
    
    def test_topic_authorization(self):
        # Only devices in access_control.input_devices allowed
        topic = "jfa/tuya/device/abc123/command"
        authorized = is_topic_authorized(topic, user_id="user1")
        assert authorized == True
    
    def test_topic_rate_limiting(self):
        # Max 10 messages/sec per device
        for i in range(11):
            publish("topic", "msg")
        assert is_rate_limited("topic") == True

    Coverage target: 100%
```

### RLS Query Authorization
```python
# tests/unit/test_rls_authorization.py
class TestRLSAuth(TestCase):
    def test_user_can_access_own_location(self):
        # User1 in location A can see A
        query = "SELECT * FROM input_devices WHERE tenant_id = 'tenant1'"
        rows = execute_rls(query, user_id="user1", tenant_id="tenant1")
        assert len(rows) == devices_in_location_A
    
    def test_user_cannot_access_other_tenant(self):
        # User1 in tenant1 cannot see tenant2
        query = "SELECT * FROM input_devices WHERE tenant_id = 'tenant2'"
        rows = execute_rls(query, user_id="user1", tenant_id="tenant2")
        assert len(rows) == 0
    
    def test_cross_location_access_blocked(self):
        # User in location A cannot see location B (same tenant)
        query = "SELECT * FROM input_devices WHERE location_id = 'loc_b'"
        rows = execute_rls(query, user_id="user1", location_id="loc_a")
        assert len(rows) == 0

    Coverage target: 100%
    Critical: Row-level security enforcement
```

### Stripe Webhook Signature Verification
```python
# tests/unit/test_stripe_signature.py
class TestStripeSignature(TestCase):
    def test_valid_signature(self):
        payload = '{"id": "evt_123"}'
        signature = create_signature(payload, secret="sk_test_123")
        assert verify_signature(payload, signature, "sk_test_123") == True
    
    def test_invalid_signature_rejected(self):
        payload = '{"id": "evt_123"}'
        invalid_sig = "invalid_signature"
        assert verify_signature(payload, invalid_sig, "sk_test_123") == False
    
    def test_replay_attack_prevention(self):
        # Timestamp > 5 min = reject
        payload = create_payload(timestamp=time.time() - 300)
        assert is_payload_fresh(payload) == False
    
    def test_webhook_idempotency(self):
        # Same event_id processed twice = idempotent
        event_id = "evt_123"
        process_webhook(event_id)
        process_webhook(event_id)
        assert get_transaction_count() == 1

    Coverage target: 100%
    Critical: Security-sensitive
```

---

## 2. Integration Tests

### Tuya Hub ↔ MQTT Broker (TLS Handshake)
```python
# tests/integration/test_tuya_mqtt_integration.py
class TestTuyaMQTTIntegration(TestCase):
    def setUp(self):
        self.mqtt_broker = MockMQTTBroker(port=1883, tls=True)
        self.tuya_hub = TuyaHub(host="127.0.0.1", token="test_token")
    
    def test_tls_handshake_success(self):
        # Hub connects with valid cert
        assert self.tuya_hub.connect() == True
        assert self.mqtt_broker.is_connected(self.tuya_hub) == True
    
    def test_cert_validation_failure(self):
        # Hub rejects invalid cert
        self.mqtt_broker.set_cert("invalid_cert.pem")
        assert self.tuya_hub.connect() == False
    
    def test_message_pub_sub(self):
        self.tuya_hub.connect()
        self.tuya_hub.subscribe("jfa/tuya/device/+/status")
        self.mqtt_broker.publish("jfa/tuya/device/abc123/status", '{"online": true}')
        message = self.tuya_hub.receive(timeout=5)
        assert message["online"] == True
    
    def test_offline_fallback(self):
        # If MQTT offline, use cached token
        self.mqtt_broker.stop()
        result = self.tuya_hub.actuate_relay("relay1", "on")
        assert result == "using_cached_token"

    Coverage: Integration points
    Timeout: 30s per test
```

### PIN → Database → Relay Actuate (End-to-End)
```python
# tests/integration/test_pin_to_relay.py
class TestPINToRelayFlow(TestCase):
    def setUp(self):
        self.db = TestDatabase()
        self.mqtt = MockMQTTBroker()
        self.api = FastAPITestClient()
    
    def test_successful_pin_entry_relay_actuate(self):
        # 1. POST /access/pin with valid PIN
        response = self.api.post("/access/pin", json={
            "pin": "1234",
            "device_id": "kp_abc123",
            "location_id": "loc_a"
        })
        assert response.status_code == 200
        assert response.json()["access_granted"] == True
        
        # 2. Database logs input_event
        event = self.db.query("SELECT * FROM input_events WHERE device_id='kp_abc123' ORDER BY created_at DESC LIMIT 1")
        assert event.pin_hash is not None
        assert event.result == "access_granted"
        
        # 3. MQTT relay actuate message published
        relay_msg = self.mqtt.get_last_message("jfa/tuya/device/relay_xyz/command")
        assert relay_msg["command"] == "on"
        assert relay_msg["duration"] == 5  # 5s pulse
    
    def test_invalid_pin_no_relay(self):
        response = self.api.post("/access/pin", json={
            "pin": "0000",  # wrong PIN
            "device_id": "kp_abc123"
        })
        assert response.status_code == 403
        assert response.json()["access_granted"] == False
        
        # Relay NOT actuated
        relay_messages = self.mqtt.get_messages("jfa/tuya/device/relay_xyz/command")
        assert len(relay_messages) == 0

    Coverage: Critical path
    Timeout: 10s
```

### Card UID → Suite RLS Query → AccessPay Balance Check
```python
# tests/integration/test_card_to_accesspay.py
class TestCardToAccessPay(TestCase):
    def test_card_uid_query_suite_balance(self):
        # 1. Card reader sends UID
        card_uid = "045ACD12"
        
        # 2. Query Suite with RLS (multi-tenant isolation)
        query_result = self.suite_db.execute_rls(
            "SELECT balance FROM access_pay_account WHERE card_uid = %s",
            (card_uid,),
            user_id="user1",
            tenant_id="tenant1"
        )
        
        # Should only see cards in user1's tenant
        assert len(query_result) == 1
        assert query_result[0]["balance"] > 0
        
        # 3. Check access granted
        balance = query_result[0]["balance"]
        can_access = balance >= ACCESS_COST
        assert can_access == True
    
    def test_card_cross_tenant_blocked(self):
        # User in tenant1 cannot see tenant2 cards
        query_result = self.suite_db.execute_rls(
            "SELECT balance FROM access_pay_account WHERE tenant_id = 'tenant2'",
            (),
            user_id="user1",
            tenant_id="tenant1"
        )
        assert len(query_result) == 0

    Coverage: Security-critical
```

### Failover: Hub Offline → Cached Tokens + Local MQTT
```python
# tests/integration/test_failover_offline_hub.py
class TestFailoverOfflineHub(TestCase):
    def test_hub_offline_use_cache(self):
        # Pre-populate Redis cache with valid tokens
        cache.set("device:abc123:token", "cached_token_xyz", ttl=3600)
        
        # MQTT broker goes offline
        self.mqtt.stop()
        
        # Retry with cached token
        result = self.api.post("/access/pin", json={"pin": "1234"})
        assert result.status_code == 200
        assert result.json()["using_cache"] == True
    
    def test_cache_token_expiry(self):
        # Cache token expired > 1 hour
        cache.set("device:abc123:token", "expired_token", ttl=-1)
        
        # No cached token available
        self.mqtt.stop()
        result = self.api.post("/access/pin", json={"pin": "1234"})
        assert result.status_code == 503  # Service unavailable
        assert result.json()["error"] == "hub_offline_no_cache"

    Coverage: Resilience
```

### Moloni API Recibo Generation
```python
# tests/integration/test_moloni_recibo.py
class TestMoloniRecibo(TestCase):
    def test_generate_invoice_success(self):
        # Create transaction via Stripe
        transaction = {
            "stripe_tx_id": "pi_123",
            "amount": 5.00,
            "description": "Access to WC-A",
            "customer": {"email": "user@example.com"}
        }
        
        # Generate Moloni invoice
        response = moloni_client.create_invoice(transaction)
        assert response.status_code == 201
        assert response.invoice_number is not None
        
        # Validate XML (SAF-T format)
        xml = export_saft_invoice(response.invoice_id)
        assert validate_saft_xml(xml) == True
    
    def test_moloni_api_error_handling(self):
        # Moloni API timeout → fallback
        moloni_client.set_timeout(0.001)  # Force timeout
        
        response = moloni_client.create_invoice({"amount": 5.00})
        assert response.error == "timeout"
        # Fallback: store locally, retry background job
        assert is_stored_for_retry(response.tx_id) == True

    Coverage: Payment integration
```

---

## 3. E2E Tests (Selenium)

### SvelteKit PIN Pad UI (Keyboard Input + Submit)
```python
# tests/e2e/test_pin_pad_ui.py
class TestPINPadUI(SeleniumTestCase):
    def test_pin_pad_keyboard_input(self):
        driver = self.driver
        driver.get("http://localhost:5173/access/pin")
        
        # Find PIN pad
        input_field = driver.find_element(By.ID, "pin-input")
        
        # Type PIN
        input_field.send_keys("1234")
        assert input_field.value == "1234"
    
    def test_pin_pad_backspace(self):
        input_field = driver.find_element(By.ID, "pin-input")
        input_field.send_keys("12345")
        input_field.send_keys(Keys.BACKSPACE)
        assert input_field.value == "1234"
    
    def test_pin_pad_submit_success(self):
        input_field = driver.find_element(By.ID, "pin-input")
        submit_btn = driver.find_element(By.ID, "submit-pin")
        
        input_field.send_keys("1234")
        submit_btn.click()
        
        # Wait for result
        result = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "access-result"))
        )
        assert "Access Granted" in result.text
    
    def test_pin_pad_error_display(self):
        input_field = driver.find_element(By.ID, "pin-input")
        submit_btn = driver.find_element(By.ID, "submit-pin")
        
        input_field.send_keys("0000")  # wrong
        submit_btn.click()
        
        error = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "error"))
        )
        assert "Invalid PIN" in error.text

    Timeout: 30s per test
```

### NFC Card Reader Simulation (Mock PN532)
```python
# tests/e2e/test_card_reader_simulation.py
class TestCardReaderE2E(SeleniumTestCase):
    def test_card_read_simulation(self):
        # Mock PN532 device via WebSocket
        ws = self.create_mock_pn532_websocket()
        
        driver.get("http://localhost:5173/access/card")
        
        # Simulate card read
        ws.send({
            "type": "card_detected",
            "uid": "045ACD12",
            "timestamp": time.time()
        })
        
        # Wait for card display
        card_display = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "card-uid"))
        )
        assert "045ACD12" in card_display.text
    
    def test_card_invalid_uid(self):
        ws = self.create_mock_pn532_websocket()
        
        ws.send({
            "type": "card_detected",
            "uid": "INVALID",
            "timestamp": time.time()
        })
        
        error = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "error"))
        )
        assert "Invalid card" in error.text

    Timeout: 30s per test
```

### Double-Auth Flow (Card → PIN → Relay)
```python
# tests/e2e/test_double_auth_flow.py
class TestDoubleAuthFlow(SeleniumTestCase):
    def test_double_auth_success(self):
        driver.get("http://localhost:5173/access/double-auth")
        
        # Step 1: Tap card
        self.simulate_card_read("045ACD12")
        card_element = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "card-confirmed"))
        )
        assert card_element.is_displayed()
        
        # Step 2: Enter PIN
        pin_input = driver.find_element(By.ID, "pin-input")
        pin_input.send_keys("1234")
        submit = driver.find_element(By.ID, "submit-pin")
        submit.click()
        
        # Step 3: Access granted
        result = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "access-result"))
        )
        assert "Access Granted" in result.text
    
    def test_double_auth_invalid_pin(self):
        # Card OK, PIN fails
        self.simulate_card_read("045ACD12")
        
        pin_input = driver.find_element(By.ID, "pin-input")
        pin_input.send_keys("0000")
        submit = driver.find_element(By.ID, "submit-pin")
        submit.click()
        
        error = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "error"))
        )
        assert "Access Denied" in error.text

    Timeout: 60s
    Critical path
```

### Payment Confirmation (Stripe Test Mode)
```python
# tests/e2e/test_payment_confirmation.py
class TestPaymentConfirmation(SeleniumTestCase):
    def test_payment_success_confirmation(self):
        driver.get("http://localhost:5173/payment")
        
        # Click "Add Balance"
        add_btn = driver.find_element(By.ID, "add-balance-btn")
        add_btn.click()
        
        # Stripe popup appears
        stripe_frame = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.TAG_NAME, "iframe"))
        )
        driver.switch_to.frame(stripe_frame)
        
        # Enter test card (4242 4242 4242 4242)
        card_input = driver.find_element(By.NAME, "cardnumber")
        card_input.send_keys("4242424242424242")
        
        # Expire + CVC
        driver.find_element(By.NAME, "exp-date").send_keys("1225")
        driver.find_element(By.NAME, "cvc").send_keys("123")
        
        # Submit
        pay_btn = driver.find_element(By.ID, "stripe-pay")
        pay_btn.click()
        
        driver.switch_to.default_content()
        
        # Confirmation page
        confirmation = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "payment-success"))
        )
        assert "Balance Added" in confirmation.text
        
        # Moloni receipt link
        receipt_link = driver.find_element(By.ID, "moloni-receipt")
        assert receipt_link.get_attribute("href") is not None

    Timeout: 60s
    Uses Stripe test mode
```

---

## 4. Load Tests

### 100 Simultaneous PIN Attempts (Rate Limiting)
```python
# tests/load/test_rate_limiting.py
from locust import HttpUser, task, between

class PINAttackUser(HttpUser):
    wait_time = between(0.1, 0.5)
    
    @task
    def attempt_pin(self):
        # Simulate brute-force attempt
        response = self.client.post("/access/pin", json={
            "pin": "random",
            "device_id": "kp_abc123"
        })
        
        # After 3 attempts in 60s, expect 429 (rate limited)
        if response.status_code == 429:
            self.on_rate_limit()
    
    def on_rate_limit(self):
        # Confirm lockout
        response = self.client.post("/access/pin", json={
            "pin": "1234",  # valid PIN
            "device_id": "kp_abc123"
        })
        assert response.status_code == 423  # Locked

# Run: locust -f test_rate_limiting.py --users 100 --spawn-rate 10
# Expected: 100% rate-limited after 3 attempts each
```

### 1000 MQTT Messages/Sec Throughput
```bash
# tests/load/mqtt_throughput_test.sh
#!/bin/bash
# Publish 1000 msgs/sec for 60s = 60k messages total

for i in {1..60}; do
  for j in {1..1000}; do
    mosquitto_pub -h 127.0.0.1 -p 1883 \
      -t "jfa/tuya/device/relay_$((RANDOM % 10))/status" \
      -m "{\"status\": \"on\", \"seq\": $j}" &
  done
  echo "Batch $i: 1000 messages published"
  sleep 1
done

# Measure MQTT broker:
# - Message latency < 100ms
# - CPU usage < 30%
# - Dropped messages: 0
```

### Database Query Latency (RLS with 10 Tenants)
```python
# tests/load/test_rls_latency.py
import time
import concurrent.futures

def query_rls_performance():
    db = TestDatabase()
    
    # Create 10 test tenants
    for i in range(10):
        db.create_tenant(f"tenant_{i}")
    
    # Concurrent queries (100 queries, 10 tenants = 1000 rows)
    def query_devices(tenant_id):
        start = time.time()
        rows = db.execute_rls(
            "SELECT * FROM input_devices",
            user_id=f"user_{tenant_id}",
            tenant_id=tenant_id
        )
        latency = time.time() - start
        return latency
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        latencies = list(executor.map(query_devices, range(10)))
    
    # Assert: p95 latency < 50ms, p99 < 100ms
    latencies.sort()
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[int(len(latencies) * 0.99)]
    
    assert p95 < 0.05, f"P95 latency {p95}s > 50ms"
    assert p99 < 0.10, f"P99 latency {p99}s > 100ms"
```

---

## 5. Security Tests

### PIN Brute-Force Mitigation (3 Attempts → 60s Lockout)
```python
# tests/security/test_pin_bruteforce.py
class TestPINBruteForce(TestCase):
    def test_lockout_after_3_attempts(self):
        device_id = "kp_abc123"
        
        # Attempt 1
        self.api.post("/access/pin", json={"pin": "0000", "device_id": device_id})
        assert is_locked(device_id) == False
        
        # Attempt 2
        self.api.post("/access/pin", json={"pin": "1111", "device_id": device_id})
        assert is_locked(device_id) == False
        
        # Attempt 3 → LOCKED
        self.api.post("/access/pin", json={"pin": "2222", "device_id": device_id})
        assert is_locked(device_id) == True
        assert get_lockout_seconds(device_id) == 60
    
    def test_lockout_duration(self):
        device_id = "kp_abc123"
        set_locked(device_id, 60)
        
        # Try correct PIN while locked
        response = self.api.post("/access/pin", json={"pin": "1234", "device_id": device_id})
        assert response.status_code == 423  # Locked
        
        # Wait 60s
        time.sleep(61)
        
        # Now correct PIN works
        response = self.api.post("/access/pin", json={"pin": "1234", "device_id": device_id})
        assert response.status_code == 200
    
    def test_progressive_lockout(self):
        # Attempt 1: 3 min lockout
        # Attempt 2: 10 min lockout
        # Attempt 3: 30 min lockout
        # Pattern: exponential backoff
        
        device_id = "kp_abc123"
        lockout_durations = []
        
        for attempt in range(3):
            set_locked(device_id, 180 * (attempt + 1))
            lockout_durations.append(get_lockout_seconds(device_id))
        
        assert lockout_durations == [180, 360, 900]

    Coverage: Security-critical
```

### MQTT TLS Certificate Validation
```python
# tests/security/test_mqtt_tls.py
class TestMQTTTLS(TestCase):
    def test_self_signed_cert_rejected(self):
        # MQTT broker with self-signed cert
        mqtt = MockMQTTBroker(cert="selfsigned.pem")
        
        # Client rejects
        client = MQTTClient(host="127.0.0.1", verify_cert=True)
        assert client.connect() == False
    
    def test_expired_cert_rejected(self):
        mqtt = MockMQTTBroker(cert="expired.pem")
        
        client = MQTTClient(host="127.0.0.1", verify_cert=True)
        assert client.connect() == False
    
    def test_valid_cert_accepted(self):
        mqtt = MockMQTTBroker(cert="valid.pem")
        
        client = MQTTClient(host="127.0.0.1", verify_cert=True)
        assert client.connect() == True

    Coverage: TLS/SSL
```

### HMAC Signature Verification
```python
# tests/security/test_hmac_signature.py
class TestHMACSignature(TestCase):
    def test_valid_signature(self):
        message = "transfer:€5:user1:2026-05-26"
        secret = "sk_secret_123"
        
        signature = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
        assert verify_hmac(message, signature, secret) == True
    
    def test_invalid_signature_rejected(self):
        message = "transfer:€5:user1:2026-05-26"
        secret = "sk_secret_123"
        invalid_sig = "00000000000000000000000000000000"
        
        assert verify_hmac(message, invalid_sig, secret) == False
    
    def test_message_tampering_detected(self):
        message = "transfer:€5:user1:2026-05-26"
        secret = "sk_secret_123"
        signature = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
        
        # Tamper with amount
        tampered = "transfer:€50:user1:2026-05-26"
        assert verify_hmac(tampered, signature, secret) == False

    Coverage: Cryptography
```

### SQL Injection (Parameterized Queries)
```python
# tests/security/test_sql_injection.py
class TestSQLInjection(TestCase):
    def test_parameterized_query_safe(self):
        # Parameterized query with user input
        device_id = "kp_abc123'; DROP TABLE input_events; --"
        
        # Should treat as string, not execute DROP
        rows = db.query(
            "SELECT * FROM input_devices WHERE device_id = %s",
            (device_id,)
        )
        
        # Table still exists (attack failed)
        assert db.table_exists("input_devices") == True
        
        # Query returned 0 rows (no device with that literal ID)
        assert len(rows) == 0
    
    def test_string_concat_injection_vulnerable(self):
        # NEVER do this:
        device_id = "kp_abc123' OR '1'='1"
        query = f"SELECT * FROM input_devices WHERE device_id = '{device_id}'"
        
        # This WOULD return all rows (vulnerable!)
        # Confirm we DON'T do this in codebase
        assert "f\"" not in read_source_file("backend/api/db.py")

    Coverage: Security-critical
```

### CORS + CSRF Token Handling
```python
# tests/security/test_cors_csrf.py
class TestCORSCSRF(TestCase):
    def test_cors_origin_whitelisted(self):
        # Request from allowed origin
        response = self.client.post(
            "/access/pin",
            json={"pin": "1234"},
            headers={"Origin": "https://app.example.com"}
        )
        assert response.status_code == 200
    
    def test_cors_origin_blocked(self):
        # Request from unauthorized origin
        response = self.client.post(
            "/access/pin",
            json={"pin": "1234"},
            headers={"Origin": "https://evil.com"}
        )
        assert response.status_code == 403  # Forbidden
    
    def test_csrf_token_required(self):
        # POST without CSRF token
        response = self.client.post(
            "/access/pin",
            json={"pin": "1234"}
        )
        # Should fail if CSRF enabled
        assert response.status_code in [403, 422]

    Coverage: Web security
```

---

## 6. Compliance Tests

### RGPD: Card UID Anonimização (90d Auto-Delete)
```python
# tests/compliance/test_rgpd_anonymization.py
class TestRGPDAnonimization(TestCase):
    def test_card_uid_anonymization_90days(self):
        # Insert card UID with timestamp
        card_uid = "045ACD12"
        created_at = datetime.now() - timedelta(days=91)
        
        db.insert("input_events", {
            "card_uid": card_uid,
            "created_at": created_at,
            "access_result": "granted"
        })
        
        # Run anonymization job
        anonymize_old_events(days=90)
        
        # Card UID should be anonymized
        row = db.query("SELECT card_uid FROM input_events WHERE id = ?", (row_id,))
        assert row[0]["card_uid"] == "****CD12"  # Masked
    
    def test_recent_card_uid_retained(self):
        # Insert recent event
        card_uid = "045ACD12"
        created_at = datetime.now() - timedelta(days=30)
        
        db.insert("input_events", {
            "card_uid": card_uid,
            "created_at": created_at
        })
        
        anonymize_old_events(days=90)
        
        # Should be retained
        row = db.query("SELECT card_uid FROM input_events WHERE created_at = ?", (created_at,))
        assert row[0]["card_uid"] == "045ACD12"  # Not masked

    Coverage: RGPD compliance
```

### PCI-DSS: Stripe Tokenization (Never Store Full CC)
```python
# tests/compliance/test_pci_dss.py
class TestPCIDSS(TestCase):
    def test_no_credit_card_stored(self):
        # Scan database for credit card patterns
        rows = db.query("SELECT * FROM payment_methods")
        
        cc_pattern = r'\d{13,19}'
        for row in rows:
            for column in row:
                if isinstance(column, str):
                    assert not re.match(cc_pattern, column), \
                        "Credit card number found in database!"
    
    def test_stripe_token_stored_instead(self):
        # Payment stored as Stripe token (pm_xxx)
        payment = db.query("SELECT token FROM payment_methods LIMIT 1")
        assert payment[0]["token"].startswith("pm_")
    
    def test_payment_log_masked(self):
        # Log files should not contain CC numbers
        with open("logs/payment.log", "r") as f:
            content = f.read()
            assert not re.search(r'\d{13,19}', content), \
                "Credit card found in logs!"

    Coverage: PCI-DSS compliance
```

### SAF-T: Moloni Export XML Validation
```python
# tests/compliance/test_saft_validation.py
class TestSAFTValidation(TestCase):
    def test_moloni_export_valid_xml(self):
        # Generate SAF-T export
        export = moloni_client.export_saft()
        
        # Parse XML
        root = ET.fromstring(export)
        
        # Validate required elements
        assert root.find(".//CompanyID") is not None
        assert root.find(".//AuditFile/Header/CompanyName") is not None
        assert root.find(".//AuditFile/MasterFiles/Customer") is not None
    
    def test_saft_schema_compliance(self):
        # Validate against PT SAF-T schema
        export = moloni_client.export_saft()
        
        schema = ET.parse("schemas/saft_pt_schema.xsd")
        assert schema.getroot().validate(ET.fromstring(export)) == True
    
    def test_invoice_lineage_complete(self):
        # All invoices have continuous numbering
        root = ET.fromstring(moloni_client.export_saft())
        
        invoices = root.findall(".//Invoice")
        invoice_numbers = sorted([int(inv.find("InvoiceNo").text) for inv in invoices])
        
        # Check no gaps
        for i in range(len(invoice_numbers) - 1):
            assert invoice_numbers[i+1] == invoice_numbers[i] + 1

    Coverage: Tax compliance
```

### Audit Log Completeness (input_events Table)
```python
# tests/compliance/test_audit_log.py
class TestAuditLogCompleteness(TestCase):
    def test_all_access_logged(self):
        # Attempt access with valid PIN
        self.api.post("/access/pin", json={"pin": "1234", "device_id": "kp_abc123"})
        
        # Check input_events table
        events = db.query("SELECT * FROM input_events WHERE device_id = 'kp_abc123' ORDER BY created_at DESC LIMIT 1")
        
        assert len(events) == 1
        event = events[0]
        
        # Required fields
        assert event["device_id"] == "kp_abc123"
        assert event["access_result"] in ["granted", "denied"]
        assert event["pin_hash"] is not None  # Hashed PIN
        assert event["created_at"] is not None
        assert event["user_id"] is not None or event["tenant_id"] is not None
    
    def test_audit_log_immutable(self):
        # Audit logs should not be editable after creation
        event_id = 123
        
        # Try to update
        result = db.execute("UPDATE input_events SET access_result='granted' WHERE id=%s", (event_id,))
        
        # Should be blocked by trigger or RLS policy
        assert result.affected_rows == 0
    
    def test_audit_log_retention_policy(self):
        # Logs retained 2 years minimum
        created_at = datetime.now() - timedelta(days=730)
        
        # Insert event
        db.insert("input_events", {"created_at": created_at, ...})
        
        # Run retention job
        prune_old_events(days=730)
        
        # Event should still exist
        event = db.query("SELECT * FROM input_events WHERE created_at = ?", (created_at,))
        assert len(event) == 1

    Coverage: Audit & compliance
```

---

## Test Execution Strategy

### Phase 1 (Weeks 1-2): Unit + Integration
```bash
# Run tests for Tuya integration
pytest tests/unit/ tests/integration/test_tuya_mqtt_integration.py -v --cov=backend/api --cov-report=html

# Target: 85% coverage
```

### Phase 2 (Weeks 3-4): Add Card Reader Tests
```bash
pytest tests/unit/test_card_uid.py tests/e2e/test_card_reader_simulation.py -v
```

### Phase 3-5: Full Regression
```bash
pytest tests/ -v --cov --cov-report=html --cov-report=term-missing

# Pre-commit:
pytest tests/unit/ tests/integration/ -q
```

### Load & Security (Week 10)
```bash
locust -f tests/load/test_rate_limiting.py --users 100
pytest tests/security/ tests/compliance/ -v
```

---

## Coverage Targets by Phase

| Phase | Unit | Integration | E2E | Load | Security | Total |
|-------|------|-------------|-----|------|----------|-------|
| Phase 1 | 85% | 75% | 50% | — | 75% | 78% |
| Phase 2 | 90% | 80% | 70% | — | 80% | 80% |
| Phase 3 | 85% | 85% | 75% | — | 85% | 83% |
| Phase 4 | 85% | 90% | 85% | 50% | 95% | 85% |
| Phase 5 | 90% | 95% | 90% | 80% | 100% | **93%** |

**Final Target: 93% coverage (critical modules 95%+)**

---

**Documento versão:** 2026-05-26
**Próximo passo:** Runbooks Deploy + Scaling Matrix
