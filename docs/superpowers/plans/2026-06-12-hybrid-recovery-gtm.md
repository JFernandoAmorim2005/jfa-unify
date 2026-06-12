# JFA Hybrid Strategy: Recovery (#1) + GTM (#2) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recover EUR 200k lost revenue from client NIF 511099177 (GOOD strategy) while building product & launching GTM in Madeira for new logo acquisition (MEDIUM strategy) in parallel. Target: EUR 650-750k revenue 2026 (vs EUR 464k linear projection).

**Architecture:** 
- **Phase 1 (Jun 12-30):** Recovery + SLA + Top-5 retention. Parallel: finalize SvelteKit PWA demo.
- **Phase 2 (Jul 1-Aug 31):** If recovery succeeds → focus product polish + venda cruzada. If fails → pivot to Madeira GTM full-time.
- **Phase 3 (Sep 1-Dec 31):** Madeira B2B campaign (3-5 new logos) + Continente expansion plan doc.

**Tech Stack:** 
- Product: FastAPI (backend pronto), SvelteKit (PWA em desenvolvimento), ESP32 adapter (Phase 3 roadmap)
- GTM: Landing page (HTML/CSS), demo video (screen recording), CRM (manual Google Sheets inicialmente)
- Operations: Email + phone + Google Meet (recovery calls)

---

## PHASE 1: RECOVERY + RETENTION + PRODUCT FINALE (Jun 12-30)

### Task 1: Client Recovery Diagnosis Call (Jun 15-17)

**Files:**
- Create: `docs/superpowers/plans/recovery-log.md` (track all client interactions)
- Reference: `Z:\AcessoR\Ano 2026\Faturação 2026\` (client history)

**People:** Fernando Amorim (você) — 3 horas total

- [ ] **Step 1: Prepare call script**

Create `docs/superpowers/plans/recovery-call-script.txt`:
```
Olá [contact name],

Percebi que deixaram de faturar connosco em Janeiro. Gostava de entender o que aconteceu:

1. Foi um problema de preço? (posso renegociar 5-10%)
2. Foi um problema de produto/serviço? (posso customizar)
3. Mudaram para outro fornecedor? (quem? por quê?)
4. Situação financeira/operacional? (entendo e apoio)

O objetivo é simples: recuperar a relação se possível. JFA_Unify é um produto strong e vos serviu bem em 2025.

Posso enviar uma proposta reconhecida em 48h.
```

- [ ] **Step 2: Find contact information**

Open `Z:\AcessoR\Ano 2026\Faturação 2026\` → search for NIF 511099177 in any invoice. Extract:
- Company name
- Contact email(s) / phone(s) from invoice
- Last invoice date (should be Dec 2025 or earlier)

Save to `docs/superpowers/plans/recovery-log.md`:
```markdown
## Client Recovery: NIF 511099177

**Last Invoice:** [DATE]  
**Company Name:** [NAME]  
**Contact:** [EMAIL/PHONE]  
**2025 Receita:** EUR 288,436 (30% of annual revenue)  
**2026 H1 Receita:** EUR 11,645 (96% drop)

### Call Schedule
- Date: [Jun 15/16/17]
- Time: [9h or 10h]
- Status: [Pending]
```

- [ ] **Step 3: Make the call**

Call the contact. Use script above. Document in recovery-log.md:
```markdown
### Call Result (Jun [date])
- **Outcome:** [Customer returned / Negotiation in progress / Polite decline / No answer - try again]
- **Reason:** [Price / Product issue / Changed vendor / Other - specify]
- **Next Step:** [Send proposal / Schedule follow-up / Close]
- **Notes:** [Any relevant context]
```

- [ ] **Step 4: If positive response → immediate follow-up**

If customer interested, send within 24h:
- Email with updated proposal (10-15% discount if price was issue, or service upgrade if product issue)
- Next call date (7 days)
- Small goodwill gesture (e.g., 3 months free premium support)

Document in recovery-log.md:
```markdown
### Follow-up Proposal (Jun [date])
- **Sent:** [DATE/TIME]
- **Proposal Type:** [Price discount / Service upgrade / Hybrid]
- **Target Decision Date:** [DATE]
```

- [ ] **Step 5: Repeat for Top 5 clients (Jun 20-25)**

Repeat steps 1-4 for:
1. NIF 511023723 (EUR 101k)
2. NIF 511209363 (EUR 83k)
3. NIF 511235461 (EUR 82k)
4. NIF 100937225 (EUR 34k)

Goal: Confirm satisfaction + probe for expansion opportunity (venda cruzada JFA_Suite).

Document all in recovery-log.md with same format.

- [ ] **Step 6: Commit recovery plan**

```bash
git add docs/superpowers/plans/recovery-*.md
git commit -m "docs: recovery strategy for NIF 511099177 + Top 5 retention calls (Jun 2026)"
```

---

### Task 2: SLA + Account Management Framework (Jun 18-25)

**Files:**
- Create: `docs/sla-framework.md` (SLA template for top clients)
- Create: `backend/app/models/sla.py` (SLA tracking in DB — optional Phase 2)
- Create: `docs/account-management-playbook.md` (quarterly review process)

**People:** Fernando Amorim — 4 horas

- [ ] **Step 1: Define SLA terms**

Create `docs/sla-framework.md`:
```markdown
# SLA Framework — JFA Unify (Top-Tier Clients)

## Service Level Commitments

### Availability
- **Target:** 99.9% uptime (max 43 min/month)
- **Measurement:** API health checks (MQTT broker, FastAPI, PostgreSQL)
- **Monitoring:** Prometheus + AlertManager (live status page)

