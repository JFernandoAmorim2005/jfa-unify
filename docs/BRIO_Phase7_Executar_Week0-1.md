# BRIO Fase 7 — EXECUTAR Week 0-1 (Fernando)

**Data Início:** 2026-05-27  
**Duração:** 10 dias trabalho (2 semanas calendário)  
**Owner:** Fernando Amorim (CTO/CEO)  
**Status:** EM EXECUÇÃO (Day 1-2) ✅

---

## 🚀 DAY 1 SUMMARY (2026-05-27)

✅ **T1 (GDPR DPA):** Emails enviados (Tuya legal + Legal advisor PT)  
✅ **T2 (Stock):** Email enviado (Gravid — stock confirmation)  
✅ **T3 (MQTT Abstraction):** Design completo (interface + adapters + schema)  
⏳ **Awaiting:** Day 2 respostas (Tuya template, Gravid stock confirm)  
⏳ **Ready for:** T4 blocking (schema lock pending Day 7 review)

---

## Visão Geral

Execução do **Week 0-1 Checklist** confirmado em Phase 5, com 5 trabalhos paralelos não-bloqueantes:

| Tarefa | Owner | Início | Fim | Duração | Crítico? |
|--------|-------|--------|-----|---------|----------|
| **T1** Tuya GDPR DPA | Legal/CFO | Day 1 | Day 3 | 1-2 dias | ✅ SIM |
| **T2** Stock Hub 6E | Operações | Day 1 | Day 2 | 1 dia | ✅ SIM |
| **T3** MQTT Abstraction Design | CTO/Product | Day 2-5 | Day 7 | 5 dias | ✅ SIM |
| **T4** Pilot Data Anon Setup | Backend | Day 3-5 | Day 5 | 2 dias | ⚠️ Bloqueado por T3 |
| **T5** Tuya Pricing Lock | CFO | Day 5-7 | Day 10 | 3 dias | ⚠️ Bloqueado por T2 |

**Caminho crítico:** T1 → T5 → MVP pronto (Day 10)

---

## Tarefa T1: Tuya GDPR DPA

**Owner:** Fernando + Legal (Consultor DPA)

### Day 1 — Contacto Tuya Legal & DPA Advisor

```
Ações:
□ Email para Tuya EMEA legal (gdpr-dpa@tuya.com)
  Assunto: "JFA_Unify — Tuya Hub 6E GDPR Data Processing Agreement"
  Body:
    - Company: JFA Unify (Madeira, Portugal)
    - Product: Tuya Hub 6E managed WiFi access control
    - Data categories: PIN hashes (HMAC-SHA256), card UIDs (JSONB), IP logs (INET)
    - Subprocessor: Tuya Cloud (EU data residency)
    - DPA scope: Tuya acts as Data Processor for JFA (Data Controller)
    - Timeline: Signature by Month 2 (2026-07-27) for revenue go-live
    - Pilot: May start with anonymized data (random UUIDs) until DPA signed

□ Contactar Legal Advisor GDPR (recomendado: Formigueiro & Associados, Madeira)
  - Discussão: GDPR implicações (Tuya como subprocessor, JFA como controller)
  - Contrato: DPA template Tuya + revisão PT-PT
  - Timeline: 2-3 dias para advogado rever

□ Criar Issue Linear "T1-GDPR-DPA-TUYA" (projeto INGEST)
  Labels: urgent, gdpr, compliance, t1
  Blocker: Week 0-1 MVP start
```

### Day 2-3 — Follow-up & Template Negotiation

```
Ações:
□ Receber DPA template Tuya
  - Rever data flows (cloud vs local fallover)
  - Check: EU Standard Contractual Clauses (SCCs) presentes?
  - Check: Sub-processor notification required?

□ Legal advisor rever template
  - Identif gaps (PT-GDPR + LGPD se Brasil fase later)
  - Suggest modificações (e.g., data deletion SLA post-pilot)
  - Timeline optimista: assinatura Week 2-3

□ Feedback para Tuya
  - Enviar redlined DPA template
  - Pedir turnaround 48h-72h
```

