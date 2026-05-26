<script>
  import { onMount, onDestroy } from 'svelte';

  // Props
  export let device = null;
  /*
    Estrutura esperada:
    {
      id: string,
      name: string,
      type: 'door' | 'gate' | 'locker' | 'generic',
      auth_mode: 'pin' | 'card' | 'pin_card' | 'card_pin',
      firmware_version: string,
      location: string,
    }
  */

  // Estado
  let isOnline = false;
  let lastSeen = null;
  let lastSeenFormatted = '';
  let heartbeatAge = 0;        // segundos desde o último heartbeat
  let uptimeSeconds = 0;
  let mqttSignalStrength = null; // RSSI em dBm (se disponível)
  let relativeTimeInterval;
  let heartbeatTimeout;

  // Thresholds para considerar device offline (sem heartbeat por X segundos)
  const OFFLINE_THRESHOLD_SEC = 60;
  const WARNING_THRESHOLD_SEC = 30;

  $: statusLevel = heartbeatAge >= OFFLINE_THRESHOLD_SEC
    ? 'offline'
    : heartbeatAge >= WARNING_THRESHOLD_SEC
    ? 'warning'
    : isOnline ? 'online' : 'offline';

  $: statusLabel = {
    online:  'Online',
    warning: 'Intermitente',
    offline: 'Offline',
  }[statusLevel] ?? 'Desconhecido';

  // Mapeamento dos modos de autenticação para labels
  const AUTH_MODE_INFO = {
    pin:      { label: 'Apenas PIN',        icon: '🔢', class: 'mode-pin' },
    card:     { label: 'Apenas Cartão',     icon: '💳', class: 'mode-card' },
    pin_card: { label: 'PIN + Cartão',      icon: '🔐', class: 'mode-combined' },
    card_pin: { label: 'Cartão + PIN',      icon: '🔐', class: 'mode-combined' },
  };

  const DEVICE_TYPE_LABELS = {
    door:    'Porta',
    gate:    'Portão',
    locker:  'Cacifo',
    generic: 'Dispositivo',
  };

  $: authInfo = AUTH_MODE_INFO[device?.auth_mode] ?? { label: device?.auth_mode ?? 'Desconhecido', icon: '?', class: 'mode-unknown' };
  $: deviceTypeLabel = DEVICE_TYPE_LABELS[device?.type] ?? device?.type ?? 'Dispositivo';

  function formatRelativeTime(ts) {
    if (!ts) return 'Nunca';
    const diff = Math.floor((Date.now() - ts) / 1000);
    if (diff < 5)   return 'agora mesmo';
    if (diff < 60)  return `há ${diff}s`;
    if (diff < 3600) return `há ${Math.floor(diff / 60)}min`;
    if (diff < 86400) return `há ${Math.floor(diff / 3600)}h`;
    return new Date(ts).toLocaleDateString('pt-PT');
  }

  function formatUptime(seconds) {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}min`;
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    return m > 0 ? `${h}h ${m}min` : `${h}h`;
  }

  function formatSignal(rssi) {
    if (rssi === null || rssi === undefined) return '—';
    if (rssi >= -50) return `${rssi} dBm (Excelente)`;
    if (rssi >= -65) return `${rssi} dBm (Bom)`;
    if (rssi >= -75) return `${rssi} dBm (Razoável)`;
    return `${rssi} dBm (Fraco)`;
  }

  // Processamento de heartbeat recebido via MQTT
  // Chamar externamente: component.receiveHeartbeat(data)
  export function receiveHeartbeat(data) {
    /*
      Estrutura esperada:
      {
        online: boolean,
        timestamp: number (unix ms),
        uptime_seconds: number,
        rssi: number (dBm, opcional)
      }
    */
    isOnline = data.online ?? true;
    lastSeen = data.timestamp ?? Date.now();
    lastSeenFormatted = formatRelativeTime(lastSeen);
    heartbeatAge = 0;
    uptimeSeconds = data.uptime_seconds ?? uptimeSeconds;
    mqttSignalStrength = data.rssi ?? null;

    // Reset do timeout de offline
    clearTimeout(heartbeatTimeout);
    heartbeatTimeout = setTimeout(() => {
      isOnline = false;
    }, OFFLINE_THRESHOLD_SEC * 1000);
  }

  onMount(() => {
    // TODO: Subscrever tópico MQTT "devices/{device.id}/heartbeat"
    // mqttClient.subscribe(`devices/${device?.id}/heartbeat`, (msg) => {
    //   receiveHeartbeat(JSON.parse(msg));
    // });

    // Actualizar tempo relativo e age a cada 5 segundos
    relativeTimeInterval = setInterval(() => {
      if (lastSeen) {
        lastSeenFormatted = formatRelativeTime(lastSeen);
        heartbeatAge = Math.floor((Date.now() - lastSeen) / 1000);
      }
      if (isOnline) uptimeSeconds += 5;
    }, 5000);
  });

  onDestroy(() => {
    clearInterval(relativeTimeInterval);
    clearTimeout(heartbeatTimeout);
    // TODO: mqttClient.unsubscribe(...)
  });
</script>

<div class="device-status" class:status-online={statusLevel === 'online'} class:status-warning={statusLevel === 'warning'} class:status-offline={statusLevel === 'offline'}>
  {#if device}
    <!-- Cabeçalho do device -->
    <div class="device-header">
      <div class="device-identity">
        <div class="device-type-icon" aria-hidden="true">
          {#if device.type === 'door'}🚪
          {:else if device.type === 'gate'}🔓
          {:else if device.type === 'locker'}🔒
          {:else}📟{/if}
        </div>
        <div class="device-titles">
          <h2 class="device-name">{device.name}</h2>
          <span class="device-type">{deviceTypeLabel}</span>
        </div>
      </div>

      <!-- Badge de status -->
      <div class="status-badge" class:online={statusLevel === 'online'} class:warning={statusLevel === 'warning'} class:offline={statusLevel === 'offline'} role="status" aria-label="Estado: {statusLabel}">
        <span class="status-dot" aria-hidden="true"></span>
        {statusLabel}
      </div>
    </div>

    <!-- Métricas principais -->
    <div class="metrics-grid">
      <div class="metric">
        <span class="metric-icon" aria-hidden="true">🔑</span>
        <div class="metric-content">
          <span class="metric-label">Modo de Auth</span>
          <span class="metric-value auth-mode {authInfo.class}">{authInfo.label}</span>
        </div>
      </div>

      <div class="metric">
        <span class="metric-icon" aria-hidden="true">⏱</span>
        <div class="metric-content">
          <span class="metric-label">Última Actividade</span>
          <span class="metric-value">{lastSeenFormatted || 'Aguardar...'}</span>
        </div>
      </div>

      {#if uptimeSeconds > 0}
        <div class="metric">
          <span class="metric-icon" aria-hidden="true">⚡</span>
          <div class="metric-content">
            <span class="metric-label">Uptime</span>
            <span class="metric-value">{formatUptime(uptimeSeconds)}</span>
          </div>
        </div>
      {/if}

      {#if mqttSignalStrength !== null}
        <div class="metric">
          <span class="metric-icon" aria-hidden="true">📶</span>
          <div class="metric-content">
            <span class="metric-label">Sinal WiFi</span>
            <span class="metric-value">{formatSignal(mqttSignalStrength)}</span>
          </div>
        </div>
      {/if}

      {#if device.location}
        <div class="metric">
          <span class="metric-icon" aria-hidden="true">📍</span>
          <div class="metric-content">
            <span class="metric-label">Localização</span>
            <span class="metric-value">{device.location}</span>
          </div>
        </div>
      {/if}

      {#if device.firmware_version}
        <div class="metric">
          <span class="metric-icon" aria-hidden="true">💾</span>
          <div class="metric-content">
            <span class="metric-label">Firmware</span>
            <code class="metric-value firmware">{device.firmware_version}</code>
          </div>
        </div>
      {/if}
    </div>

    <!-- Aviso se device está em modo warning ou offline -->
    {#if statusLevel !== 'online'}
      <div class="status-alert" class:alert-warning={statusLevel === 'warning'} class:alert-offline={statusLevel === 'offline'} role="alert">
        {#if statusLevel === 'warning'}
          <span aria-hidden="true">⚠️</span>
          Sinal intermitente — último heartbeat há {heartbeatAge}s
        {:else}
          <span aria-hidden="true">🔴</span>
          Device offline — sem heartbeat há {heartbeatAge}s
        {/if}
      </div>
    {/if}

    <!-- ID do device (discreto) -->
    <p class="device-id">ID: <code>{device.id}</code></p>

  {:else}
    <!-- Estado vazio -->
    <div class="empty-state">
      <span class="empty-icon" aria-hidden="true">📟</span>
      <p>Nenhum device seleccionado</p>
    </div>
  {/if}
</div>

<style>
  .device-status {
    background: #ffffff;
    border-radius: 16px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    padding: 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
    width: 100%;
    max-width: 420px;
    border-left: 4px solid #d0d0d0;
    transition: border-color 0.3s;
  }

  .device-status.status-online  { border-left-color: #2e7d32; }
  .device-status.status-warning { border-left-color: #e65100; }
  .device-status.status-offline { border-left-color: #c62828; }

  /* Cabeçalho */
  .device-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
  }

  .device-identity {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .device-type-icon {
    font-size: 2rem;
    line-height: 1;
  }

  .device-titles {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
  }

  .device-name {
    font-size: 1.15rem;
    font-weight: 700;
    color: #1a1a2e;
    margin: 0;
  }

  .device-type {
    font-size: 0.8rem;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  /* Badge de status */
  .status-badge {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.3rem 0.75rem;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 700;
    white-space: nowrap;
  }

  .status-badge.online  { background: #e8f5e9; color: #2e7d32; }
  .status-badge.warning { background: #fff3e0; color: #e65100; }
  .status-badge.offline { background: #ffebee; color: #c62828; }

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: currentColor;
  }

  .status-badge.online .status-dot {
    animation: blink 2s ease-in-out infinite;
  }

  @keyframes blink {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.3; }
  }

  /* Grid de métricas */
  .metrics-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.75rem;
  }

  .metric {
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
    padding: 0.6rem 0.75rem;
    background: #f8f9fa;
    border-radius: 8px;
  }

  .metric-icon {
    font-size: 1.1rem;
    line-height: 1.4;
    flex-shrink: 0;
  }

  .metric-content {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
    min-width: 0;
  }

  .metric-label {
    font-size: 0.7rem;
    font-weight: 600;
    color: #999;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .metric-value {
    font-size: 0.85rem;
    color: #1a1a2e;
    font-weight: 500;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .auth-mode {
    font-weight: 600;
  }

  .mode-pin      { color: #1565c0; }
  .mode-card     { color: #4527a0; }
  .mode-combined { color: #2e7d32; }
  .mode-unknown  { color: #888; }

  .firmware {
    font-family: 'Courier New', monospace;
    font-size: 0.8rem;
    background: #e8e8e8;
    padding: 0.1rem 0.3rem;
    border-radius: 3px;
  }

  /* Alertas */
  .status-alert {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.6rem 0.8rem;
    border-radius: 8px;
    font-size: 0.82rem;
    font-weight: 500;
  }

  .alert-warning { background: #fff3e0; color: #bf360c; }
  .alert-offline { background: #ffebee; color: #b71c1c; }

  /* ID discreto */
  .device-id {
    font-size: 0.72rem;
    color: #bbb;
    margin: 0;
  }

  .device-id code {
    font-family: 'Courier New', monospace;
    background: #f0f0f0;
    padding: 0.1rem 0.3rem;
    border-radius: 3px;
  }

  /* Estado vazio */
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
    padding: 2rem;
    color: #bbb;
    text-align: center;
  }

  .empty-icon { font-size: 2.5rem; }
</style>