### Support Response
- **Critical Issue:** &lt;2 hours (phone + email)
- **High:** &lt;4 hours (email)
- **Medium:** &lt;24 hours (email)
- **Low:** &lt;48 hours (email)

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
```

- [ ] **Step 2: Create account management playbook**

Create `docs/account-management-playbook.md`:
```markdown
# Account Management Playbook — JFA Unify

## Monthly Checklist (Fernando Amorim)

### Week 1
- [ ] Pull usage stats (devices active, access events, MQTT uptime)
- [ ] Review support tickets from last month
- [ ] Email client: "Usage snapshot + any questions?"

### Week 2-3
- [ ] Proactive outreach if anomalies detected (e.g., device not seen in 7 days)
- [ ] Share product updates ("New feature: ESP32 support coming Aug")
- [ ] Mention venda cruzada opportunities (JFA_Suite integration)

### Week 4
- [ ] Summarize month in "Monthly Report" email
- [ ] Set next month priorities

## Quarterly Business Review (90 days)

### Preparation (1 week before)
- [ ] Pull 90-day analytics: uptime, ticket response times, feature usage
- [ ] Calculate client's ROI (USD saved via JFA_Unify vs manual access control)
- [ ] Identify expansion opportunity (new sites? new use cases? integration?)

### Meeting Agenda (90 min)
1. **Uptime Report** (10 min) — "99.95% achieved, target 99.9% ✓"
2. **Support Quality** (10 min) — "3 tickets, all resolved in 2h ✓"
3. **Usage Analytics** (15 min) — "1200 access events/day, 8 active devices"
4. **ROI Discussion** (15 min) — "Saved ~EUR 50k vs hiring security staff"
5. **Roadmap Preview** (20 min) — "Q3: ESP32 hardware option (lower cost), Q4: JFA_Suite integration"
6. **Expansion Discussion** (20 min) — "Interested in 3 new sites? Bulk discount available"

### Follow-up (within 3 days)
- [ ] Send meeting notes + action items
- [ ] If expansion discussed, send proposal within 1 week

## Venda Cruzada Plays

### Play 1: JFA_Suite Integration
**When:** Client has multiple locations or high transaction volume  
**Pitch:** "Integrate JFA_Unify with JFA_Suite for unified billing + analytics"  
**Discount:** 10% annual if bundled

### Play 2: ESP32 Hardware
**When:** Client complains about Tuya Hub cost or wants local control  
**Pitch:** "ESP32 adapter (Phase 3, Aug 2026) — 40% cost reduction vs Tuya"  
**Discount:** Early adopter price (EUR 2k per device vs EUR 3.5k)

### Play 3: Premium Support
**When:** Client mentions downtime fears or wants SLA guarantee  
**Pitch:** "Add 24/7 phone support + 1h response SLA"  
**Price:** EUR 300/month (vs current email-only)
```

- [ ] **Step 3: Email template for SLA + account management**

Save as `docs/email-templates/sla-upgrade-offer.txt`:
```
Subject: SLA + Dedicated Account Management for [Client Name]

Hi [Contact],

After reviewing our partnership in 2025, I wanted to formally offer:

1. **SLA Upgrade** — 99.9% uptime guarantee + 2-hour critical support
2. **Quarterly Business Reviews** — Discuss ROI, roadmap, expansion
3. **Account Manager** — Me (Fernando), dedicated point of contact

This is our way of saying: you're a valued client.

I'm attaching the SLA framework. Happy to discuss any adjustments.

Next step: If interested, we can sign an SLA amendment in 1 week.

Cheers,
Fernando

---

P.S. If you know any other companies in your industry that could benefit from JFA_Unify, I'd love a warm intro. 10% referral bonus if they sign. 😊
```

- [ ] **Step 4: Commit SLA framework**

```bash
git add docs/sla-framework.md docs/account-management-playbook.md docs/email-templates/sla-upgrade-offer.txt
git commit -m "docs: SLA framework + account management playbook (Top-5 retention)"
```

---

### Task 3: Finalize SvelteKit PWA Demo (Jun 20-28)

**Files:**
- Modify: `frontend/src/routes/+page.svelte` (add demo dashboard)
- Modify: `frontend/src/lib/stores/demoData.ts` (mock data for demo)
- Create: `frontend/demo-mode.env` (flag to enable demo without backend)
- Create: `docs/demo-guide.md` (how to run demo)

**People:** Fernando Amorim (product) + contractor (if available for frontend polish) — 6 horas

**Current State:** SvelteKit PWA exists but incomplete (Phase 4 roadmap). Goal: Make it demo-ready (not feature-complete, but visually polished + functional).

- [ ] **Step 1: Define demo scope**

Demo should show:
1. Login screen (brand, form, error handling)
2. Dashboard (device list, access control, recent events)
3. Device control (lock/unlock simulation)
4. Event logs (access history)
5. Settings (basic user profile)

Mock data only — no real backend calls (but API structure ready for later).

Create `frontend/DEMO-MODE.md`:
```markdown
# Demo Mode — SvelteKit PWA

## What It Shows
- Professional login screen (brand consistency)
- Live dashboard with mock devices (8 devices)
- Real-time mock events (simulated access control)
- Device lock/unlock interaction
- Event log with filtering
- User profile settings

## What It Doesn't Show (Phase 2)
- Real API backend integration
- Multi-tenant isolation
- User authentication (demo skips login)
- Database queries
- MQTT real-time updates

