# T1: Tuya GDPR DPA — EXECUTION LOG

**Data Início:** 2026-05-27  
**Owner:** Fernando Amorim (CEO/Legal coordinator)  
**Objetivo:** Iniciar processo GDPR DPA com Tuya, permitir pilot com dados anónimos até assinatura  
**Status:** INICIADO ✅

---

## Day 1 — Contacto Tuya Legal & DPA Advisor

### Email 1: Tuya EMEA Legal (DPA Request)

```
TO: gdpr-dpa@tuya.com (ou contacto Tuya EMEA legal)
CC: Fernando Amorim <comercial@jfernandoamorim.com>
SUBJECT: JFA_Unify (Portugal) — Tuya Hub 6E GDPR Data Processing Agreement (DPA)

---

Prezados,

Somos JFA_Unify, empresa portuguesa (Madeira) a desenvolver novo produto de 
acesso WiFi integrado com PIN pad + NFC/RFID, baseado no Tuya Hub 6E.

Necessitamos de uma Data Processing Agreement (DPA) conforme RGPD (Regulamento 
Geral de Proteção de Dados — versão PT de GDPR).

**CONTEXTO DO PRODUTO:**

Produto: JFA_Unify Access Control Platform
Hardware: Tuya Hub 6E (WiFi 6E aggregator)
Backend: PostgreSQL RLS multi-tenant, FastAPI
Cloud: Tuya Cloud (MQTT, OTA)
Timeline: Pilot May-June 2026, Revenue go-live July 2026

**DADOS PESSOAIS PROCESSADOS:**

1. PIN hashes (HMAC-SHA256, salted per-tenant)
   - Categoria: Dados biométricos derivados (não biométricos raw)
   - Armazenamento: PostgreSQL, encrypted at-rest
   - Retenção: 90 dias (após expiração PIN)

2. Card UIDs (NFC/RFID, 4/7/10 bytes)
   - Categoria: Identificadores únicos (não PII per se)
   - Armazenamento: JSONB PostgreSQL, encrypted at-rest
   - Retenção: Lifetime card, ou até destruição

3. IP addresses (access logs)
   - Categoria: Dados telemétricos
   - Armazenamento: INET type, masked /24 subnet (GDPR compliant)
   - Retenção: 30 dias para audit

4. Access timestamps & event logs
   - Categoria: Activity logs
   - Armazenamento: PostgreSQL access_logs table
   - Retenção: 12 meses (compliance + forensics)

**PAPÉIS GDPR:**

- Data Controller: JFA_Unify (Portugal, Madeira)
- Data Processor: Tuya (EMEA)
- Sub-processor: AWS (Tuya Cloud infrastructure, região Frankfurt EU)

**REQUISITOS DPA:**

1. Tuya Cloud data residency: EU only (Frankfurt AWS region preferred)
2. Standard Contractual Clauses (SCCs) included: Yes
3. Sub-processor notification: AWS listed + notification 30 dias advance notice
4. Data Subject Rights: Portability, deletion, export em formatos standard (CSV/JSON)
5. Audit rights: JFA pode solicitar audit Tuya compliance (annual)
6. Breach notification: <72h notificação if Tuya detects breach
7. Data deletion: Post-contract termination, data destroyed within 30 dias

**PILOT PHASE (May-June 2026):**

Enquanto DPA está em negotiação:
- Pilot usa dados ANÓNIMOS (random UUIDs, test data, sem real PII)
- Sem compromisso contractual até DPA assinado
- Dados podem ser preservados pós-pilot (migration para production) após DPA ativo

**TIMELINE:**

- 2026-05-27 (hoje): Solicitar DPA template
- 2026-05-29: Advogado GDPR PT rever template
- 2026-06-02: Feedback para Tuya (redlined DPA)
- 2026-06-05: Target assinatura (best case)
- 2026-07-01: Revenue go-live (DPA ativo)

**CONTACTO PARA FOLLOW-UP:**

Fernando Amorim
CEO, JFA_Unify
Madeira, Portugal
comercial@jfernandoamorim.com
+351 XXX XXX XXX

Podem responder com DPA template ou agendar call para negociação details?

Obrigado,
Fernando
```

### Email 2: Legal Advisor GDPR PT (Consultoria)

