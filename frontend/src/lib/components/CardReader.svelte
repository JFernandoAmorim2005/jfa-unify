<script>
  import { onMount, onDestroy, createEventDispatcher } from 'svelte';
  import { mqttClient } from '../services/mqtt.js';

  // Props
  export let deviceId = '';
  export let topic = '';   // MQTT topic a subscrever, ex: "devices/{id}/card"

  const dispatch = createEventDispatcher();

  let cardUid = '';
  let isScanning = false;
  let lastReadTime = null;
  let lastReadTimeFormatted = '';
  let connectionStatus = 'disconnected'; // 'connected' | 'disconnected' | 'error'
  let manualUid = '';
  let showManualEntry = false;
  let errorMessage = '';

  // Intervalo de formatação de tempo relativo
  let relativeTimeInterval;

  function formatRelativeTime(timestamp) {
    if (!timestamp) return '';
    const diff = Math.floor((Date.now() - timestamp) / 1000);
    if (diff < 5)  return 'agora mesmo';
    if (diff < 60) return `há ${diff}s`;
    if (diff < 3600) return `há ${Math.floor(diff / 60)}min`;
    return new Date(timestamp).toLocaleTimeString('pt-PT');
  }

  // Handler para mensagens MQTT de leitura de cartão NFC/RFID
  function handleCardMessage(message) {
    try {
      const data = typeof message === 'string' ? JSON.parse(message) : message;

      if (data.card_uid) {
        cardUid = data.card_uid.toUpperCase();
        lastReadTime = data.timestamp ? new Date(data.timestamp).getTime() : Date.now();
        lastReadTimeFormatted = formatRelativeTime(lastReadTime);
        isScanning = false;
        errorMessage = '';

        // Emite evento para o componente pai processar validação
        // TODO: O pai deve chamar api.validateAccess({ card_uid: cardUid, device_id: deviceId })
        dispatch('cardRead', {
          card_uid: cardUid,
          device_id: deviceId,
          timestamp: lastReadTime
        });
      }
    } catch (err) {
      console.error('[CardReader] Erro ao processar mensagem MQTT:', err);
      errorMessage = 'Erro ao ler mensagem do cartão.';
    }
  }

  // Handler para status de scanning (ex: device a aguardar cartão)
  function handleScanStatus(message) {
    try {
      const data = typeof message === 'string' ? JSON.parse(message) : message;
      if (typeof data.scanning === 'boolean') {
        isScanning = data.scanning;
      }
    } catch {
      // ignora mensagens mal formadas
    }
  }

  function handleConnectionChange(status) {
    connectionStatus = status;
  }

  async function connectMqtt() {
    if (!topic) return;
    try {
      // TODO: Subscrever tópicos MQTT via mqtt.js
      // mqttClient.subscribe(topic, handleCardMessage);
      // mqttClient.subscribe(`${topic}/status`, handleScanStatus);
      // mqttClient.onConnectionChange(handleConnectionChange);
      connectionStatus = 'connected'; // placeholder
    } catch (err) {
      connectionStatus = 'error';
      errorMessage = 'Não foi possível ligar ao broker MQTT.';
    }
  }

  function handleManualSubmit() {
    const uid = manualUid.trim().toUpperCase();
    if (!uid) return;

    cardUid = uid;
    lastReadTime = Date.now();
    lastReadTimeFormatted = formatRelativeTime(lastReadTime);
    manualUid = '';
    showManualEntry = false;

    dispatch('cardRead', {
      card_uid: cardUid,
      device_id: deviceId,
      timestamp: lastReadTime,
      manual: true
    });
  }

  function handleManualKeydown(event) {
    if (event.key === 'Enter') handleManualSubmit();
    if (event.key === 'Escape') { showManualEntry = false; manualUid = ''; }
  }

  function clearCard() {
    cardUid = '';
    lastReadTime = null;
    lastReadTimeFormatted = '';
    errorMessage = '';
  }

  onMount(async () => {
    await connectMqtt();

    // Actualiza tempo relativo a cada 10 segundos
    relativeTimeInterval = setInterval(() => {
      if (lastReadTime) {
        lastReadTimeFormatted = formatRelativeTime(lastReadTime);
      }
    }, 10000);
  });

  onDestroy(() => {
    clearInterval(relativeTimeInterval);
    // TODO: mqttClient.unsubscribe(topic, handleCardMessage);
  });
</script>