### Success Criteria ✅
- [ ] DPA assinado OU piloto iniciável com dados test (sem DPA 30 dias max)
- [ ] Tuya confirma EU data residency (Frankfurt AWS region)
- [ ] Legal clearance para proceder com pilot anonymizado

### Risk Mitigation
| Risk | Impacto | Mitigation |
|------|---------|-----------|
| Tuya DPA delay >1 mês | Revenue slip Month 3+ | Pilot com dados test (no real PII until signed) |
| Tuya nega SCCs | Go-live bloqueado | Escalate CRO Tuya; consider SaaS swap |
| Legal contesta compliance | Timeline slip | Pre-align legal antes contato Tuya |

---

## Tarefa T2: Stock Tuya Hub 6E Confirmation

**Owner:** Operations + Gravid (Distribuidor)

### Day 1 — Contacto Gravid

```
Ações:
□ Email para Gravid EMEA (sales@gravid.pt ou key account manager)
  Assunto: "JFA_Unify — Tuya Hub 6E Bulk Order — Stock Confirmation"
  Body:
    - SKU: Tuya Hub 6E (WiFi 6E, model THD-ZigBee-HUB-6E)
    - Quantidade: 100 units (Pilot) + 20 units (contingency) = 120 units
    - Timeline: 
      * 20 units Week 2-3 (dev + pilot setup)
      * 80 units Month 2 (pilot ramp)
      * Lead time aceitável: 2-4 weeks from PO
    - Preço locked? (vamos negociar em T5)
    - Payment terms: Net 30 / Net 60?

□ Perguntar alternativas se stock insuficiente
  - Backorder timeline (quando chega stock)?
  - Second-source vendors (Alibaba, AliExpress, distribuidor US)?
```

### Day 2 — Confirmação & Booking

```
Ações:
□ Receber confirmação stock de Gravid
  - Confirmar quantidade disponível
  - Confirmar ETA para Week 2-3 (20 units)
  - Confirmar ETA para Month 2 (80 units)

□ Colocar PO (Purchase Order) preliminar
  - Quantidade: 20 units (Week 2-3)
  - Condição: Stock hold 30 dias, cancellable no-penalty até Day 5

□ Criar Issue Linear "T2-STOCK-HUB6E"
  Labels: procurement, critical, t2
  Blocker: Day 5 confirmação final
```

### Success Criteria ✅
- [ ] 20 units Hub 6E confirmadas para Week 2-3
- [ ] 80 units Hub 6E confirmadas para Month 2
- [ ] Preço unit locked (para T5)
- [ ] ETA documentada em Gravid contract

### Risk Mitigation
| Risk | Impacto | Mitigation |
|------|---------|-----------|
| Stock insuficiente | Pilot delay | Second-source: Alibaba/distribuidor US (+1 semana) |
| Preço varia | Budget overage | Negociar volume discount T5 (120 units → 5-10% discount) |

---

## Tarefa T3: MQTT Abstraction Design

**Owner:** CTO (Fernando) + Product Lead

### Day 2-3 — Architecture Design Session