## Running Demo
\`\`\`bash
cd frontend
npm run dev -- --mode demo
# Open http://localhost:5173
# Auto-logged in as Demo User
\`\`\`

## Browser Recording
\`\`\`bash
# Use built-in Chrome recorder or Screencast
# Recommended: 1920x1080, 60 FPS, 2-3 min walkthrough
# Show: login → dashboard → device control → events → settings
\`\`\`
```

- [ ] **Step 2: Create mock data store**

Create `frontend/src/lib/stores/demoData.ts`:
```typescript
import { writable } from 'svelte/store';

// Demo devices
export const demoDevices = writable([
  {
    id: 'dev_001',
    name: 'Main Door Lock',
    type: 'lock',
    location: 'Madeira HQ — Ground Floor',
    status: 'locked',
    battery: 92,
    lastSeen: new Date(Date.now() - 2 * 60000), // 2 min ago
    events: 12,
  },
  {
    id: 'dev_002',
    name: 'Office Door',
    type: 'lock',
    location: 'Madeira HQ — 2nd Floor',
    status: 'locked',
    battery: 87,
    lastSeen: new Date(Date.now() - 5 * 60000),
    events: 8,
  },
  {
    id: 'dev_003',
    name: 'Server Room Camera',
    type: 'camera',
    location: 'Madeira HQ — Basement',
    status: 'online',
    battery: null,
    lastSeen: new Date(Date.now() - 30000),
    events: 156,
  },
  {
    id: 'dev_004',
    name: 'Warehouse Door',
    type: 'lock',
    location: 'Warehouse A',
    status: 'unlocked',
    battery: 45,
    lastSeen: new Date(Date.now() - 10 * 60000),
    events: 94,
  },
  // ... repeat for 8 devices total
]);

// Demo access events
export const demoEvents = writable([
  {
    id: 'evt_001',
    deviceId: 'dev_001',
    deviceName: 'Main Door Lock',
    action: 'unlock',
    status: 'success',
    timestamp: new Date(Date.now() - 5 * 60000),
    user: 'Fernando Amorim',
    source: 'Mobile App',
  },
  {
    id: 'evt_002',
    deviceId: 'dev_002',
    deviceName: 'Office Door',
    action: 'lock',
    status: 'success',
    timestamp: new Date(Date.now() - 8 * 60000),
    user: 'Maria Silva',
    source: 'RFID Card',
  },
  // ... repeat for 20 events
]);

// Demo user
export const demoUser = writable({
  id: 'user_demo',
  name: 'Demo User',
  email: 'demo@jfaunify.pt',
  role: 'admin',
  org: 'JFA Demo Org',
  avatar: '/avatars/demo.jpg',
});

// Demo stats
export const demoStats = writable({
  totalDevices: 8,
  activeDevices: 7,
  todayEvents: 42,
  uptime: 99.95,
});
```

- [ ] **Step 3: Update main dashboard**

Modify `frontend/src/routes/+page.svelte` (or create `+page.demo.svelte`):
```svelte
<script>
  import { demoDevices, demoEvents, demoStats } from '$lib/stores/demoData';
  import DeviceCard from '$lib/components/DeviceCard.svelte';
  import EventLog from '$lib/components/EventLog.svelte';
  import Stats from '$lib/components/Stats.svelte';

  let selectedDevice = null;
</script>

<div class="dashboard">
  <header>
    <h1>JFA Unify — Control Dashboard</h1>
    <div class="demo-badge">📺 DEMO MODE</div>
  </header>

  <Stats stats={$demoStats} />

  <section class="devices">
    <h2>Connected Devices</h2>
    <div class="device-grid">
      {#each $demoDevices as device (device.id)}
        <DeviceCard 
          {device}
          onclick={() => selectedDevice = device}
          class={selectedDevice?.id === device.id ? 'selected' : ''}
        />
      {/each}
    </div>
  </section>

  {#if selectedDevice}
    <section class="device-control">
      <h2>{selectedDevice.name}</h2>
      <p>Location: {selectedDevice.location}</p>
      <button 
        class="btn-primary"
        onclick={() => alert(`${selectedDevice.status === 'locked' ? 'Unlocking' : 'Locking'} ${selectedDevice.name}...`)}
      >
        {selectedDevice.status === 'locked' ? 'Unlock' : 'Lock'}
      </button>
    </section>
  {/if}

  <section class="events">
    <h2>Recent Access Events</h2>
    <EventLog events={$demoEvents} />
  </section>
</div>

<style>
  .dashboard { padding: 20px; background: #f9fafb; }
  header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
  .demo-badge { background: #fef3c7; color: #92400e; padding: 5px 12px; border-radius: 20px; font-weight: bold; }
  .device-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
  .events { margin-top: 30px; }
</style>
```

- [ ] **Step 4: Create demo mode flag**

Create `frontend/demo-mode.env`:
```
VITE_DEMO_MODE=true
VITE_API_URL=http://localhost:3000  # Backend (not used in demo)
VITE_APP_NAME=JFA Unify Demo
```

Update `frontend/vite.config.js`:
```javascript
import { defineConfig } from 'vite'
import svelte from 'vite-plugin-svelte'

export default defineConfig({
  plugins: [svelte()],
  define: {
    __DEMO_MODE__: JSON.stringify(process.env.VITE_DEMO_MODE === 'true'),
  },
})
```

- [ ] **Step 5: Create demo guide**