<div class="card-reader">
  <!-- Cabeçalho com status de ligação -->
  <div class="header">
    <h2 class="title">Tap Card</h2>
    <span class="connection-badge" class:connected={connectionStatus === 'connected'} class:error={connectionStatus === 'error'}>
      <span class="badge-dot"></span>
      {#if connectionStatus === 'connected'}MQTT OK
      {:else if connectionStatus === 'error'}Erro
      {:else}Desligado{/if}
    </span>
  </div>

  <!-- Área principal de scan -->
  <div
    class="scanner-area"
    class:scanning={isScanning}
    class:has-card={cardUid}
    role="status"
    aria-live="polite"
    aria-label={isScanning ? 'A aguardar cartão' : cardUid ? `Cartão lido: ${cardUid}` : 'Pronto para leitura'}
  >
    {#if cardUid}
      <!-- Estado: cartão lido -->
      <div class="card-success">
        <svg class="card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
          <rect x="2" y="5" width="20" height="14" rx="3" />
          <path d="M2 10h20" />
          <path d="M6 15h4" stroke-linecap="round" />
          <path d="M14 15h2" stroke-linecap="round" />
        </svg>
        <p class="card-uid">{cardUid}</p>
        <button class="clear-btn" on:click={clearCard} aria-label="Limpar leitura">Limpar</button>
      </div>
    {:else if isScanning}
      <!-- Estado: scanning activo -->
      <div class="scanning-pulse">
        <svg class="nfc-icon pulse" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
          <path d="M20 12a8 8 0 0 1-8 8M4 12a8 8 0 0 1 8-8" stroke-linecap="round" />
          <path d="M17 12a5 5 0 0 1-5 5M7 12a5 5 0 0 1 5-5" stroke-linecap="round" />
          <circle cx="12" cy="12" r="2" fill="currentColor" />
        </svg>
        <p class="scan-text">Scanning...</p>
      </div>
    {:else}
      <!-- Estado: aguardar -->
      <div class="idle-state">
        <svg class="nfc-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
          <path d="M20 12a8 8 0 0 1-8 8M4 12a8 8 0 0 1 8-8" stroke-linecap="round" />
          <path d="M17 12a5 5 0 0 1-5 5M7 12a5 5 0 0 1 5-5" stroke-linecap="round" />
          <circle cx="12" cy="12" r="2" fill="currentColor" />
        </svg>
        <p class="scan-text">Ready for scan</p>
        <p class="scan-hint">Aproxime o cartão NFC/RFID</p>
      </div>
    {/if}
  </div>

  <!-- Informação do último cartão lido -->
  {#if cardUid}
    <div class="card-info-panel">
      <div class="info-row">
        <span class="info-label">UID</span>
        <code class="info-value uid-value">{cardUid}</code>
      </div>
      {#if lastReadTimeFormatted}
        <div class="info-row">
          <span class="info-label">Lido</span>
          <span class="info-value">{lastReadTimeFormatted}</span>
        </div>
      {/if}
      {#if deviceId}
        <div class="info-row">
          <span class="info-label">Device</span>
          <span class="info-value">{deviceId}</span>
        </div>
      {/if}
    </div>
  {/if}

  <!-- Entrada manual de UID (fallback) -->
  <div class="manual-entry-section">
    {#if showManualEntry}
      <div class="manual-form">
        <input
          type="text"
          bind:value={manualUid}
          placeholder="Ex: A1B2C3D4"
          class="manual-input"
          maxlength="20"
          on:keydown={handleManualKeydown}
          aria-label="UID do cartão (entrada manual)"
          autocomplete="off"
          spellcheck="false"
        />
        <div class="manual-actions">
          <button class="manual-submit" on:click={handleManualSubmit} disabled={!manualUid.trim()}>
            Usar UID
          </button>
          <button class="manual-cancel" on:click={() => { showManualEntry = false; manualUid = ''; }}>
            Cancelar
          </button>
        </div>
      </div>
    {:else}
      <button class="manual-toggle" on:click={() => { showManualEntry = true; }}>
        Entrada manual de UID
      </button>
    {/if}
  </div>

  {#if errorMessage}
    <p class="error-msg" role="alert">{errorMessage}</p>
  {/if}
</div>

<style>
  .card-reader {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    padding: 1.5rem;
    background: #ffffff;
    border-radius: 16px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    max-width: 380px;
    width: 100%;
  }

  .header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .title {
    font-size: 1.25rem;
    font-weight: 700;
    color: #1a1a2e;
    margin: 0;
  }

  .connection-badge {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.75rem;
    font-weight: 600;
    color: #999;
    padding: 0.2rem 0.6rem;
    border-radius: 20px;
    background: #f5f5f5;
  }

  .connection-badge.connected { color: #2e7d32; background: #e8f5e9; }
  .connection-badge.error     { color: #c62828; background: #ffebee; }

  .badge-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: currentColor;
  }

  /* Área de scanner */
  .scanner-area {
    padding: 2rem 1.5rem;
    border: 2px dashed #d0d0d0;
    border-radius: 12px;
    text-align: center;
    transition: all 0.3s ease;
    background: #fafafa;
    min-height: 180px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .scanner-area.scanning {
    border-color: #1a1a2e;
    border-style: solid;
    background: #f0f0f8;
  }

  .scanner-area.has-card {
    border-color: #2e7d32;
    border-style: solid;
    background: #f0fff4;
  }

  .nfc-icon {
    width: 64px;
    height: 64px;
    color: #bbb;
    margin-bottom: 0.75rem;
  }

  .scanner-area.scanning .nfc-icon,
  .nfc-icon.pulse {
    color: #1a1a2e;
    animation: pulse 1.2s ease-in-out infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50%       { opacity: 0.6; transform: scale(1.08); }
  }

  .idle-state,
  .scanning-pulse,
  .card-success {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.25rem;
  }

  .scan-text {
    font-size: 1rem;
    font-weight: 600;
    color: #333;
    margin: 0;
  }

  .scan-hint {
    font-size: 0.8rem;
    color: #999;
    margin: 0;
  }

  .card-icon {
    width: 52px;
    height: 52px;
    color: #2e7d32;
    margin-bottom: 0.5rem;
  }

  .card-uid {
    font-size: 1.1rem;
    font-weight: 700;
    color: #2e7d32;
    letter-spacing: 0.1em;
    margin: 0;
  }

  .clear-btn {
    margin-top: 0.5rem;
    padding: 0.3rem 0.8rem;
    font-size: 0.8rem;
    background: none;
    border: 1px solid #a5d6a7;
    border-radius: 6px;
    color: #2e7d32;
    cursor: pointer;
    transition: background 0.15s;
  }

  .clear-btn:hover {
    background: #e8f5e9;
  }

  /* Painel de informação */
  .card-info-panel {
    background: #f8f9fa;
    border-radius: 8px;
    padding: 0.75rem 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }

  .info-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .info-label {
    font-size: 0.75rem;
    font-weight: 600;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    min-width: 48px;
  }

  .info-value {
    font-size: 0.85rem;
    color: #333;
  }

  .uid-value {
    font-family: 'Courier New', monospace;
    background: #e8e8e8;
    padding: 0.1rem 0.4rem;
    border-radius: 4px;
    font-size: 0.8rem;
  }

  /* Entrada manual */
  .manual-entry-section {
    border-top: 1px solid #f0f0f0;
    padding-top: 0.75rem;
  }

  .manual-toggle {
    background: none;
    border: none;
    color: #888;
    font-size: 0.8rem;
    cursor: pointer;
    text-decoration: underline;
    padding: 0;
    transition: color 0.15s;
  }

  .manual-toggle:hover { color: #555; }

  .manual-form {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .manual-input {
    padding: 0.6rem 0.75rem;
    font-size: 0.9rem;
    font-family: 'Courier New', monospace;
    border: 1.5px solid #d0d0d0;
    border-radius: 8px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    outline: none;
    transition: border-color 0.15s;
  }

  .manual-input:focus { border-color: #1a1a2e; }

  .manual-actions {
    display: flex;
    gap: 0.5rem;
  }

  .manual-submit, .manual-cancel {
    flex: 1;
    padding: 0.5rem;
    font-size: 0.85rem;
    border-radius: 7px;
    border: none;
    cursor: pointer;
    font-weight: 600;
    transition: background 0.15s;
  }

  .manual-submit {
    background: #1a1a2e;
    color: #fff;
  }

  .manual-submit:hover:not(:disabled) { background: #2d2d4a; }
  .manual-submit:disabled { background: #ccc; cursor: not-allowed; }

  .manual-cancel {
    background: #f0f0f0;
    color: #555;
  }

  .manual-cancel:hover { background: #e0e0e0; }

  .error-msg {
    color: #c62828;
    font-size: 0.85rem;
    text-align: center;
    margin: 0;
    padding: 0.5rem;
    background: #ffebee;
    border-radius: 6px;
  }
</style>