```
Ações:
□ Definir MQTT abstraction interface (interface genérica)
  
  Pseudocódigo:
  ```python
  # app/services/mqtt_base.py (ABSTRACT)
  class MqttBackend(ABC):
      @abstractmethod
      async def connect(self, config: MqttConfig) -> None:
          """Connect to MQTT broker."""
      
      @abstractmethod
      async def publish(self, topic: str, payload: dict, qos: int = 1) -> None:
          """Publish message to topic."""
      
      @abstractmethod
      async def subscribe(self, topic: str, callback: Callable) -> None:
          """Subscribe to topic pattern."""
      
      @abstractmethod
      async def disconnect(self) -> None:
          """Graceful disconnect."""
      
      @property
      @abstractmethod
      def is_connected(self) -> bool:
          """Health status."""
  
  # Implementations:
  # - TuyaMqttBackend(MqttBackend)  [Year 1-2]
  # - Esp32MqttBackend(MqttBackend) [Year 3+]
  ```

□ Definir topic naming convention (invariantes MQTT)
  
  ```
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
  ```

□ Definir failover strategy (local vs cloud)
  
  ```
  Diagrama:
  Device → [Tuya Hub local MQTT] ─── offline ─→ [Local SQLite fallback]
                  ↓ (online)
           [Tuya Cloud MQTT] → [JFA Backend]
  
  Timeout: 30s local → fallback SQLite
  Retry: exponential backoff (1s, 2s, 5s, 10s, stop)
  Sync: when online → batch upload from SQLite
  ```

□ Produto: Definir fase 2/3 triggers para ESP32-S3 swap
  - Trigger T1: >500 devices/month → ROI justifica NRE
  - Trigger T2: Tuya API breaking change → switch cost <€50k
  - Trigger T3: Margin compression (Tuya >15% royalty) → own HW savings
```

### Day 4-5 — Validation & Documentation

```
Ações:
□ Code review MQTT abstraction pattern
  - Check: dependency injection works (swappable)
  - Check: logging spans backend-agnostic
  - Check: tests cover both Tuya + mock backends

□ Criar pull request (draft)
  - Branch: feature/mqtt-abstraction-phase7
  - Files: app/services/mqtt_base.py, app/services/tuya_mqtt.py (refactor)
  - Tests: 8 tests covering abstract interface

□ Dokumentar migration path ESP32-S3
  - Document: /docs/MQTT_ABSTRACTION_DESIGN.md
  - Include: Tuya topic schema, failover diagram, swap checklist
```

### Day 6-7 — Approval & Merge

```
Ações:
□ Code review + approval (CTO self-review ✓)
□ Merge to main
□ Update CI/CD pipeline (if new dependencies)
□ Criar Issue Linear "T3-MQTT-ABSTRACTION-MERGED"
  Labels: architecture, completed, t3
```

### Success Criteria ✅
- [ ] MQTT interface abstração definida + documentada
- [ ] Topic naming invariantes locked (prod-safe)
- [ ] Failover strategy codificada (local fallback)
- [ ] Phase 2/3 swap triggers identified + documented
- [ ] Pull request merged to main
- [ ] Tests: 8/8 passing, coverage ≥95%

### Cost & Timeline
| Item | Cost | Timeline |
|------|------|----------|
| Design + implementation | €5.000 | 5 dias |
| Testing + validation | Included | 2 dias |
| **Total** | **€5.000** | **7 dias** |

**Parallelism:** Não bloqueante MVP (design ahead of implementation)

### Risk Mitigation
| Risk | Impacto | Mitigation |
|------|---------|-----------|
| Abstraction over-engineered | Slow MVP | MVP uses TuyaMqttBackend only (interface ready) |
| Topic schema changed later | Firmware flash required | Lock schema in Day 3 code review |

---

## Tarefa T4: Pilot Data Anonymization Setup

**Owner:** Backend Lead (+ T3 blocker)

### Prerequisite
- **Bloqueado por:** T3 MQTT design (topic schema deve estar locked)

### Day 4-5 — Anonymization Logic

