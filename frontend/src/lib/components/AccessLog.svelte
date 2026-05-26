<script>
  import { onMount } from 'svelte';
  import { getAccessLogs } from '../services/api.js';

  // Props
  export let deviceId = '';     // Filtrar por device específico (opcional)
  export let maxRows = 50;      // Número máximo de entradas a mostrar
  export let autoRefresh = 30;  // Intervalo de refresh em segundos (0 = desactivado)

  // Estado
  let logs = [];
  let isLoading = false;
  let errorMessage = '';
  let lastRefresh = null;
  let refreshInterval;
  let filterType = 'all';       // 'all' | 'pin' | 'card' | 'success' | 'failure'
  let sortAsc = false;          // Ordenação: false = mais recente primeiro

  // Tipos de acesso mapeados para labels legíveis
  const ACCESS_TYPE_LABELS = {
    pin_valid:     { label: 'PIN Válido',    class: 'type-pin-valid' },
    pin_invalid:   { label: 'PIN Inválido',  class: 'type-pin-invalid' },
    card_read:     { label: 'Cartão Lido',   class: 'type-card' },
    card_unknown:  { label: 'Cartão Desconhecido', class: 'type-card-unknown' },
    pin_card:      { label: 'PIN + Cartão',  class: 'type-combined' },
    access_denied: { label: 'Acesso Negado', class: 'type-denied' },
  };

  // Logs filtrados e ordenados
  $: filteredLogs = logs
    .filter(log => {
      if (filterType === 'all') return true;
      if (filterType === 'pin')     return log.access_type?.startsWith('pin');
      if (filterType === 'card')    return log.access_type?.startsWith('card');
      if (filterType === 'success') return log.success === true;
      if (filterType === 'failure') return log.success === false;
      return true;
    })
    .sort((a, b) => {
      const diff = new Date(a.timestamp) - new Date(b.timestamp);
      return sortAsc ? diff : -diff;
    })
    .slice(0, maxRows);

  $: successCount = logs.filter(l => l.success).length;
  $: failureCount = logs.filter(l => !l.success).length;
  $: successRate = logs.length > 0
    ? Math.round((successCount / logs.length) * 100)
    : 0;

  function getAccessTypeInfo(type) {
    return ACCESS_TYPE_LABELS[type] ?? { label: type ?? 'Desconhecido', class: 'type-unknown' };
  }

  function formatTimestamp(ts) {
    if (!ts) return '—';
    const d = new Date(ts);
    return d.toLocaleString('pt-PT', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    });
  }

  function maskCardUid(uid) {
    if (!uid || uid.length <= 4) return uid ?? '—';
    return uid.slice(0, 2) + '••••' + uid.slice(-2);
  }

  async function loadLogs() {
    isLoading = true;
    errorMessage = '';
    try {
      // TODO: Integração com GET /api/access/logs?device_id=&limit=
      const data = await getAccessLogs({ deviceId, limit: maxRows });
      logs = data ?? [];
      lastRefresh = new Date();
    } catch (err) {
      errorMessage = 'Erro ao carregar histórico de acessos.';
      console.error('[AccessLog] Erro ao carregar logs:', err);
    } finally {
      isLoading = false;
    }
  }

  // Adicionar nova entrada em tempo real (chamado pelo componente pai via MQTT)
  export function appendLog(entry) {
    logs = [entry, ...logs].slice(0, maxRows * 2);
  }

  function toggleSort() {
    sortAsc = !sortAsc;
  }

  onMount(async () => {
    await loadLogs();

    if (autoRefresh > 0) {
      refreshInterval = setInterval(loadLogs, autoRefresh * 1000);
    }
  });

  import { onDestroy } from 'svelte';
  onDestroy(() => {
    if (refreshInterval) clearInterval(refreshInterval);
  });
</script>

