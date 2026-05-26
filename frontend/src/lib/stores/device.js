/**
 * stores/device.js — Estado global dos devices
 *
 * Contém a lista de devices, o device activo seleccionado,
 * e o estado de online/offline recebido via MQTT heartbeats.
 */

import { writable, derived, get } from 'svelte/store';

// ─── Stores base ─────────────────────────────────────────────────────────────

/**
 * Lista de todos os devices carregados da API.
 *
 * @type {import('svelte/store').Writable<Device[]>}
 */
export const devices = writable([]);

/**
 * ID do device actualmente seleccionado no dashboard.
 *
 * @type {import('svelte/store').Writable<string | null>}
 */
export const selectedDeviceId = writable(null);

/**
 * Map de estado de conectividade por device ID.
 * Actualizado por heartbeats MQTT.
 *
 * @type {import('svelte/store').Writable<Map<string, DeviceOnlineState>>}
 */
export const deviceOnlineState = writable(new Map());

// ─── Stores derivados ────────────────────────────────────────────────────────

/**
 * Device actualmente seleccionado, com estado de online merged.
 *
 * @type {import('svelte/store').Readable<DeviceWithState | null>}
 */
export const selectedDevice = derived(
  [devices, selectedDeviceId, deviceOnlineState],
  ([$devices, $selectedId, $onlineState]) => {
    if (!$selectedId) return null;
    const device = $devices.find(d => d.id === $selectedId);
    if (!device) return null;

    const onlineInfo = $onlineState.get($selectedId);
    return {
      ...device,
      online: onlineInfo?.online ?? false,
      last_seen: onlineInfo?.last_seen ?? device.last_seen,
      uptime_seconds: onlineInfo?.uptime_seconds ?? 0,
      rssi: onlineInfo?.rssi ?? null,
    };
  }
);

/**
 * Lista de devices com estado de online merged.
 *
 * @type {import('svelte/store').Readable<DeviceWithState[]>}
 */
export const devicesWithState = derived(
  [devices, deviceOnlineState],
  ([$devices, $onlineState]) => $devices.map(device => {
    const onlineInfo = $onlineState.get(device.id);
    return {
      ...device,
      online: onlineInfo?.online ?? false,
      last_seen: onlineInfo?.last_seen ?? device.last_seen,
    };
  })
);

/**
 * Contagem de devices online/offline.
 *
 * @type {import('svelte/store').Readable<{ online: number, offline: number, total: number }>}
 */
export const deviceCounts = derived(devicesWithState, ($devices) => ({
  total:   $devices.length,
  online:  $devices.filter(d => d.online).length,
  offline: $devices.filter(d => !d.online).length,
}));

// ─── Acções ──────────────────────────────────────────────────────────────────

/**
 * Carrega a lista de devices (normalmente chamado após login).
 * Não faz o fetch — recebe os dados já obtidos via api.js.
 *
 * @param {Device[]} list
 */
export function setDevices(list) {
  devices.set(list ?? []);
  // Seleccionar o primeiro device por defeito se nenhum estiver seleccionado
  if (!get(selectedDeviceId) && list?.length > 0) {
    selectedDeviceId.set(list[0].id);
  }
}

/**
 * Selecciona um device por ID.
 *
 * @param {string} deviceId
 */
export function selectDevice(deviceId) {
  selectedDeviceId.set(deviceId);
}

/**
 * Actualiza o estado de online de um device (chamado por heartbeat MQTT).
 *
 * @param {string} deviceId
 * @param {DeviceOnlineState} state
 */
export function updateDeviceOnlineState(deviceId, state) {
  deviceOnlineState.update(map => {
    const newMap = new Map(map);
    newMap.set(deviceId, {
      ...newMap.get(deviceId),
      ...state,
      last_seen: state.last_seen ?? Date.now(),
    });
    return newMap;
  });
}

/**
 * Marca todos os devices como offline (ex: quando a ligação MQTT cai).
 */
export function markAllDevicesOffline() {
  deviceOnlineState.update(map => {
    const newMap = new Map(map);
    for (const [id, state] of newMap) {
      newMap.set(id, { ...state, online: false });
    }
    return newMap;
  });
}

/**
 * Adiciona ou actualiza um device na lista.
 *
 * @param {Device} device
 */
export function upsertDevice(device) {
  devices.update(list => {
    const idx = list.findIndex(d => d.id === device.id);
    if (idx >= 0) {
      const updated = [...list];
      updated[idx] = { ...list[idx], ...device };
      return updated;
    }
    return [...list, device];
  });
}

// ─── Tipos (JSDoc) ────────────────────────────────────────────────────────────

/**
 * @typedef {Object} Device
 * @property {string} id
 * @property {string} name
 * @property {'door'|'gate'|'locker'|'generic'} type
 * @property {'pin'|'card'|'pin_card'|'card_pin'} auth_mode
 * @property {string} [location]
 * @property {string} [firmware_version]
 * @property {boolean} [online]
 * @property {string} [last_seen] — ISO 8601
 */

/**
 * @typedef {Object} DeviceOnlineState
 * @property {boolean} online
 * @property {number} [last_seen] — unix ms
 * @property {number} [uptime_seconds]
 * @property {number} [rssi] — dBm
 */

/**
 * @typedef {Device & DeviceOnlineState} DeviceWithState
 */