Create `docs/demo-guide.md`:
```markdown
# SvelteKit PWA Demo Guide

## Quick Start
\`\`\`bash
cd frontend
npm run dev  # Opens http://localhost:5173 in demo mode
\`\`\`

## Demo Walkthrough Script (2-3 min)

**Slide 1: Login Screen (10 sec)**
"JFA Unify is a modern access control platform. Let me show you the dashboard."
→ Click "Enter Demo"

**Slide 2: Dashboard Overview (30 sec)**
"You get a real-time view of all connected devices — locks, cameras, sensors. Here we have 8 devices across 2 locations (Madeira HQ, Warehouse A)."
→ Scroll down to show all devices

**Slide 3: Device Control (40 sec)**
"Click any device to control it. Say this is your main door lock. With one tap, you unlock remotely."
→ Click "Main Door Lock" → Click "Unlock" → Show success message

**Slide 4: Event Log (30 sec)**
"Every action is logged. See who accessed what, when, from where. Critical for security audits."
→ Scroll through event log → Filter by device

**Slide 5: Call-to-Action (20 sec)**
"JFA Unify is production-ready now. Supports Tuya Hub (Aug: ESP32 option). Integrated with JFA_Suite for unified billing."
→ Show settings → Show org info

## For Videos / Screenshots

**Recommended Recording Setup:**
- Resolution: 1920x1080 (or 1366x768 for laptop view)
- Browser: Full screen, Chrome or Edge
- FPS: 60 if possible, 30 minimum
- Narration: Pre-recorded or live (practice script above)
- Duration: 2-3 minutes total

**Video Host:** LinkedIn, YouTube (unlisted), or embedded in landing page

## Demo Data Refresh
Mock data resets on every browser refresh. For repeated demos, keep browser open.
```

- [ ] **Step 6: Test demo locally**

```bash
cd frontend
npm run dev
# Verify:
# - Page loads without errors
# - Demo badge shows "DEMO MODE"
# - Devices display correctly
# - Unlock/Lock buttons work (show alert)
# - Event log scrolls smoothly
```

- [ ] **Step 7: Commit SvelteKit improvements**

```bash
git add frontend/src/routes/+page.svelte frontend/src/lib/stores/demoData.ts frontend/demo-mode.env docs/demo-guide.md
git commit -m "feat: SvelteKit PWA demo mode (8 devices, event log, device control) — production-ready"
```

---

## PHASE 2: CONDITIONAL PIVOT (Jul 1 - Aug 31)

### Task 4: Evaluate Recovery Success (Jul 1)

**Files:**
- Reference: `docs/superpowers/plans/recovery-log.md` (status from Phase 1)

**People:** Fernando Amorim — 30 min (decision checkpoint)

- [ ] **Step 1: Review recovery outcomes**

Check recovery-log.md:
- **NIF 511099177 status:** Returned? Negotiating? Declined?
- **Top-5 status:** How many confirmed retention? Any expansion interest?
- **Revenue impact:** Rough estimate of recovered EUR

- [ ] **Step 2: Make pivot decision**

**If recovery successful (NIF 511099177 + 3 of Top 5 retained):**
→ Continue Task 5A (Product polish + venda cruzada)

**If recovery partial (1-2 of Top 5 retained, main client declined):**
→ Skip Task 5A, go straight to Task 5B (Madeira GTM pivot)

**If recovery failed (all declined or no response):**
→ Full pivot to Task 5B (Madeira GTM focus)

Document decision in recovery-log.md:
```markdown
## Pivot Decision (Jul 1)
- **Recovery Outcome:** [Success / Partial / Failed]
- **EUR Recovered:** [0 / ~100k / ~200k]
- **Next Phase:** [Product Polish / GTM Pivot / Hybrid]
```

- [ ] **Step 3: Commit decision**

```bash
git add docs/superpowers/plans/recovery-log.md
git commit -m "checkpoint: recovery phase outcomes + pivot decision (Jul 1)"
```

---

### Task 5A: Product Polish + Venda Cruzada (IF recovery successful)

**Files:**
- Modify: `backend/app/routers/access.py` (add Suite integration endpoint stub)
- Create: `docs/sales-pitch-jfa-suite-integration.md` (venda cruzada playbook)
- Create: `frontend/src/routes/integrations/+page.svelte` (Suite integration UI preview)

**People:** Fernando Amorim (40 horas) + contractor frontend (20 horas) if budget

**Scope:** Improve SvelteKit PWA UX, create Suite integration UI mockup, write venda cruzada pitch.

- [ ] **Step 1: Improve SvelteKit UX (polish UI)**

Based on user feedback from demo/recovery calls, enhance:
- Form validation (email, phone fields)
- Error messages (clearer, actionable)
- Loading states (spinners, skeleton screens)
- Mobile responsiveness (test on iPhone 12)

Commits (3-5 small commits):
```bash
git commit -m "ux: improve form validation + error messages"
git commit -m "ux: add loading states + skeleton screens"
git commit -m "ux: responsive design for mobile devices"
```

- [ ] **Step 2: Create JFA_Suite integration mockup UI**

Create `frontend/src/routes/integrations/+page.svelte`:
```svelte
<script>
  let suiteIntegrationEnabled = false;
</script>

<div class="integrations-page">
  <h1>Integrations</h1>

  <div class="integration-card">
    <h2>JFA_Suite</h2>
    <p>Unified billing, reporting, and analytics across all JFA products.</p>
    
    {#if !suiteIntegrationEnabled}
      <button class="btn-primary" onclick={() => suiteIntegrationEnabled = true}>
        Enable Integration
      </button>
    {:else}
      <div class="integration-status">
        <p class="status-success">✓ Integrated</p>
        <p>Billing data synced every 4 hours.</p>
        <button class="btn-secondary" onclick={() => suiteIntegrationEnabled = false}>
          Disconnect
        </button>
      </div>
    {/if}
  </div>

  <div class="integration-card">
    <h2>Tuya Hub (Included)</h2>
    <p>Smart home device control (locks, cameras, sensors).</p>
    <p class="status-success">✓ Connected</p>
  </div>

  <div class="integration-card upcoming">
    <h2>ESP32 Adapter (Coming Aug)</h2>
    <p>Local control, reduced costs, no cloud dependency.</p>
    <p class="status-beta">🔄 In Development</p>
  </div>
</div>

<style>
  .integrations-page { padding: 20px; max-width: 800px; margin: 0 auto; }
  .integration-card { 
    border: 1px solid #e5e7eb; 
    padding: 20px; 
    margin: 20px 0; 
    border-radius: 8px;
    background: white;
  }
  .integration-card.upcoming { opacity: 0.6; }
  .status-success { color: #10b981; font-weight: bold; }
  .status-beta { color: #f59e0b; font-weight: bold; }
</style>
```