```
Ações:
□ Implementar data anonymization layer
  
  Pseudocódigo:
  ```python
  # app/utils/anonymizer.py
  import uuid
  from datetime import datetime
  
  class PilotDataAnonymizer:
      @staticmethod
      def anonymize_pin(pin: str) -> str:
          """HMAC-SHA256 com random salt per tenant."""
          return hmac.new(
              key=PILOT_SALT.encode(),
              msg=pin.encode(),
              digestmod='sha256'
          ).hexdigest()
      
      @staticmethod
      def generate_test_device_id() -> str:
          """Generate UUID v4 for test device."""
          return str(uuid.uuid4())
      
      @staticmethod
      def generate_test_card_uid() -> str:
          """Generate random 7-byte UID (valid NFC format)."""
          return secrets.token_hex(7)
      
      @staticmethod
      def anonymize_ip(ip_str: str) -> str:
          """Mask IP to /24 subnet (GDPR compliant)."""
          parts = ip_str.split('.')
          return f"{parts[0]}.{parts[1]}.{parts[2]}.0"
  ```

□ Criar test data factory
  - 5 test tenants (test-org-1..5)
  - 20 test devices per tenant (100 total)
  - 50 test PINs + 50 test card UIDs
  - timestamp ranges: 2026-05-27 to 2026-06-30

□ Criar fixture dataset anonymization
  - Use: /tests/fixtures/pilot_data_anonymized.sql
  - Include: INSERT statements for all test data
  - Verify: No real PII (randomized)
```

### Day 5 — Validation & Documentation

```
Ações:
□ Testar anonymization layer
  - Test 1: PIN hashing determinístico (same input → same hash)
  - Test 2: Device ID única per test device
  - Test 3: IP masking removes last octet
  - Test 4: Card UID 7-byte format valid

□ Criar migrations Alembic
  - Migration: 004_load_pilot_test_data.py
  - Condição: IF environment = PILOT or TESTING
  - Rollback: DELETE WHERE created_at > 2026-05-27 AND tenant_id LIKE 'test-%'
```

### Success Criteria ✅
- [ ] Anonymizer module 100% tested (4 test cases)
- [ ] Test data factory gerada (100 devices, 2500 access logs)
- [ ] Migration reversível (rollback safe)
- [ ] Nenhuma PII real em fixture

### Cost & Timeline
| Item | Cost | Timeline |
|------|------|----------|
| Implementation | Included em MVP | 2 dias |
| Testing | Included | 1 dia |

### Risk Mitigation
| Risk | Impacto | Mitigation |
|------|---------|-----------|
| PII leaks to fixtures | GDPR violation | Code review all fixture data (no real emails/phones) |
| Anonymizer bug | Data corruption | Unit tests cover 100% paths |

---

## Tarefa T5: Tuya Pricing Lock Contract

**Owner:** CFO (Fernando) + Gravid account manager

### Prerequisite
- **Bloqueado por:** T2 stock confirmation (necessário para volume negotiation)

### Day 6-7 — Negotiation

```
Ações:
□ Email para Gravid sales (após T2 confirmação stock)
  Assunto: "JFA_Unify — Tuya Hub 6E Volume Pricing — 2-Year Lock"
  Body:
    - Volume: 120 units Year 1 + 200 units Year 2 (estimated) = 320 units
    - Request: 5-10% volume discount on unit price
    - Lock term: 2 years (2026-05-27 to 2028-05-27)
    - Price guarantee: Tuya price changes flagged 90 days advance notice
    - Payment: 30% deposit, 70% on delivery (per unit 20 at a time)
    - SLA: Lead time ≤4 weeks
    
    Budget impact:
    - Current: €58.320 / 100 units = €583/unit
    - Target: €583 × 90% = €525/unit (5% discount)
    - Savings: 320 units × (€583 - €525) = €18.560 (10% budget buffer)

□ Solicitar contrato formal (términos pagamento + SLA)
  - Terms: Net 30 payment after delivery
  - Garantia: 2-year fixed price (revisível Year 3)
  - Cancellation: No penalty até Day 10; after Day 10 = 10% cancellation fee

□ Financeiro: Coordenar payment authority
  - PO approval: Fernando (€30k deposit approved)
  - Budget tracking: Spreadsheet EUR/device vs baseline €583
```

### Day 8-10 — Contract Finalization

