<script>
  import { onMount } from 'svelte';
  import PinPad from '$lib/components/PinPad.svelte';
  import CardReader from '$lib/components/CardReader.svelte';
  import AccessLog from '$lib/components/AccessLog.svelte';
  import DeviceStatus from '$lib/components/DeviceStatus.svelte';
  import { validateAccess, listDevices, ApiError } from '$lib/services/api.js';
  import { mqttClient } from '$lib/services/mqtt.js';
  import { setDevices, selectedDevice, deviceCounts, selectDevice, updateDeviceOnlineState } from '$lib/stores/device.js';
  import { isAuthenticated } from '$lib/stores/auth.js';

  // Estado do dashboard
  let showPinPad = false;
  let accessResult = null;   // { allowed, reason }
  let accessResultTimeout;
  let accessLogRef;          // ref para AccessLog.appendLog
  let isValidating = false;

  // Device activo (subscrito ao store derivado)
  $: device = $selectedDevice;
  $: counts = $deviceCounts;

  // ─── Handlers de eventos dos componentes ─────────────────────────────────

  /** Chamado pelo PinPad quando o utilizador submete um PIN */
  async function handlePinSubmit(event) {
    const { pin, device_id, timestamp, signature } = event.detail;

    if (!device_id) {
      showFeedback({ allowed: false, reason: 'Nenhum device seleccionado.' });
      return;
    }

    isValidating = true;
    try {
      // TODO: O signature já foi calculado no PinPad via crypto.js
      // O servidor valida HMAC + PIN
      const result = await validateAccess({ pin, device_id, timestamp });
      showFeedback(result);

      // Adiciona ao log em tempo real
      accessLogRef?.appendLog({
        id: crypto.randomUUID(),
        device_id,
        access_type: result.allowed ? 'pin_valid' : 'pin_invalid',
        card_uid: null,
        success: result.allowed,
        timestamp: new Date(timestamp).toISOString(),
      });
    } catch (err) {
      if (err instanceof ApiError) {
        showFeedback({ allowed: false, reason: err.message });
      } else {
        showFeedback({ allowed: false, reason: 'Erro inesperado.' });
      }
    } finally {
      isValidating = false;
      showPinPad = false;
    }
  }

  /** Chamado pelo CardReader quando um cartão é lido */
  async function handleCardRead(event) {
    const { card_uid, device_id, timestamp, manual } = event.detail;

    if (!device_id) {
      showFeedback({ allowed: false, reason: 'Nenhum device seleccionado.' });
      return;
    }

    isValidating = true;
    try {
      const result = await validateAccess({ card_uid, device_id, timestamp });
      showFeedback(result);

      accessLogRef?.appendLog({
        id: crypto.randomUUID(),
        device_id,
        access_type: result.allowed ? 'card_read' : 'card_unknown',
        card_uid,
        success: result.allowed,
        timestamp: new Date(timestamp).toISOString(),
      });
    } catch (err) {
      if (err instanceof ApiError) {
        showFeedback({ allowed: false, reason: err.message });
      } else {
        showFeedback({ allowed: false, reason: 'Erro inesperado.' });
      }
    } finally {
      isValidating = false;
    }
  }

  function showFeedback(result) {
    accessResult = result;
    clearTimeout(accessResultTimeout);
    accessResultTimeout = setTimeout(() => { accessResult = null; }, 5000);
  }

  // ─── Inicialização ────────────────────────────────────────────────────────

  onMount(async () => {
    // Ligar ao broker MQTT
    try {
      await mqttClient.connect();

      // Subscrever heartbeats de todos os devices
      mqttClient.subscribe('devices/+/heartbeat', (message, topic) => {
        try {
          const deviceId = topic.split('/')[1];
          const data = JSON.parse(message);
          updateDeviceOnlineState(deviceId, {
            online: data.online ?? true,
            last_seen: data.timestamp ?? Date.now(),
            uptime_seconds: data.uptime_seconds,
            rssi: data.rssi,
          });
        } catch { /* ignora */ }
      });
    } catch (err) {
      console.error('[Dashboard] Erro ao ligar MQTT:', err);
    }

    // Carregar lista de devices
    // TODO: Descomentar após ter autenticação implementada
    // try {
    //   const deviceList = await listDevices();
    //   setDevices(deviceList);
    // } catch (err) {
    //   console.error('[Dashboard] Erro ao carregar devices:', err);
    // }

    // Dados de exemplo enquanto a API não está integrada
    setDevices([
      {
        id: 'dev-001',
        name: 'Porta Principal',
        type: 'door',
        auth_mode: 'pin_card',
        location: 'Entrada Norte',
        firmware_version: '2.1.4',
      },
      {
        id: 'dev-002',
        name: 'Portão Garagem',
        type: 'gate',
        auth_mode: 'card',
        location: 'Garagem',
        firmware_version: '2.0.8',
      },
    ]);
  });
