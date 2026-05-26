/**
 * services/api.js — Cliente HTTP para a API JFA_Remotes
 *
 * Todos os pedidos são assinados com HMAC-SHA256.
 * O token de autenticação JWT é lido da store auth.js.
 *
 * Endpoints base (configurados via VITE_API_BASE_URL):
 *   POST /api/access/validate   — validar PIN ou cartão
 *   GET  /api/access/logs       — histórico de acessos
 *   GET  /api/devices           — listar devices
 *   GET  /api/devices/:id       — detalhe do device
 */

import { get } from 'svelte/store';
import { authToken } from '../stores/auth.js';
import { signHmac, buildSignedPayload } from '../utils/crypto.js';

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';

// ─── Core fetch ──────────────────────────────────────────────────────────────

/**
 * Executa um fetch autenticado com HMAC-SHA256 e JWT Bearer.
 *
 * @param {string} path — caminho relativo, ex: '/api/access/validate'
 * @param {RequestInit & { json?: object }} options
 * @returns {Promise<any>} — corpo JSON da resposta
 * @throws {ApiError}
 */
export async function fetchWithAuth(path, options = {}) {
  const token = get(authToken);
  const headers = new Headers(options.headers ?? {});

  // Content-Type para pedidos JSON
  if (options.json) {
    headers.set('Content-Type', 'application/json');
  }

  // Bearer JWT
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  // Assinatura HMAC-SHA256 do corpo (se aplicável)
  let body = options.body;
  if (options.json) {
    const { payload, canonical } = buildSignedPayload(options.json);
    const signature = await signHmac(canonical);

    if (signature) {
      headers.set('X-Signature', signature);
      headers.set('X-Timestamp', String(payload.timestamp));
      headers.set('X-Nonce', payload.nonce);
    }

    body = JSON.stringify(options.json);
  }

  const url = `${BASE_URL}${path}`;

  let response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
      body,
    });
  } catch (err) {
    throw new ApiError(0, 'Erro de rede — verifique a ligação.', err);
  }

  if (!response.ok) {
    let detail = '';
    try {
      const errorBody = await response.json();
      detail = errorBody.message ?? errorBody.error ?? JSON.stringify(errorBody);
    } catch {
      detail = await response.text().catch(() => '');
    }
    throw new ApiError(response.status, detail || `HTTP ${response.status}`);
  }

  // Resposta vazia (204 No Content)
  if (response.status === 204) return null;

  return response.json();
}

// ─── Access ───────────────────────────────────────────────────────────────────

/**
 * Valida acesso por PIN, cartão, ou ambos.
 *
 * @param {{ pin?: string, card_uid?: string, device_id: string, timestamp?: number }} params
 * @returns {Promise<AccessValidationResult>}
 *
 * AccessValidationResult:
 * {
 *   allowed: boolean,
 *   reason: string,
 *   session_token?: string,
 *   log_id: string,
 * }
 */
export async function validateAccess({ pin, card_uid, device_id, timestamp }) {
  return fetchWithAuth('/api/access/validate', {
    method: 'POST',
    json: {
      pin: pin ?? null,
      card_uid: card_uid ?? null,
      device_id,
      timestamp: timestamp ?? Date.now(),
    },
  });
}

/**
 * Obtém o histórico de acessos.
 *
 * @param {{ deviceId?: string, limit?: number, offset?: number, since?: number }} params
 * @returns {Promise<AccessLogEntry[]>}
 *
 * AccessLogEntry:
 * {
 *   id: string,
 *   device_id: string,
 *   access_type: string,
 *   card_uid: string | null,
 *   success: boolean,
 *   timestamp: string (ISO 8601),
 *   metadata?: object,
 * }
 */
export async function getAccessLogs({ deviceId, limit = 50, offset = 0, since } = {}) {
  const params = new URLSearchParams();
  if (deviceId) params.set('device_id', deviceId);
  if (limit)    params.set('limit', String(limit));
  if (offset)   params.set('offset', String(offset));
  if (since)    params.set('since', String(since));

  const query = params.toString() ? `?${params}` : '';
  return fetchWithAuth(`/api/access/logs${query}`);
}

// ─── Devices ──────────────────────────────────────────────────────────────────

/**
 * Lista todos os devices acessíveis ao utilizador autenticado.
 *
 * @returns {Promise<Device[]>}
 *
 * Device:
 * {
 *   id: string,
 *   name: string,
 *   type: 'door' | 'gate' | 'locker' | 'generic',
 *   auth_mode: 'pin' | 'card' | 'pin_card' | 'card_pin',
 *   location: string,
 *   firmware_version: string,
 *   online: boolean,
 *   last_seen: string (ISO 8601),
 * }
 */
export async function listDevices() {
  return fetchWithAuth('/api/devices');
}

/**
 * Obtém o detalhe de um device específico.
 *
 * @param {string} deviceId
 * @returns {Promise<Device>}
 */
export async function getDevice(deviceId) {
  return fetchWithAuth(`/api/devices/${encodeURIComponent(deviceId)}`);
}

// ─── Erro tipado ──────────────────────────────────────────────────────────────

export class ApiError extends Error {
  /**
   * @param {number} status — HTTP status code (0 = erro de rede)
   * @param {string} message
   * @param {unknown} [cause]
   */
  constructor(status, message, cause) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.cause = cause;
  }

  get isNetworkError() { return this.status === 0; }
  get isUnauthorized() { return this.status === 401; }
  get isForbidden()    { return this.status === 403; }
  get isNotFound()     { return this.status === 404; }
  get isServerError()  { return this.status >= 500; }
}
