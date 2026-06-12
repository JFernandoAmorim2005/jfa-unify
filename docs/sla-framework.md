# SLA Framework — JFA Unify (Top-Tier Clients)

## Service Level Commitments

### Availability
- **Target:** 99.9% uptime (max 43 min/month)
- **Measurement:** API health checks (MQTT broker, FastAPI, PostgreSQL)
- **Monitoring:** Prometheus + AlertManager (live status page)

### Support Response
- **Critical Issue:** <2 hours (phone + email)
- **High:** <4 hours (email)
- **Medium:** <24 hours (email)
- **Low:** <48 hours (email)

**Critical** = "access control system down" (physical security impact)
**High** = "intermittent access failures" (user can't access)
**Medium** = "feature request" / "performance question"
**Low** = "documentation" / "general inquiry"

### Quarterly Business Review
- **Frequency:** Every 90 days
- **Attendees:** Fernando Amorim + Client contact + (optional) CTO
- **Agenda:**
  1. Uptime report (actual vs 99.9% target)
  2. Support ticket review (response times met? quality?)
  3. Feature usage analytics (ROI of JFA_Unify)
  4. Roadmap preview + upsell opportunity (JFA_Suite integration, ESP32 hardware, etc.)
  5. Renewal + expansion discussion

### Credits for SLA Breaches
- 1% uptime miss = 5% monthly credit
- 5% uptime miss = 15% monthly credit
- Support response miss = 2% monthly credit per incident

Example: If uptime = 99.1% (0.8% below target), client gets 5% discount next month.

## Implementation for NIF 511099177 + Top 4

**If recovery successful:**
- Sign SLA addendum (amendment to existing contract)
- Enable monitoring + status page
- Schedule first QBR for Jul 15

**If recovery negotiation ongoing:**
- Offer SLA as sweetener ("Plus dedicated support if you come back")
- Build trust via transparent uptime

**Template Email to Send:**

Subject: SLA Upgrade — 99.9% Uptime Guarantee + Quarterly Business Reviews

Hi [Contact],

As part of our commitment to [company name], I'm proposing an upgraded SLA that gives you:

✓ 99.9% uptime guarantee (max 43 min/month downtime)
✓ 2-hour critical support response
✓ Quarterly business reviews (show ROI, discuss roadmap)
✓ Uptime credits if we miss targets

This is standard for enterprise customers. Attached is the SLA framework — let me know if you'd like any adjustments.

Goal: Make you feel like a priority client.

Cheers,
Fernando