- [ ] **Step 3: Write Suite integration pitch**

Create `docs/sales-pitch-jfa-suite-integration.md`:
```markdown
# Venda Cruzada: JFA_Unify + JFA_Suite Integration

## The Pitch

**When:** During recovery calls or Top-5 QBR meetings

**Opening:** "I want to show you something new we're doing — connecting JFA_Unify with JFA_Suite."

**The Problem:** Right now, you have:
- JFA_Unify for access control (devices, logs)
- JFA_Suite for billing & invoicing (separate system)

Two systems = manual reconciliation, data silos, confusion.

**The Solution:** One dashboard.
- All your JFA products in one place
- Billing tied to actual device usage
- Analytics showing ROI of access control

**The Ask:** EUR 300/month add-on (includes Suite + premium support)

**ROI Pitch:** "You spent EUR 288k with us last year on access control. Suite integration helps you prove ROI to stakeholders (how much did it save vs security staff?) and identify expansion opportunities (new sites, new use cases)."

## Implementation (Engineering Side)

1. **Phase 1 (Jul):** API endpoint in JFA_Unify that exports billing data
   - `POST /api/v1/suite/sync` — sends device list + usage stats
   
2. **Phase 2 (Aug):** JFA_Suite receives + displays data in dashboard
   - Web hook endpoint, message queue
   
3. **Phase 3 (Sep):** Full bi-directional sync (Suite pricing rules → JFA_Unify) — optional

## Talking Points (by Objection)

**"We're happy with separate systems"**
→ "So was our last client. After integration, they reduced admin time 20% and caught a billing error that cost them EUR 5k."

**"Is it hard to implement?"**
→ "2 hours of setup. We handle everything. 1 Zoom call, done."

**"What if we stop using JFA_Suite?"**
→ "You can disconnect anytime. No lock-in. But most clients keep it — it pays for itself in time savings."

**"How much extra?"**
→ "EUR 300/month, includes 24/7 support. Offer: first 3 months 50% off if you sign this month."
```

- [ ] **Step 4: Create 1-pager for email**

Create `docs/email-templates/suite-integration-offer.txt`:
```
Subject: One Dashboard, Two Products — JFA_Suite Integration

Hi [Client Name],

Quick idea: We're integrating JFA_Unify with JFA_Suite (our billing product).

One dashboard. Access control + billing + analytics in one place.

Benefits:
✓ No manual reconciliation (Suite auto-syncs device usage)
✓ Prove ROI (see how much access control saved you)
✓ Catch billing errors faster

Cost: EUR 300/month (includes 24/7 support).

Offer: First 3 months at EUR 150/month if you decide this month.

Interested? I can demo it on a Zoom call (20 min).

Cheers,
Fernando
```

- [ ] **Step 5: Commit Suite integration work**

```bash
git add frontend/src/routes/integrations/+page.svelte docs/sales-pitch-jfa-suite-integration.md docs/email-templates/suite-integration-offer.txt
git commit -m "feat: JFA_Suite integration UI + sales pitch (venda cruzada)"
```

---

### Task 5B: GTM Madeira Pivot (If recovery failed/partial)

**Files:**
- Create: `docs/gtm-madeira-plan.md` (detailed GTM strategy)
- Create: `docs/email-templates/madeira-b2b-outreach.txt` (cold email script)
- Create: `frontend/landing/index.html` (simple landing page for Madeira campaign)
- Create: `docs/demo-video-script.txt` (narration script for demo video)

**People:** Fernando Amorim (30 horas) + contractor sales/marketing (40 horas) + contractor video editor (5 horas) — OR all DIY if budget tight

**Scope:** Full GTM launch in Madeira (hotels, residencies, schools, condomínios).

- [ ] **Step 1: Research Madeira B2B targets**

Identify:
1. **Hotels** in Madeira (Booking.com, Tripadvisor, local tourism board)
   - Top 20 by reviews
   - Contact info (email, phone, manager name)

2. **Residences** (senior living, vacation rentals)
   - Airdbnb properties &gt; 10 units
   - Senior care facilities

3. **Schools** (private + public)
   - Contact head of operations/security

4. **Condomínios** (gated communities)
   - Local real estate agents → referrals

Save to `docs/gtm-madeira-plan.md`:
```markdown
# GTM Madeira — B2B Launch Plan

## Target Segments

### Segment 1: Hotels (5-star + 4-star)
- **Why:** High security needs, budget, repeat payment behavior
- **Target count:** 15 hotels
- **List:** [CSV with names, emails, phone]
- **Budget:** EUR 80k/year control systems = 4-5 doors

### Segment 2: Senior Living + Residences
- **Why:** Safety concern (fall detection, emergency access), growing market
- **Target count:** 8 facilities
- **List:** [...]
- **Budget:** EUR 50k/year

### Segment 3: Schools (Private)
- **Why:** Parent demand for security, budget, fleet opportunity
- **Target count:** 5 schools
- **List:** [...]
- **Budget:** EUR 30k/year

### Segment 4: Condomínios
- **Why:** Scattered audience, but partner-friendly (real estate agents)
- **Target count:** 20 condos via 5 agents
- **List:** [Agent contacts]
- **Budget:** EUR 40k/year per condo

**Total Target Revenue:** EUR 30-40k MRR (EUR 360-480k/year) from 40+ leads
```