<div class="access-log">
  <!-- Cabeçalho com estatísticas sumárias -->
  <div class="log-header">
    <div class="header-top">
      <h2 class="title">Access Log</h2>
      <button
        class="refresh-btn"
        on:click={loadLogs}
        disabled={isLoading}
        aria-label="Actualizar logs"
        title="Actualizar"
      >
        <svg class="refresh-icon" class:spinning={isLoading} viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </button>
    </div>

    <!-- Estatísticas -->
    <div class="stats-row">
      <div class="stat">
        <span class="stat-value">{logs.length}</span>
        <span class="stat-label">Total</span>
      </div>
      <div class="stat success">
        <span class="stat-value">{successCount}</span>
        <span class="stat-label">Sucesso</span>
      </div>
      <div class="stat failure">
        <span class="stat-value">{failureCount}</span>
        <span class="stat-label">Falha</span>
      </div>
      <div class="stat rate">
        <span class="stat-value">{successRate}%</span>
        <span class="stat-label">Taxa</span>
      </div>
    </div>

    <!-- Filtros -->
    <div class="filters" role="group" aria-label="Filtrar logs">
      {#each [
        { value: 'all',     label: 'Todos' },
        { value: 'pin',     label: 'PIN' },
        { value: 'card',    label: 'Cartão' },
        { value: 'success', label: 'Sucesso' },
        { value: 'failure', label: 'Falha' },
      ] as f}
        <button
          class="filter-btn"
          class:active={filterType === f.value}
          on:click={() => { filterType = f.value; }}
        >
          {f.label}
        </button>
      {/each}
    </div>
  </div>

  <!-- Tabela de logs -->
  {#if isLoading && logs.length === 0}
    <div class="loading-state">
      <span class="spinner" aria-hidden="true"></span>
      <p>A carregar histórico...</p>
    </div>
  {:else if errorMessage}
    <div class="error-state">
      <p class="error-msg" role="alert">{errorMessage}</p>
      <button class="retry-btn" on:click={loadLogs}>Tentar novamente</button>
    </div>
  {:else if filteredLogs.length === 0}
    <div class="empty-state">
      <p>Sem registos{filterType !== 'all' ? ' para este filtro' : ''}.</p>
    </div>
  {:else}
    <div class="table-wrapper" role="region" aria-label="Tabela de histórico de acessos">
      <table class="log-table">
        <thead>
          <tr>
            <th>
              <button class="sort-btn" on:click={toggleSort} aria-label="Ordenar por data">
                Timestamp {sortAsc ? '↑' : '↓'}
              </button>
            </th>
            <th>Tipo</th>
            <th>Estado</th>
            <th>Card UID</th>
            <th>Device</th>
          </tr>
        </thead>
        <tbody>
          {#each filteredLogs as log (log.id ?? log.timestamp)}
            <tr class:success-row={log.success} class:failure-row={!log.success}>
              <td class="timestamp-cell">
                <time datetime={log.timestamp}>{formatTimestamp(log.timestamp)}</time>
              </td>
              <td>
                {@const typeInfo = getAccessTypeInfo(log.access_type)}
                <span class="type-badge {typeInfo.class}">{typeInfo.label}</span>
              </td>
              <td>
                <span class="status-badge" class:status-success={log.success} class:status-failure={!log.success}>
                  {log.success ? 'Sucesso' : 'Falha'}
                </span>
              </td>
              <td class="uid-cell">
                <code>{maskCardUid(log.card_uid)}</code>
              </td>
              <td class="device-cell">
                <span class="device-label">{log.device_id ?? deviceId ?? '—'}</span>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>

    {#if lastRefresh}
      <p class="last-refresh">
        Actualizado: {lastRefresh.toLocaleTimeString('pt-PT')}
        {#if autoRefresh > 0}· Auto-refresh cada {autoRefresh}s{/if}
      </p>
    {/if}
  {/if}
</div>

<style>
  .access-log {
    background: #ffffff;
    border-radius: 16px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    overflow: hidden;
    width: 100%;
  }

  .log-header {
    padding: 1.25rem 1.5rem;
    border-bottom: 1px solid #f0f0f0;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .header-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .title {
    font-size: 1.2rem;
    font-weight: 700;
    color: #1a1a2e;
    margin: 0;
  }

  .refresh-btn {
    background: none;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 0.4rem;
    cursor: pointer;
    color: #666;
    transition: background 0.15s, color 0.15s;
    display: flex;
    align-items: center;
  }

  .refresh-btn:hover:not(:disabled) { background: #f5f5f5; color: #333; }
  .refresh-btn:disabled { opacity: 0.4; cursor: not-allowed; }

  .refresh-icon { width: 18px; height: 18px; }

  .refresh-icon.spinning {
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin { to { transform: rotate(360deg); } }

  /* Estatísticas */
  .stats-row {
    display: flex;
    gap: 0.5rem;
  }

  .stat {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 0.5rem;
    background: #f8f9fa;
    border-radius: 8px;
    gap: 0.1rem;
  }

  .stat.success { background: #e8f5e9; }
  .stat.failure { background: #ffebee; }
  .stat.rate    { background: #e3f2fd; }

  .stat-value {
    font-size: 1.1rem;
    font-weight: 700;
    color: #1a1a2e;
  }

  .stat.success .stat-value { color: #2e7d32; }
  .stat.failure .stat-value { color: #c62828; }
  .stat.rate    .stat-value { color: #1565c0; }

  .stat-label {
    font-size: 0.7rem;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  /* Filtros */
  .filters {
    display: flex;
    gap: 0.4rem;
    flex-wrap: wrap;
  }

  .filter-btn {
    padding: 0.3rem 0.7rem;
    font-size: 0.8rem;
    font-weight: 500;
    border: 1.5px solid #e0e0e0;
    border-radius: 20px;
    background: none;
    color: #666;
    cursor: pointer;
    transition: all 0.15s;
  }

  .filter-btn:hover { border-color: #1a1a2e; color: #1a1a2e; }

  .filter-btn.active {
    background: #1a1a2e;
    border-color: #1a1a2e;
    color: #fff;
  }

  /* Tabela */
  .table-wrapper {
    overflow-x: auto;
  }

  .log-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85rem;
  }

  .log-table thead {
    background: #f8f9fa;
    border-bottom: 2px solid #e8e8e8;
  }

  .log-table th {
    padding: 0.7rem 1rem;
    text-align: left;
    font-size: 0.75rem;
    font-weight: 700;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    white-space: nowrap;
  }

  .sort-btn {
    background: none;
    border: none;
    font-size: inherit;
    font-weight: inherit;
    color: inherit;
    letter-spacing: inherit;
    text-transform: inherit;
    cursor: pointer;
    padding: 0;
    transition: color 0.15s;
  }

  .sort-btn:hover { color: #1a1a2e; }

  .log-table tbody tr {
    border-bottom: 1px solid #f0f0f0;
    transition: background 0.1s;
  }

  .log-table tbody tr:hover { background: #fafafa; }
  .log-table tbody tr.success-row:hover { background: #f5fff5; }
  .log-table tbody tr.failure-row:hover { background: #fff5f5; }

  .log-table td {
    padding: 0.65rem 1rem;
    color: #333;
    white-space: nowrap;
  }

  .timestamp-cell { color: #666; font-size: 0.8rem; }

  /* Badges */
  .type-badge, .status-badge {
    display: inline-block;
    padding: 0.2rem 0.55rem;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
  }

  .type-pin-valid    { background: #e8f5e9; color: #2e7d32; }
  .type-pin-invalid  { background: #fff8e1; color: #e65100; }
  .type-card         { background: #e3f2fd; color: #1565c0; }
  .type-card-unknown { background: #fce4ec; color: #880e4f; }
  .type-combined     { background: #ede7f6; color: #4527a0; }
  .type-denied       { background: #ffebee; color: #c62828; }
  .type-unknown      { background: #f5f5f5; color: #777; }

  .status-success { background: #e8f5e9; color: #2e7d32; }
  .status-failure { background: #ffebee; color: #c62828; }

  .uid-cell code {
    font-family: 'Courier New', monospace;
    font-size: 0.8rem;
    background: #f0f0f0;
    padding: 0.1rem 0.3rem;
    border-radius: 3px;
    color: #444;
  }

  .device-label {
    font-size: 0.8rem;
    color: #777;
  }

  /* Estados */
  .loading-state, .error-state, .empty-state {
    padding: 3rem 1.5rem;
    text-align: center;
    color: #888;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.75rem;
  }

  .spinner {
    display: inline-block;
    width: 28px;
    height: 28px;
    border: 3px solid #e0e0e0;
    border-top-color: #1a1a2e;
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
  }

  .error-msg { color: #c62828; }

  .retry-btn {
    padding: 0.5rem 1.2rem;
    background: #1a1a2e;
    color: #fff;
    border: none;
    border-radius: 8px;
    font-size: 0.85rem;
    cursor: pointer;
  }

  .last-refresh {
    padding: 0.6rem 1.5rem;
    font-size: 0.75rem;
    color: #aaa;
    text-align: right;
    border-top: 1px solid #f5f5f5;
  }
</style>