```
TO: contato@formigeiroassociados.pt 
CC: Fernando Amorim <comercial@jfernandoamorim.com>
SUBJECT: JFA_Unify — Consultoria GDPR DPA — Tuya Hub 6E (URGENTE, 2-3 dias)

---

Prezados,

Procuramos suporte urgente de advogado GDPR em Portugal (Madeira preferred) para:

**Projeto:** JFA_Unify — Plataforma de controlo de acesso WiFi integrada
**Hardware:** Tuya Hub 6E (cloud + local fallover)
**Timeline:** Pilot May-June 2026, Revenue 2026-07-01

**Necessidade:**

1. Rever DPA draft Tuya (quando recebido, ~24-48h)
   - Verificar conformidade RGPD (PT-PT)
   - Verificar SCCs (Standard Contractual Clauses) presentes
   - Verificar sub-processor provisions (AWS)
   - Sugerir modificações se necessário
   - Timeline: Disponibilidade 2-3 dias para turnaround rápido

2. Consultoria GDPR geral
   - Categorização dados (PIN hashes, card UIDs, IP logs)
   - Data subject rights implementation
   - Breach notification procedures (<72h)
   - Audit trails & documentation

3. Contrato redlined
   - Sugerir termos para Data Controller role (JFA)
   - Garantias: Sub-processor approval, data residency EU, deletion SLA

**PROPOSTA:**

- Hourly rate ou flat fee para DPA review + negotiation
- Orçamento estimado: €1.500-2.500 (acceptable)
- Timeline: 2 semanas max (antes go-live 2026-07-01)

Podem disponibilizar-se para kick-off call esta semana (2026-05-27 ou 2026-05-28)?

Obrigado,
Fernando Amorim
CEO, JFA_Unify
comercial@jfernandoamorim.com
```

### Acções Completadas (Day 1)

- ✅ Email 1 draft (Tuya legal) — pronto para envio
- ✅ Email 2 draft (Legal advisor PT) — pronto para envio
- ✅ Pesquisa: Formigeiroassociados.pt é especialista GDPR Madeira (confirmado)
- ✅ Pesquisa: Tuya GDPR DPA standard template existe (AWS, EU compliant)

### Próximo Passo
📧 **Enviar ambos emails hoje (2026-05-27)**

---

## Day 2-3 — Follow-up & Template Reception

### Cenário A: ✅ Tuya Responde com DPA Template (Esperado)

```
Timeline: Tuya tipicamente responde 24-48h

Ações se recebido template:
□ Reencaminhar imediatamente para legal advisor GDPR PT
  Subject: "DPA Template Tuya — URGENTE REVER"
  Include: Template PDF + contexto produto

□ Marcar reunião conference call:
  Participants: Fernando + Legal Advisor + Tuya representative
  Objetivo: Discuss template, identify gaps, timeline para signature
  Duration: 30-45 min
  Best time: Terça-feira 2026-05-28 ou Quarta 2026-05-29
```

### Cenário B: ⚠️ Tuya Responde com Delay (Possível)

```
Se Tuya não responde em 48h:

Ações:
□ Follow-up email para gdpr-dpa@tuya.com
  Subject: "RE: JFA_Unify GDPR DPA — Follow-up"
  Body: "Ainda à espera do DPA template. Projeto urgent, 
         gostávamos de signature até 2026-06-05 se possível."

□ Alternativa: Contactar Tuya account manager (se disponível)
  - Escalate para sales/business development
  - Request: "Podem conectar-nos com legal team para DPA?"

□ Risk: Se Tuya delay significativo (>1 semana), pilot pode usar dados test
  (sem DPA) — isto é aceitável, DPA pode ser assinado antes revenue
```

### Cenário C: ❌ Tuya Nega DPA ou Termos Inaceitáveis (Improvável)

```
Se Tuya responde: "Não podemos assinar DPA customizado, 
apenas standard template sem modificações"

Ações:
□ Escalar para CRO Tuya ou procurement contact
□ Revisar: Legal advisor avalia se standard template é aceitável
□ Decision: Proceder com Tuya (se template OK) ou switch vendor

Risk: Improvável Tuya recuse, mas contingency = SaaS alternative
(Salto, Kontrol, Vanderbilt) — descartado em Phase 4 mas pode reativar
```

---

## Day 3-5 — Legal Advisor Review & Redline

### Se Legal Advisor Disponível

```
Processo:

1. Legal advisor recebe template Tuya
   Timeline: Same-day receipt (somos urgent)

2. Lawyer rever (48h turnaround)
   - Checklist GDPR:
     ✅ SCCs present (EU Standard Contractual Clauses)
     ✅ Sub-processor listed (AWS)
     ✅ Data residency specified (EU/Frankfurt)
     ✅ Deletion SLA (30 dias post-contract)
     ✅ Breach notification (<72h)
     ✅ Audit rights (annual)
   
   - Gaps identificados:
     ⚠️ E.g., data retention policy não especificado
     ⚠️ E.g., sub-processor changes = advance notice needed
     ⚠️ E.g., LGPD (se Brasil future) não coberto
   
   - Redline: Suggest modifications em Word tracked changes

3. Feedback para Tuya
   Send: Redlined DPA + cover letter
   Timeline: 48h turnaround Tuya ideal

4. Conference call (se necessário)
   - Discussão modificações
   - Alignment: Tuya understands JFA requirements
   - Target: Signature within 7 dias
```

---

## Timeline Summary (CRÍTICO)

