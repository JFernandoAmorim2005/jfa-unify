# T2: Stock Tuya Hub 6E Confirmation — EXECUTION LOG

**Data Início:** 2026-05-27  
**Owner:** Fernando Amorim  
**Objetivo:** Confirmar stock 20 units Week 2-3 + 80 units Month 2  
**Status:** INICIADO ✅

---

## Day 1 — Contacto Gravid EMEA

### Email Draft (Pronto para envio)

```
TO: sales@gravid.pt (ou account manager Tuya)
CC: Fernando Amorim <comercial@jfernandoamorim.com>
SUBJECT: JFA_Unify — Tuya Hub 6E Bulk Order — Stock Confirmation (120 units Y1)

---

Prezados,

Somos JFA_Unify, novo produto integrador de acesso WiFi + PIN pad + NFC/RFID 
desenvolvido em Madeira (Portugal).

Gostávamos de confirmar disponibilidade do seguinte:

**PRODUTO & QUANTIDADE:**
- SKU: Tuya Hub 6E (WiFi 6E, model THD-ZigBee-HUB-6E)
- Total Year 1: 120 units
  * Pilot & Development: 20 units (URGENTE — Week 2-3 de Maio)
  * Pilot Ramp: 80 units (June 2026)
  * Contingency: 20 units (backup, flexible)

**TIMELINE & LOGISTICS:**
- Lead time aceitável: 2-4 semanas a partir de PO
- Delivery flexibility: Podemos aceitar parcial shipments
- Incoterms: CIF Madeira ou ex-works (flexível)

**QUESTÕES:**
1. Têm stock disponível de 20 units para Week 2-3 de Junho? [2026-06-10 deadline]
2. ETA para os restantes 80 units (idealmente antes 2026-07-01)?
3. Qual é o preço unit actual (para negociação volume discount later)?
4. Condições pagamento (Net 30, Net 60, depósito?)?
5. Qual é o ponto de contacto para volume lock 2-year pricing?

**CONTEXT:**
Este é um projecto critical path para JFA_Unify. Antecipamos 300+ units em Year 2 
se pilot bem-sucedido. Portanto, temos interesse em estabelecer parceria 
long-term com pricing competitivo.

Podem responder por email ou agendar call para Thursday/Friday (2026-05-30/31)?

Obrigado,

Fernando Amorim
CTO/CEO, JFA_Unify
Madeira, Portugal
comercial@jfernandoamorim.com
+351 XXX XXX XXX [contact number]
```

### Acções Completadas

- ✅ Email draft pronto
- ✅ Detalhes técnicos verified (THD-ZigBee-HUB-6E é modelo correcto)
- ✅ Timeline realista (Week 2-3 Junho = 1.5 semanas, aceitável)

### Próximo Passo
📧 **Enviar email para Gravid hoje (2026-05-27)**

---

## Day 2 — Follow-up & Booking

### Cenários Possíveis

#### Cenário A: ✅ Stock Confirmado (Esperado)
```
Se Gravid responde: "Temos 20 units Week 2-3 e 80 units Month 2"

Ações:
□ Solicitar confirmação escrita (email ou quote)
□ Colocar PO preliminar:
  
  JFA_Unify — PRELIMINARY PO (Tuya Hub 6E)
  ──────────────────────────────────────────
  Date: 2026-05-27
  Vendor: Gravid (EMEA)
  PO Status: CONDITIONAL (stock hold 30 dias)
  
  Line Item 1:
  - Product: Tuya Hub 6E (WiFi 6E)
  - Quantity: 20 units
  - Unit Price: TBD (negociar T5)
  - Total: €11.660 (calculado 583€/unit)
  - Delivery: Week 2-3 June 2026 (2026-06-10 max)
  - Incoterms: CIF Madeira (ou ex-works)
  
  Line Item 2:
  - Product: Tuya Hub 6E (WiFi 6E)
  - Quantity: 80 units
  - Unit Price: TBD (negociar T5)
  - Total: €46.640
  - Delivery: Month 2 (2026-07-01 target)
  - Incoterms: CIF Madeira
  
  Payment Terms:
  - 30% deposit upon order (€17.388)
  - 70% on delivery (€40.912)
  - Net 30 after delivery
  
  Conditions:
  - PO cancellable no-penalty até 2026-05-31 (Day 5)
  - Stock hold: 30 dias (até 2026-06-27)
  - Lead time: Máximo 4 semanas (SLA requirement)
  - Garantia: Standard 2-year manufacturer

□ Enviar PO para Gravid (confirmação stock = autorização para processar)
□ Coordenar com CFO (Fernando) pagamento 30% deposit (€17.388)
```

#### Cenário B: ⚠️ Stock Parcial
```
Se Gravid responde: "Temos 15 units Week 2-3, 80 units Month 2"

Ações:
□ Solicitar alternativas:
  - Backorder timeline (quando chega stock missing 5 units?)
  - Second-source distribuidor? (Alibaba, AliExpress, US)
  - Preço diferente se ordem parcial?

□ Decision point:
  - If backorder <1 semana → accept
  - If backorder >1 semana → second-source 5 units Alibaba (+1-2 semanas)
```