</script>

<svelte:head>
  <title>JFA Remotes — Dashboard</title>
</svelte:head>

<div class="dashboard">
  <!-- Barra de topo -->
  <header class="topbar">
    <div class="topbar-brand">
      <span class="brand-logo" aria-hidden="true">🔐</span>
      <span class="brand-name">JFA Remotes</span>
    </div>
    <div class="topbar-stats">
      <span class="stat-chip online">
        <span class="chip-dot" aria-hidden="true"></span>
        {counts.online} online
      </span>
      <span class="stat-chip offline">
        <span class="chip-dot" aria-hidden="true"></span>
        {counts.offline} offline
      </span>
    </div>
  </header>

  <!-- Feedback de resultado de acesso -->
  {#if accessResult}
    <div
      class="access-feedback"
      class:feedback-success={accessResult.allowed}
      class:feedback-failure={!accessResult.allowed}
      role="status"
      aria-live="polite"
    >
      <span class="feedback-icon" aria-hidden="true">
        {accessResult.allowed ? '✅' : '❌'}
      </span>
      <div class="feedback-text">
        <strong>{accessResult.allowed ? 'Acesso Autorizado' : 'Acesso Negado'}</strong>
        <span>{accessResult.reason ?? ''}</span>
      </div>
      <button class="feedback-close" on:click={() => { accessResult = null; }} aria-label="Fechar notificação">✕</button>
    </div>
  {/if}

  <!-- Layout principal -->
  <main class="main-content">
    <!-- Coluna esquerda: devices -->
    <aside class="sidebar">
      <h2 class="section-title">Devices</h2>

      <!-- Lista de devices -->
      <div class="device-list" role="list">
        {#each $deviceCounts.total > 0 ? [] : [] as device}
          <!-- Preenchido dinamicamente -->
        {/each}
      </div>

      <!-- Status do device seleccionado -->
      {#if device}
        <DeviceStatus {device} />
      {:else}
        <div class="no-device">
          <p>Seleccione um device para ver o estado.</p>
        </div>
      {/if}

      <!-- Botões de acção -->
      <div class="action-buttons">
        <button
          class="action-btn primary"
          on:click={() => { showPinPad = true; }}
          disabled={!device || isValidating}
        >
          <span aria-hidden="true">🔢</span>
          Inserir PIN
        </button>
      </div>
    </aside>

    <!-- Coluna central: card reader + log -->
    <section class="content-area">
      <!-- Card Reader -->
      {#if device}
        <div class="panel">
          <CardReader
            deviceId={device.id}
            topic="devices/{device.id}/card"
            on:cardRead={handleCardRead}
          />
        </div>
      {/if}

      <!-- Access Log -->
      <div class="panel panel-wide">
        <AccessLog
          deviceId={device?.id ?? ''}
          bind:this={accessLogRef}
          autoRefresh={30}
        />
      </div>
    </section>
  </main>

  <!-- Modal do PinPad -->
  {#if showPinPad}
    <PinPad
      deviceId={device?.id ?? ''}
      on:submit={handlePinSubmit}
      on:cancel={() => { showPinPad = false; }}
    />
  {/if}

  <!-- Loading overlay durante validação -->
  {#if isValidating}
    <div class="validating-overlay" role="status" aria-label="A validar acesso...">
      <div class="validating-spinner"></div>
      <p>A validar...</p>
    </div>
  {/if}
</div>

<style>
  /* Reset e base */
  :global(*, *::before, *::after) {
    box-sizing: border-box;
  }

  :global(body) {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #f0f2f5;
    color: #1a1a2e;
  }

  .dashboard {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
  }

  /* Topbar */
  .topbar {
    background: #1a1a2e;
    color: #ffffff;
    padding: 0.75rem 1.5rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    position: sticky;
    top: 0;
    z-index: 100;
  }

  .topbar-brand {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 1.1rem;
    font-weight: 700;
  }

  .brand-logo { font-size: 1.3rem; }

  .topbar-stats {
    display: flex;
    gap: 0.75rem;
  }

  .stat-chip {
    display: flex;
    align-items: center;
    gap: 0.3rem;
    font-size: 0.8rem;
    font-weight: 600;
    padding: 0.25rem 0.65rem;
    border-radius: 20px;
  }

  .stat-chip.online  { background: rgba(46,125,50,0.25); color: #a5d6a7; }
  .stat-chip.offline { background: rgba(198,40,40,0.25); color: #ef9a9a; }

  .chip-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: currentColor;
  }

  /* Feedback banner */
  .access-feedback {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.85rem 1.5rem;
    font-size: 0.9rem;
    animation: slideDown 0.2s ease-out;
  }

  @keyframes slideDown {
    from { transform: translateY(-10px); opacity: 0; }
    to   { transform: translateY(0);     opacity: 1; }
  }

  .feedback-success { background: #e8f5e9; border-bottom: 2px solid #2e7d32; color: #1b5e20; }
  .feedback-failure { background: #ffebee; border-bottom: 2px solid #c62828; color: #7f0000; }

  .feedback-icon { font-size: 1.3rem; flex-shrink: 0; }

  .feedback-text {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
  }

  .feedback-close {
    background: none;
    border: none;
    cursor: pointer;
    color: inherit;
    opacity: 0.6;
    font-size: 1rem;
    padding: 0.2rem 0.4rem;
    border-radius: 4px;
    transition: opacity 0.15s;
  }

  .feedback-close:hover { opacity: 1; }

  /* Layout principal */
  .main-content {
    flex: 1;
    display: grid;
    grid-template-columns: 320px 1fr;
    gap: 1.5rem;
    padding: 1.5rem;
    max-width: 1400px;
    margin: 0 auto;
    width: 100%;
  }

  /* Sidebar */
  .sidebar {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .section-title {
    font-size: 0.85rem;
    font-weight: 700;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin: 0;
  }

  .device-list {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .no-device {
    background: #fff;
    border-radius: 12px;
    padding: 1.5rem;
    text-align: center;
    color: #aaa;
    font-size: 0.85rem;
  }

  .action-buttons {
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
  }

  .action-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    padding: 0.8rem;
    font-size: 0.95rem;
    font-weight: 600;
    border: none;
    border-radius: 10px;
    cursor: pointer;
    transition: background 0.15s, transform 0.08s, box-shadow 0.15s;
  }

  .action-btn.primary {
    background: #1a1a2e;
    color: #fff;
  }

  .action-btn.primary:hover:not(:disabled) {
    background: #2d2d4a;
    box-shadow: 0 4px 14px rgba(26,26,46,0.25);
  }

  .action-btn:disabled {
    background: #ccc;
    cursor: not-allowed;
  }

  /* Área de conteúdo */
  .content-area {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }

  .panel {
    display: flex;
    justify-content: flex-start;
  }

  .panel-wide {
    width: 100%;
  }

  /* Overlay de validação */
  .validating-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.4);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 1rem;
    color: #fff;
    font-size: 1rem;
    z-index: 900;
  }

  .validating-spinner {
    width: 40px;
    height: 40px;
    border: 4px solid rgba(255,255,255,0.3);
    border-top-color: #fff;
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
  }

  @keyframes spin { to { transform: rotate(360deg); } }

  /* Responsivo */
  @media (max-width: 768px) {
    .main-content {
      grid-template-columns: 1fr;
      padding: 1rem;
    }
  }
</style>