```
Ações:
□ Receber contrato draft de Gravid
  - Rever: Preço, SLA, payment terms, cancellation
  - Negoce: Desconto adicional se possible

□ Signature & archivo
  - Contrato signed (digital signature aceitável)
  - Arquivo: /docs/contracts/Gravid-Tuya-2YearPriceLock-2026.pdf

□ Criar PO formal
  - PO number: JFA-PO-001-2026
  - Quantity: 20 units (Week 2-3), 80 units (Month 2), 200 units (Year 2)
  - Payment: 30% deposit (€3.150) due 5 dias after PO

□ Issue Linear "T5-PRICING-LOCKED"
  Labels: finance, contracts, t5
  Status: CLOSED ✅
```

### Success Criteria ✅
- [ ] Contrato assinado 2-year price lock (€525/unit or better)
- [ ] SLA defined: ≤4 week lead time
- [ ] PO formal emitido (JFA-PO-001-2026)
- [ ] 30% deposit processado (€3.150)

### Cost & Timeline
| Item | Cost | Timeline |
|------|------|----------|
| Negociação | Time only | 2 dias |
| Contrato legal | ~€500 (advogado) | included in T1 legal |

### Risk Mitigation
| Risk | Impacto | Mitigation |
|------|---------|-----------|
| Gravid nega desconto | Orçamento tight | Increase contingency a €20k (já alocado) |
| Lead time >4 weeks | Pilot delay | Second-source Alibaba (+1 week) |

---

## Sumário Week 0-1

| Tarefa | Owner | Status | Data Fim | Blocker | Notes |
|--------|-------|--------|----------|---------|-------|
| T1 | Legal/CFO | INICIADO | 2026-05-29 | — | Paralelo |
| T2 | Operações | INICIADO | 2026-05-28 | — | Paralelo |
| T3 | CTO | INICIADO | 2026-06-02 | T1 starts | Não bloqueante MVP |
| T4 | Backend | PENDING | 2026-06-02 | T3 locked | Start Day 4 |
| T5 | CFO | PENDING | 2026-06-06 | T2 confirm | Start Day 6 |

**Caminho crítico:** T1 (Day 1-3) → Tuya DPA → Revenue release → T5 (Day 6-10) → Price locked → MVP Week 1-4 começável

**Paralelismo:** T1, T2 rodam simultaneamente (Day 1-2); T3 inicia Day 2 (não depende); T4, T5 dependem de T3, T2 respectivamente (start Day 4-6)

**Go/No-Go Criteria (Day 5 checkpoint):**
- ✅ T1: DPA process started (signature by Month 2 acceptable)
- ✅ T2: Stock confirmado para Week 2-3
- ✅ T3: MQTT abstraction merged to main
- ⚠️ T4: Anonymization ready to integrate
- ⚠️ T5: Pricing negotiation initiated

**MVP Ready:** Day 10 (2026-06-06)
- FastAPI backend (Phase 6 ✅)
- SvelteKit frontend (Phase 6 ✅)
- MQTT abstraction tested (T3 ✅)
- Pilot data anonymized (T4 ✅)
- Budget locked (T5 ✅)
- DPA process initiated (T1 ✅)

---

## Next Phase: Week 1-4 MVP Scaffold

**Phase 6 IMPLEMENTAR (scaffold)** + **Phase 7 EXECUTAR (Week 0-1 ops)** → **Phase 8 VALIDAÇÃO**

**Week 1-4 MVP Deliverables:**
1. Tuya Hub 6E local MQTT broker tested (local fallover works)
2. PIN pad component (2-3 vendors validated)
3. NFC/RFID reader PN532 integration (SPI protocol)
4. Card UID storage + validation logic
5. Access log aggregation + audit trail
6. Pilot data ingestion (anonymized)

**Go-live criteria:** 
- PIN access + Card access both ≥99% success rate
- MQTT failover tested (broker down → local SQLite sync)
- Pilot locations ready (contact + training)

---

**Versão:** 1.0  
**Última actualização:** 2026-05-26 (Fernando, CTO)  
**Próximo checkpoint:** 2026-05-31 (Day 5, Go/No-Go decision)