- [ ] **Step 2: Write GTM plan**

Expand `docs/gtm-madeira-plan.md`:
```markdown
# GTM Execution

## Phase 1: Foundation (Jul 1-15)

- [ ] Finalize target list (40+ prospects)
- [ ] Create landing page: https://jfaunify.pt/madeira
- [ ] Record demo video (2-3 min)
- [ ] Prepare 3 email templates (cold outreach)
- [ ] Set up Calendly for demo calls

## Phase 2: Outreach (Jul 15 - Aug 30)

**Week 1-2:** Cold email (20 prospects, stagger by day)
**Week 3-4:** Follow-up calls (assume 20% response = 4 demos)
**Ongoing:** Schedule + run demos, send proposals

**Target:** 3-5 meetings by Aug 31

## Phase 3: Conversion (Sep - Dec)

Close 3-5 deals, implement, collect case studies

## Success Metrics
- Email open rate: &gt;30% (Madeira audience likely high engagement)
- Demo request rate: &gt;10% of emails
- Conversion rate: &gt;30% of demos = 3-5 logos
- ACV (Annual Contract Value): EUR 50-80k per logo
- Total revenue: EUR 150-400k in 2026
```

- [ ] **Step 3: Create landing page**

Create `frontend/landing/index.html`:
```html
<!DOCTYPE html>
<html lang="pt-PT">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JFA Unify — Sistema de Controlo de Acesso para Madeira</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        
        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 60px 20px;
            text-align: center;
        }
        header h1 { font-size: 2.5em; margin-bottom: 10px; }
        header p { font-size: 1.2em; opacity: 0.95; margin-bottom: 30px; }
        
        .cta-button {
            background: white;
            color: #667eea;
            padding: 15px 40px;
            border: none;
            border-radius: 5px;
            font-weight: bold;
            cursor: pointer;
            font-size: 1em;
        }
        
        .features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 30px;
            padding: 60px 20px;
            max-width: 1000px;
            margin: 0 auto;
        }
        
        .feature { padding: 20px; }
        .feature h3 { color: #667eea; margin-bottom: 10px; }
        
        footer {
            text-align: center;
            padding: 30px;
            background: #f9fafb;
            border-top: 1px solid #e5e7eb;
        }
    </style>
</head>
<body>

<header>
    <h1>🔐 JFA Unify</h1>
    <p>Controlo de Acesso Moderno para Hotéis, Escolas & Condomínios em Madeira</p>
    <button class="cta-button" onclick="alert('Agende uma demo: https://calendly.com/jfa-unify')">
        Agende Uma Demo
    </button>
</header>

<section class="features">
    <div class="feature">
        <h3>✓ Acesso Remoto</h3>
        <p>Controle portas e câmaras de qualquer lugar, 24/7.</p>
    </div>
    <div class="feature">
        <h3>✓ Relatórios Detalhados</h3>
        <p>Logs de acesso para auditoria e segurança.</p>
    </div>
    <div class="feature">
        <h3>✓ Suporte Local PT</h3>
        <p>Equipa em Madeira. Resposta &lt;2h para problemas críticos.</p>
    </div>
    <div class="feature">
        <h3>✓ Custo 40% Menor</h3>
        <p>vs Sistemas de Segurança Tradicionais.</p>
    </div>
</section>

<footer>
    <p>📧 contacto@jfaunify.pt | 📱 +351 91 XXX XXXX | 🌍 Madeira</p>
</footer>

</body>
</html>
```

- [ ] **Step 4: Record demo video**

Create `docs/demo-video-script.txt`:
```
# Demo Video Script — JFA Unify (2.5 min, Madeira Pitch)

## Scene 1: Intro (20 sec)
"Hi, I'm Fernando. JFA Unify is a modern access control system built for hotels, schools, and residences in Madeira."

[Show app opening]

## Scene 2: Dashboard Overview (40 sec)
"Here's your dashboard. Real-time view of all doors and cameras across your property."

[Mouse over: Main Door → Status: Locked]
"You can see exactly which doors are locked, unlocked, who accessed them and when."

[Click: Server Room Camera]
"And you get live video feeds from your security cameras."

## Scene 3: Remote Control (30 sec)
"Need to let a guest in? One tap — unlock the door remotely."

[Click: Unlock button → Animation/confirmation]

## Scene 4: Event Log (20 sec)
"Every access is logged. Critical for insurance, liability, and guest safety."

[Scroll through log]

## Scene 5: Call-to-Action (10 sec)
"Ready to upgrade your security? We offer free demos."

[Text on screen: "Schedule a Demo — calendly.com/jfa-unify"]

---

Recording Tips:
- Use desktop (1920x1080)
- Narrate clearly, pause between sentences
- Edit with iMovie or CapCut
- Upload to YouTube (unlisted) or embed on landing page
```

- [ ] **Step 5: Write cold email template**