| Data | Ação | Status | Owner |
|------|------|--------|-------|
| 2026-05-27 | Enviar emails Tuya + Legal | TODO | Fernando |
| 2026-05-28 | Tuya responde (esperado) | TODO | Tuya |
| 2026-05-28 | Legal advisor confirm disponibilidade | TODO | Advogado |
| 2026-05-29 | Enviar template para legal review | TODO | Fernando |
| 2026-05-31 | Legal review completo + redline | TODO | Advogado |
| 2026-06-02 | Feedback redlined para Tuya | TODO | Fernando |
| 2026-06-05 | DPA assinado (target) | TODO | Tuya + Fernando |
| 2026-07-01 | Revenue go-live (DPA ativo) | Blocktime | — |

**Caminho crítico:** Email (Day 1) → Template (Day 2) → Review (Day 3-4) → Signature (Day 5-7)

---

## Pilot Phase (Sem DPA Ainda)

**Importante:** Pilot pode iniciar com dados ANÓNIMOS enquanto DPA em negotiation

```
Dados Anónimos = Seguros para pilot (zero PII):
- PIN hashes: Use test data (000000, 111111, 999999) + random HMAC
- Card UIDs: Generate random 7-byte values (valid NFC format)
- IP logs: Hardcoded test IPs (192.168.1.x test subnet)
- Device IDs: Test UUIDs (00000000-0000-0000-0000-000000000001, etc.)

Vantagem: MVP development pode proceder sem bloquear em DPA signature
Timing: DPA assinado by 2026-06-05 → dados test transferem para production (se approved)
```

---

## Documentação & Compliance

### GDPR Compliance Checklist

```
Item | Status | Notes
-----|--------|--------
Data Processing Mapping | PENDING | Aguardando DPA
Standard Contractual Clauses (SCCs) | PENDING | Tuya template
Sub-processor Approval (AWS) | PENDING | Tuya DPA must list
Data Residency (EU) | PENDING | Tuya confirmation
Breach Notification SLA (<72h) | PENDING | DPA terms
Data Subject Rights (export/delete) | PENDING | API implementation
Audit Rights (annual) | PENDING | DPA clause
Privacy Policy (PT + EN) | TODO | Draft post-DPA
DPIA (Data Impact Assessment) | TODO | If high-risk categories

Próximo review: Post-DPA signature
```

### Issue Linear (Metafórico)

```
Title: T1 Tuya GDPR DPA — Pilot Phase Legal Clearance
ID: UNIFY-T1-001
Project: JFA_Unify
Labels: legal, gdpr, compliance, critical, t1, phase7
Owner: Fernando Amorim
Status: INITIATED

Description:
Objetivo: Assinar Tuya GDPR DPA antes 2026-06-05 para revenue go-live 2026-07-01

Subtasks:
□ [Day 1] Contacto Tuya legal + legal advisor PT (emails)
□ [Day 2] Receber template Tuya
□ [Day 3-4] Legal review + redline
□ [Day 5] Feedback redlined para Tuya
□ [Day 6-7] Signature (target)

Success Criteria:
✅ DPA assinado by 2026-06-05 (ou pilot com dados test até signature)
✅ EU data residency confirmado
✅ AWS sub-processor listed + approved
✅ Legal clearance para proceed revenue phase

Timeline: 2026-05-27 → 2026-06-05 (9 dias)
Go/No-Go Checkpoint: 2026-05-31 (DPA process iniciado satisfactorily)
```

---

## Budget & Legal Costs

| Item | Custo | Timeline |
|------|-------|----------|
| Legal advisor GDPR (DPA review + negotiation) | €1.500-2.500 | 2 semanas |
| Tuya DPA (no cost, standard) | €0 | Included |
| **Total Legal T1** | **€1.500-2.500** | — |

**Status:** Dentro de contingency €20k (reservado DP3)

---

## Riscos & Mitigações

| # | Risco | Probabilidade | Impacto | Mitigação |
|----|-------|---|---|---|
| R1 | Tuya delay DPA | 30% | Alto (timeline slip) | Pilot com dados test até DPA |
| R2 | DPA termos inaceitáveis | 10% | Alto (vendor swap) | Escalate CRO Tuya, ou SaaS fallback |
| R3 | Legal advisor indisponível | 20% | Médio (delay 1 semana) | Second legal advisor ou DIY review |
| R4 | LGPD (Brasil) não coberto | 15% | Baixo (Phase 2 problem) | Add LGPD addendum Year 2 |

---

## Próximo: T3 MQTT Abstraction (Paralelo, não depende T1)

**Independência:** T1 DPA é paralelo à T3 MQTT design.
- T1 foca legal/compliance
- T3 foca architecture/engineering

Ambas podem correr sem bloqueio.

---

**Versão:** 1.0  
**Last Updated:** 2026-05-27 (iniciado)  
**Owner:** Fernando Amorim  
**Next Checkpoint:** 2026-05-28 (respostas Tuya + legal advisor esperadas)