#### Cenário C: ❌ Stock Insuficiente
```
Se Gravid responde: "Apenas 10 units disponível, lead time 6 semanas"

Ações:
□ Escalar para segundo distribuidor (Plan B):
  - Alibaba Tuya Hub 6E vendors (pesquisa)
  - AliExpress Tuya Hub 6E (mais rápido, +10-15% preço)
  - Outra distribuidor EU (Mouser, RS, Arrow)

□ Risk mitigation:
  - Ordem 20 units Alibaba (3-4 semanas) + 10 units Gravid (6 semanas) = 20 units na hora
  
□ Cost impact:
  - Alibaba preço 10-15% mais alto
  - Impacto orçamento: +€1.200-1.800 (aceitável, dentro contingency €20k)
```

---

## Check-in Points

### Day 2 Morning (2026-05-28)
```
Esperado: Resposta Gravid (24h turnaround)
- [ ] Confirmação stock (yes/no/partial)
- [ ] ETA detalhado
- [ ] Preço unit indicativo
- [ ] Payment terms
```

### Day 2-3 Afternoon
```
Ação: Processar resposta
- [ ] Enviar PO preliminar (se stock OK)
- [ ] Ou contactar segundo distribuidor (se stock problema)
- [ ] Atualizar timeline Phase 7
```

### Day 4 (Check-in T2 Final Status)
```
Esperado: PO confirmado ou segundo distribuidor secured
- [ ] T2 Status: COMPLETED ✅ (stock confirmado, PO emitido)
- [ ] Budget impact: €11.660 (20 units) + €46.640 (80 units) = €58.300 (within budget)
```

---

## Documentação & Rastreamento

### Issue Linear (Metafórico — para rastreamento)
```
Title: T2 Stock Tuya Hub 6E — 120 units Year 1
ID: UNIFY-T2-001
Project: JFA_Unify
Labels: procurement, critical, t2, phase7
Owner: Fernando Amorim
Status: INITIATED

Description:
- Objetivo: Confirmar stock 20 units Week 2-3 + 80 units Month 2
- Blocker: MVP Phase 6 implementation requires hardware
- Success Criteria:
  ✅ 20 units confirmadas para 2026-06-10
  ✅ 80 units confirmadas para 2026-07-01
  ✅ Preço unit locked (para T5)
  ✅ PO emitido e deposit (€17.388) processado

Subtasks:
□ [Day 1] Email Gravid stock confirmation
□ [Day 2] Receber resposta & PO decision
□ [Day 3] PO emitido, 30% deposit processado
□ [Day 4] T2 status = COMPLETED

Timeline: 2026-05-27 → 2026-05-30
Deadline: 2026-05-31 (Go/No-Go checkpoint)
```

### Arquivo Contrato/PO
```
Estrutura ficheiros:
C:\JFA_Unify\docs\
├── contracts/
│   └── Gravid-Tuya-PO-001-2026.pdf (a ser preenchido)
├── procurement/
│   ├── T2_STOCK_EXECUTION.md (este ficheiro)
│   ├── Gravid-Quote-2026.pdf (a receber)
│   └── PO-JFA-001-2026.docx (draft)
└── invoices/
    └── (a ser preenchido após delivery)
```

---

## Timeline Summary

| Data | Ação | Status |
|------|------|--------|
| 2026-05-27 | Enviar email Gravid | TODO |
| 2026-05-28 | Receber resposta (esperado) | TODO |
| 2026-05-28 | Processar PO preliminar | TODO |
| 2026-05-29 | 30% deposit processado | TODO |
| 2026-05-30 | Confirmação final Gravid | TODO |
| 2026-05-31 | T2 Status = COMPLETED ✅ | TODO |
| 2026-06-10 | Delivery 20 units | Blocktime |
| 2026-07-01 | Delivery 80 units | Blocktime |

---

## Budget Impact

| Item | Custo Unit | Quantidade | Subtotal | Timeline |
|------|-----------|-----------|----------|----------|
| Tuya Hub 6E (20 units) | €583 | 20 | €11.660 | Week 2-3 |
| Tuya Hub 6E (80 units) | €583 | 80 | €46.640 | Month 2 |
| **Total Y1** | — | 100 | **€58.300** | — |
| Contingency | — | — | €20.000 | (reservado) |
| **Budget Total** | — | — | **€78.300** | — |

**Status:** Within approved budget ✅ (Decision Point 3 — DP3 escolha B)

---

## Riscos & Mitigações

| # | Risco | Probabilidade | Impacto | Mitigação |
|----|-------|---|---|---|
| R1 | Stock insuficiente Gravid | 20% | Alto (timeline slip) | Second-source Alibaba (+1 semana) |
| R2 | Preço varia | 30% | Médio (orçamento +5-10%) | Negociar T5 volume discount (lock 2 anos) |
| R3 | Delivery delay >2 semanas | 15% | Alto (MVP delay) | Second-source ou express shipping |
| R4 | Hub 6E firmware incompatível | 5% | Baixo (firmware update) | Testar firmware na primeira entrega |

---

## Próximo: T5 Pricing Lock

Após T2 confirmado (Day 2-3), proximamente **T5** contactará Gravid 
com proposta de volume discount 2-year lock (€525/unit target, 10% desconto).

**Dependência:** T2 confirmação é input para T5 negociação.

---

**Versão:** 1.0  
**Last Updated:** 2026-05-27 (iniciado)  
**Owner:** Fernando Amorim  
**Next Checkpoint:** 2026-05-28 (resposta Gravid esperada)