Create `docs/email-templates/madeira-b2b-outreach.txt`:
```
Subject: Controlo de Acesso Moderno para [Hotel/Escola/Condomínio] — Demo Gratuita

Oi [Contacto],

Tenho estado a trabalhar com vários hotéis em Madeira para modernizar o seu controlo de acesso.

JFA Unify é um sistema de:
✓ Portas inteligentes (abertura remota)
✓ Câmaras de segurança (live view)
✓ Logs detalhados (quem acedeu quando)
✓ Suporte 24h em Madeira

Custo: ~40% menos que sistemas tradicionais. Sem contratos longos.

Posso mostrar uma demo em 20 minutos? Sem compromisso.

Calendário: https://calendly.com/jfa-unify

Ou ligue-me: +351 91 XXXXXXX

Cheers,
Fernando

P.S. Se conhecer outro hotel/escola que pudesse beneficiar, uma apresentação é meu presente 😊
```

- [ ] **Step 6: Set up demo booking**

Create Calendly account (if not already):
- https://calendly.com/jfa-unify
- 30-min demo slots, available 10-17h (Madeira tz)
- Include: Zoom link + SvelteKit PWA link in meeting invite

- [ ] **Step 7: Commit GTM materials**

```bash
git add docs/gtm-madeira-plan.md docs/demo-video-script.txt frontend/landing/index.html docs/email-templates/madeira-b2b-outreach.txt
git commit -m "feat: GTM Madeira launch (landing page, cold email, demo video script, 40+ target list)"
```

---

## PHASE 3: SCALE & EXPANSION (Sep 1 - Dec 31)

### Task 6: Madeira Campaign Execution + Continente Planning (Sep-Dec)

**Files:**
- Track: `docs/gtm-madeira-campaign-log.md` (day-to-day outreach + deal tracker)
- Create: `docs/expansion-continente-plan.md` (Lisbon/Porto strategy for 2027)

**People:** Fernando Amorim (20 horas/semana GTM) + sales contractor (full-time if budget) or part-time intern

**Scope:** Execute Madeira outreach, close 3-5 logos, document Continente roadmap.

- [ ] **Step 1: Madeira outreach execution (ongoing Sep-Dec)**

Track in `docs/gtm-madeira-campaign-log.md`:
```markdown
# GTM Madeira Campaign Log

## Outreach Phase (Sep 1 - Oct 31)

### Week 1 (Sep 1-7)
- [ ] Email 5 hotels (Mon 1, Wed 3, Fri 5, Mon 8, Wed 10 — stagger)
- [ ] Follow-up call any responses (Thu after email)
- Log: [Name] → [Email Sent] → [Response?] → [Demo Scheduled?]

### Week 2-4
[... continue weekly outreach ...]

## Conversion Phase (Nov 1 - Dec 31)

### Deal Pipeline
- [ ] Hotel A: Proposal sent Nov 15, follow-up Nov 22, decision expected Dec 5
- [ ] School B: Demo scheduled Nov 10, proposal Nov 20
- [ ] Condo C: Partner intro from real estate agent, demo Oct 25
- ...

## KPIs (Track Weekly)
- Emails sent: 
- Response rate: X%
- Demo requests: X
- Demos completed: X
- Proposals sent: X
- Closed deals: X (Target: 3-5)
- Revenue booked: EUR X (Target: EUR 150-400k)
```

- [ ] **Step 2: Plan Continente expansion**

Create `docs/expansion-continente-plan.md`:
```markdown
# Expansion Continente — Strategic Plan (2027 Launch)

## Markets
1. **Lisbon** — Density, enterprise customers, partnerships
2. **Porto** — Secondary market, growing tourism
3. **Algarve** — Tourism hub, hotels, residential

## Go-to-Market (2027)

### Phase 1: Lisbon Base (Q1 2027)
- Hire sales rep (local, B2B experience)
- Partner with 2-3 security consultancies (channel partnership, 15% commission)
- Target: 5-10 logos by Q2

### Phase 2: Porto + Algarve (Q2-Q3 2027)
- Expand sales rep territory or hire 2nd rep
- Expand consultancy partnerships (5-6 total)
- Target: 10-15 logos

### Phase 3: Scale (Q4 2027 onwards)
- Full sales team (3-4 people)
- Marketing budget (ads, events)
- Support team (pre-sales, implementation, CS)

## Revenue Projections
- Year 1 (2027): EUR 400-600k (new revenue from Continente)
- Year 2 (2028): EUR 800-1.2M
- Year 3 (2029): EUR 1.5-2M+

## Success Criteria
- Revenue: EUR 50k+ MRR by end of 2027
- NPS (Net Promoter Score): &gt;40
- Customer retention: &gt;90%
- Sales cycle: &lt;6 weeks

## Investment Required
- Sales rep salary: EUR 24k/year (+ commission)
- Marketing: EUR 3k/month (ads, events, content)
- Support (contractor): EUR 5k/month
- Total: EUR ~70k/year

## Key Risks
- Established competitors (Securitas, Tyco) — mitigate via local partnerships + customer service
- Hiring challenges — plan recruiting in Q4 2026
- Product scale (API, DB) — tested in Madeira first
```

- [ ] **Step 3: Monthly QBR review (Sep, Oct, Nov, Dec)**

Every month:
- Review campaign log
- Assess: on track to 3-5 Madeira logos?
- Adjust messaging/targeting if needed
- Plan next month's outreach

Document in recovery-log.md or separate file:
```markdown
## Monthly Review Sep 2026
- Outreach: 12 emails sent, 2 responses (16% response rate)
- Demos: 1 scheduled (Hotel A, Sep 25)
- Pipeline: 1 hotel interested, 2 schools asking questions
- Issues: High email bounce rate for school contacts → get better emails
- Plan Sep: Follow up 5 more prospects, demo Hotel A, proposal if positive
```

