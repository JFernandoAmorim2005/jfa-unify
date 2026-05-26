# BRIO Fase 5 — Decisões Confirmadas (Fernando)

**Data:** 2026-05-26  
**Aprovação:** Fernando Amorim  
**Status:** CONFIRMADO ✅ Pronto para Phase 6 IMPLEMENTAR

---

## Decisões Confirmadas

### DP1: Pilot com dados test vs atraso DPA
**Escolha:** Opção A ✅
- Pilot Month 1-2 com dados anonimizados/test
- Revenue real inicia após DPA assinado (Month 2-3)
- Minimiza atraso ao mercado

### DP2: MQTT abstraction Week 1?
**Escolha:** Opção A ✅
- Design MQTT abstraction obrigatório Week 1
- +€5.000 investment, +3 dias paralelos (não bloqueante)
- Payoff: €20-30.000 poupados se Phase 3 (ESP32-S3) activada

### DP3: Budget Variante C?
**Escolha:** Opção B ✅
- Alocar: €58.320 (Tuya MVP Y1-2) + €20.000 (contingency)
- **NÃO reservar** €120.000 ESP32-S3 agora
- Decisão Phase 3 no Review Point 2 (Month 12) com dados reais
- Cash flow Year 1 (€326.208 cumulativo) suporta ambos cenários em Year 2

---

## Implicações para Phase 6

✅ **Week 0-1 Checklist actualizado:**
- Iniciar Tuya GDPR DPA processo (Day 1)
- Confirmar stock Tuya Hub 6E com Gravid
- **MQTT abstraction design** obrigatório (CTO + Product design, +€5k paralelo)
- Pilot data anonymization setup (usar random UUIDs até DPA)
- Contrato pricing lock Tuya (CFO)

✅ **Timeline MVP mantém 4 semanas** (MQTT abstraction paralelo, não bloqueante)

✅ **Budget Y1:** €58.320 approved, contingency €20.000 reserved

✅ **Variante C hedge:** Monitorizado com 5 triggers quantitativos (T1-T5), Review Point 2 Month 12

---

**Próximo:** Phase 6 IMPLEMENTAR — FastAPI scaffolding, Docker Compose, PostgreSQL RLS, SvelteKit PIN pad component
