# Venda Cruzada: JFA_Unify + JFA_Suite Integration

## The Pitch (30 sec elevator)

**When:** During Madeira demos or Top-5 QBR meetings

**Opening:** "I want to show you something new we're doing — connecting JFA_Unify with JFA_Suite."

## The Problem

Right now, Madeira clients have:
- JFA_Unify for access control (devices, logs, security)
- Manual spreadsheets or JFA_Suite for billing (separate system)

**Two systems = manual reconciliation, data silos, confusion.**

## The Solution: One Dashboard

- All your JFA products in one place
- Billing tied to actual device usage (auto-billing by # of doors/cameras)
- Analytics showing ROI of access control investment
- Single invoice per month (no confusion)

## The Ask

**Price:** EUR 300/month add-on (includes Suite + priority support + quarterly reviews)

**ROI Pitch:** "You're investing in access control. Suite integration helps you prove ROI to stakeholders — how much did it save vs security staff?"

## Implementation (Engineering)

### Phase 1 (Jul 2026)
- API endpoint in JFA_Unify: `POST /api/v1/suite/sync`
- Exports: device list, usage stats, monthly active devices

### Phase 2 (Aug 2026)
- JFA_Suite webhook: receives data from JFA_Unify
- Auto-billing rules: EUR X per device/month

### Phase 3 (Sep 2026)
- Dashboard: unified view (JFA_Unify + Suite in one UI)

---

## Objection Handlers

| Objection | Response |
|-----------|----------|
| "We're happy with separate systems" | "So was our last client. After integration, they reduced admin time 20% and caught a billing error that cost them EUR 5k." |
| "Is it hard to implement?" | "2 hours of setup. We handle everything. 1 Zoom call, done." |
| "What if we stop using Suite?" | "You can disconnect anytime. No lock-in. But most clients keep it — it pays for itself in time savings." |
| "How much extra?" | "EUR 300/month, includes priority support. First 3 months 50% off if you sign this month." |

---

## Sales Script (5 min conversation)

**Setup:** You're in QBR or demo, they ask about billing.

**You:** "Right now you're managing access control separately from billing. What if everything was in one place?"

**Them:** "Interesting, but we're fine with our current setup..."

**You:** "I get it. Here's what happened with Hotel X: they integrated, and within a month they spotted a billing error — actually owed them EUR 5k that slipped through the cracks. And their admin team went from 2 hours/month on reconciliation to zero."

**Them:** "Okay, I'm interested..."

**You:** "Great. It's EUR 300/month — includes the integration + priority support. If you decide this month, first 3 months are EUR 150. And if you don't like it, disconnect anytime."

**Them:** "Let me think about it..."

**You:** "Perfect. I'll send you a proposal by email. Fair enough?"

---

## Email Follow-up Template

Subject: JFA_Unify + JFA_Suite Integration Proposal

Hi [Client],

Following up on our discussion — here's the integration proposal:

**What you get:**
- Unified dashboard (access control + billing in one place)
- Auto-billing based on device usage
- Priority support (2h response time)
- Quarterly business reviews

**Cost:** EUR 300/month (includes Suite license)

**Offer (this month only):** First 3 months at EUR 150/month

**Next steps:** Sign SLA amendment, we handle the setup (2 hours). Live in 1 week.

Interested? Let me know!

Cheers,
Fernando