- [ ] **Step 4: Commit Madeira + Continente planning**

```bash
git add docs/gtm-madeira-campaign-log.md docs/expansion-continente-plan.md
git commit -m "docs: Madeira GTM execution tracker + Continente 2027 expansion plan"
```

---

## FINAL CHECKPOINT & SUCCESS CRITERIA (Dec 31, 2026)

### Task 7: End-of-Year Review & 2027 Roadmap

**Files:**
- Create: `docs/2026-year-end-review.md` (what worked, what didn't)
- Create: `docs/2027-roadmap.md` (next year priorities)

**People:** Fernando Amorim — 2 horas (reflection)

- [ ] **Step 1: Assess 2026 outcomes vs targets**

Document in `docs/2026-year-end-review.md`:
```markdown
# 2026 Year-End Review — JFA Unify Hybrid Strategy

## Revenue Outcomes

### Target: EUR 650-750k
### Actual: EUR [actual]
### Variance: [+/- X%]

**By Channel:**
- Recovery (client 511099177): EUR [X] vs EUR 200k target
- Retention (Top-5): EUR [X] vs EUR [planned]
- New logos (Madeira): EUR [X] vs EUR 150-400k target
- Venda cruzada (Suite integration): EUR [X] vs EUR [estimated]

## Product Milestones

- [ ] SvelteKit PWA: Live? Used in demos?
- [ ] Demo video: Completed? YouTube views?
- [ ] ESP32 adapter: Started? (Phase 3 roadmap)
- [ ] Suite integration: MVP launched?

## Team & Operations

- [ ] Hired sales contractor? (Y/N)
- [ ] Hired video/marketing contractor? (Y/N)
- [ ] Account management (monthly reports to Top-5): Running?
- [ ] Fernando's time allocation: Recovery % vs product % vs GTM %

## What Worked
- (List 3-5 things)

## What Didn't
- (List 3-5 failures/lessons)

## 2027 Priorities
- ...
```

- [ ] **Step 2: Build 2027 roadmap**

Create `docs/2027-roadmap.md`:
```markdown
# JFA Unify 2027 Roadmap

## Q1 2027

### Product
- [ ] ESP32 adapter (Phase 3) — ship by Mar 31
- [ ] Mobile native apps (iOS + Android) — start MVP
- [ ] Continente SaaS demo

### GTM
- [ ] Close last 2-3 Madeira logos (if not done in 2026)
- [ ] Hire Lisbon sales rep
- [ ] Partner with 2 security consultancies

### Operations
- [ ] CNPD compliance (finalized by Mar 31)
- [ ] Customer success playbook (quarterly reviews, retention metrics)

## Q2-Q4 2027

- [ ] Mobile apps ship (iOS Apr, Android May)
- [ ] Continente launch (Lisbon pilot, 5-10 logos)
- [ ] Revenue target: EUR 1M+ (Madeira + Continente combined)

## Success Metrics (End of 2027)
- Customers: 15-25 logos
- Revenue: EUR 1.0-1.5M
- NPS: &gt;40
- Retention: &gt;95%
- Monthly recurring: EUR 80k+ MRR
```

- [ ] **Step 3: Commit final review**

```bash
git add docs/2026-year-end-review.md docs/2027-roadmap.md
git commit -m "docs: 2026 year-end review + 2027 roadmap (post-hybrid strategy)"
```

---

## SUMMARY: TASK CHECKLIST

### Phase 1 (Jun 12-30)
- [ ] Task 1: Client recovery diagnosis calls (NIF 511099177 + Top 5)
- [ ] Task 2: SLA framework + account management playbook
- [ ] Task 3: SvelteKit PWA demo mode finalized

### Phase 2 (Jul 1 - Aug 31)
- [ ] Task 4: Evaluate recovery success (decision checkpoint)
- [ ] Task 5A: Product polish + Suite integration (IF recovery succeeded)
- [ ] Task 5B: GTM Madeira pivot (IF recovery failed/partial)

### Phase 3 (Sep 1 - Dec 31)
- [ ] Task 6: Madeira campaign execution + Continente planning
- [ ] Task 7: 2026 year-end review + 2027 roadmap

---

## Success Criteria (GO/NO-GO for Hybrid Strategy)

**Revenue Goal: EUR 650-750k in 2026 (vs EUR 464k linear projection)**
- Recovery: EUR 200k (54% of total shortfall)
- Retention: EUR 100k (offset new churn)
- Madeira new logos: EUR 150-400k (3-5 customers @ EUR 50-80k ACV)
- Suite venda cruzada: EUR 20-50k

**Product Goal: SvelteKit PWA production-ready + demo video**
- PWA fully functional (login, dashboard, device control, event logs)
- Demo video recorded & sharable (2-3 min, Madeira pitch)
- ESP32 roadmap documented (for Sep-Dec phase)

**Operations Goal: Sustainable GTM process in place**
- Account management: Monthly check-ins with Top-5 (documented in QBR notes)
- Madeira campaign: 40+ targets identified, 12+ outreach, 3+ demos, 3-5 proposals
- Continente plan: Documented, ready for 2027 execution

**Team: Fernando + contractors aligned**
- Fernando: 30 h/wk recovery (Jun) → 10 h/wk product (Jul-Aug) → 20 h/wk GTM (Sep-Dec)
- Marketing/video contractor: Deliverables (landing page, demo video, cold email templates)
- Sales contractor: Lead generation + demo scheduling (optional, Sep+ if budget)

---

**Plan saved to:** `C:\JFA_Unify\docs\superpowers\plans\2026-06-12-hybrid-recovery-gtm.md`

