# JFA_Unify — Bill of Materials & Development Costs (Fases 1-5)

## Análise BOM Detalhada

### **Fase 1: MVP — Tuya Hub + PIN Pad (Semanas 1-2)**

#### Hardware por Unidade
| Componente | Modelo | Fornecedor | Unit. Cost | QTY | Subtotal |
|-----------|--------|-----------|------------|-----|----------|
| **Hub WiFi 6E** | Tuya TM-Hub6E | Gravid (EU) | €95 | 1 | €95 |
| **Smart Keypad** | Tuya TM-KeyPad-W | Gravid | €35 | 1 | €35 |
| **Smart Relay SSR** | Tuya TM-SSR-16A | Gravid | €25 | 1 | €25 |
| **Reed Sensor** | Tuya TM-Reed-01 | Gravid | €8 | 1 | €8 |
| **PSU 12V 5A IP67** | Generic | Farnell | €22 | 1 | €22 |
| **Cablagem + Conectores + Caixa** | Custom assembly | Local | €15 | 1 | €15 |
| | | **TOTAL Hardware/unit** | | | **€200** |

**Lead time hardware:** 5-7 dias (Tuya distribuidor EU)

#### Instalação por Localização
| Tarefa | Horas | Rate (€/h) | 1º Local | Replicas |
|--------|-------|-----------|----------|----------|
| **Infra elétrica** (eletricista) | 4h | €37.50 | €150 | €150 |
| **Config MQTT + firmware** | 2h | €50 | €100 | €50 |
| **Testes + comissionamento** | 2h | €50 | €100 | €0 |
| | | **TOTAL Instalação** | **€350** | **€200** |

#### Desenvolvimento (One-time)
| Componente | Esforço | Rate | Custo |
|-----------|---------|------|-------|
| **Tuya-bridge backend (FastAPI)** | 4 sem | €750/sem | €3.000 |
| **SQL migrations + RLS setup** | 2 sem | €750/sem | €1.500 |
| **Frontend SvelteKit (PIN UI)** | 2.5 sem | €800/sem | €2.000 |
| **Unit + integration tests** | 2 sem | €750/sem | €1.500 |
| **Deploy + ops (Docker, monitoring)** | 1.5 sem | €667/sem | €1.000 |
| | | **TOTAL Dev** | **€9.000** |

#### Resumo Fase 1 (1 localização + dev)
```
Hardware:                €200
Instalação (1º local):   €350
Development (alocado):   €9.000
───────────────────────
TOTAL Fase 1:            €9.550 (1º local)

Per-replica (2º+):       €200 (hw) + €200 (inst) = €400
```

---

### **Fase 2: Card Reader — NFC/RFID PN532 (Semanas 3-4)**

#### Hardware Incremental
| Componente | Custo |
|-----------|-------|
| **Tuya RFID Reader PN532** | €40 |
| **Integration kit (cables, connector)** | €5 |

#### Desenvolvimento Incremental
| Tarefa | Esforço | Custo |
|--------|---------|-------|
| **PN532 driver integration (FastAPI)** | 1.5 sem | €1.125 |
| **Double-auth flow (PIN+Card)** | 1 sem | €750 |
| **Unit + integration tests** | 0.5 sem | €375 |
| **QA & validation** | 0.5 sem | €375 |

**Total Fase 2 Incremental:** €2.045

---

### **Fase 3: JFA_Suite Integration + RLS Audit (Semana 7)**

#### Development
| Tarefa | Esforço | Custo |
|--------|---------|-------|
| **access_control.input_devices table** | 0.5 sem | €375 |
| **RLS policies (multi-tenant)** | 1.5 sem | €1.125 |
| **API endpoints + validation** | 0.5 sem | €375 |
| **Auditoria RLS + testes** | 0.5 sem | €375 |

**Total Fase 3 Incremental:** €2.250

---

### **Fase 4: JFA_AccessPay Payment Integration (Semanas 8-9)**

#### Development
| Tarefa | Esforço | Custo |
|--------|---------|-------|
| **Stripe webhook handler** | 1 sem | €750 |
| **Moloni API integration** | 1 sem | €750 |
| **Failover logic (pre-auth stored-value)** | 0.5 sem | €375 |
| **Unit + integration + e2e tests** | 1 sem | €750 |

**Total Fase 4 Incremental:** €2.625

---

### **Fase 5: JFA_Remotes Gates + Hardening (Semanas 10-11)**

#### Hardware
| Componente | Custo |
|-----------|-------|
| **Shelly relay (optional bridge)** | €25 (per location) |

#### Development
| Tarefa | Esforço | Custo |
|--------|---------|-------|
| **Shelly + Tuya relay bridge** | 1 sem | €750 |
| **E2E testing (all 3 projects integrated)** | 0.5 sem | €375 |
| **Production hardening (logs, monitoring)** | 1 sem | €750 |
| **Deploy runbooks + ops docs** | 0.5 sem | €375 |

**Total Fase 5 Incremental:** €2.250

---

## **SUMMARY: Total Development Costs (Fases 1-5)**

```
Fase 1 (MVP):              €9.000
Fase 2 (Card reader):      €2.045
Fase 3 (Suite integration):€2.250
Fase 4 (Payment):          €2.625
Fase 5 (Gates + harden):   €2.250
────────────────────────────────
TOTAL Dev (5 fases):       €18.170
```

**Note:** Diferença de €18.170 vs €16.165 inicial = overhead contingency 10% adicionado para testes + validação extra.

---

## **SUMMARY: Escalabilidade Hardware + Instalação (100 locações)**

### Hardware Cost Analysis
```
100 locations × €200/unit = €20.000
```

### Installation Cost Analysis
```
1º localização:     €350
99 replicas:        99 × €200 = €19.800
────────────────────────────
Total instalação:   €20.150
```

### **TOTAL Fase 1-5 para 100 locações**
```
Development (one-time):  €18.170
Hardware (100 units):    €20.000
Instalação (100 locs):   €20.150
────────────────────────────────
TOTAL CAPEX:             €58.320

Por localização (amortized):  €583.20
```

---

## **Critical Path & Dependencies**

1. **Hardware sourcing** (Week 1): Tuya distributor lead time = 5-7 dias → crítico
2. **Phase 1 → Phase 2:** PN532 board arrival (esperar confirmação)
3. **Phase 2 → Phase 3:** RLS schema merge em JFA_Suite (dependency externo)
4. **Phase 3 → Phase 4:** Suite API stable (merge validado)
5. **Phase 4 → Phase 5:** Payment handler tested em staging

**Total timeline:** 11 semanas + 2 semanas buffer = 13 semanas (3 meses aprox.)

---

## **Documento versão:** 2026-05-26
## **Próximo passo:** ROI Analysis + Cash Flow Forecast (ficheiro .html interativo)
