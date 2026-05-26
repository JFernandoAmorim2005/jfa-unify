/**
 * routes/api/access/+server.js — Proxy de acesso (SvelteKit server endpoint)
 *
 * Este endpoint corre no servidor Node.js (SSR), não no browser.
 * Actua como proxy entre o frontend e a API JFA_Remotes, adicionando:
 *   - Verificação HMAC-SHA256 do pedido do cliente
 *   - Injecção do API key server-side (não exposta ao browser)
 *   - Rate limiting básico por IP
 *   - Logging de pedidos
 *
 * Configuração necessária (.env):
 *   VITE_HMAC_SECRET     — segredo partilhado client ↔ server proxy
 *   JFA_API_BASE_URL     — URL da API backend (privada, sem VITE_ prefix)
 *   JFA_API_KEY          — API key do backend (nunca exposta ao browser)
 */

import { json, error } from '@sveltejs/kit';

// ─── Configuração ─────────────────────────────────────────────────────────────

const API_BASE   = process.env.JFA_API_BASE_URL ?? 'http://localhost:8080';
const API_KEY    = process.env.JFA_API_KEY ?? '';
const HMAC_SECRET = process.env.VITE_HMAC_SECRET ?? '';

// Rate limiting simples em memória (substituir por Redis em produção)
const rateLimitMap = new Map(); // ip → { count, resetAt }
const RATE_LIMIT_WINDOW_MS = 60_000;
const RATE_LIMIT_MAX = 20; // pedidos por minuto por IP

// ─── Rate limiting ────────────────────────────────────────────────────────────

function checkRateLimit(ip) {
  const now = Date.now();
  const entry = rateLimitMap.get(ip);

  if (!entry || now > entry.resetAt) {
    rateLimitMap.set(ip, { count: 1, resetAt: now + RATE_LIMIT_WINDOW_MS });
    return true;
  }

  if (entry.count >= RATE_LIMIT_MAX) {
    return false;
  }

  entry.count++;
  return true;
}

// ─── Verificação HMAC ────────────────────────────────────────────────────────

const encoder = new TextEncoder();

async function verifyRequestHmac(body, signature) {
  if (!HMAC_SECRET || !signature) return false;

  try {
    const keyMaterial = encoder.encode(HMAC_SECRET);
    const key = await crypto.subtle.importKey(
      'raw',
      keyMaterial,
      { name: 'HMAC', hash: 'SHA-256' },
      false,
      ['verify']
    );

    const data = encoder.encode(body);
    const sigBytes = hexToBuffer(signature);
    return await crypto.subtle.verify('HMAC', key, sigBytes, data);
  } catch {
    return false;
  }
}

function hexToBuffer(hex) {
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < hex.length; i += 2) {
    bytes[i / 2] = parseInt(hex.slice(i, i + 2), 16);
  }
  return bytes.buffer;
}

// ─── POST /api/access (validate) ─────────────────────────────────────────────

/** @type {import('./$types').RequestHandler} */
export async function POST({ request, getClientAddress }) {
  const ip = getClientAddress();

  // Rate limiting
  if (!checkRateLimit(ip)) {
    throw error(429, 'Too Many Requests — aguarde 1 minuto.');
  }

  // Leitura e verificação do corpo
  const rawBody = await request.text();
  const signature = request.headers.get('x-signature') ?? '';

  if (HMAC_SECRET) {
    const valid = await verifyRequestHmac(rawBody, signature);
    if (!valid) {
      throw error(401, 'Assinatura HMAC inválida.');
    }
  }

  // Parse do payload
  let payload;
  try {
    payload = JSON.parse(rawBody);
  } catch {
    throw error(400, 'Payload JSON inválido.');
  }

  // Verificação de replay (timestamp não pode ser mais de 5min antigo)
  const now = Date.now();
  if (payload.timestamp && Math.abs(now - payload.timestamp) > 5 * 60 * 1000) {
    throw error(400, 'Timestamp inválido — possível replay attack.');
  }

  // Reencaminhar para a API backend com a API key server-side
  let apiResponse;
  try {
    apiResponse = await fetch(`${API_BASE}/api/access/validate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${API_KEY}`,
        'X-Forwarded-For': ip,
      },
      body: JSON.stringify({
        pin: payload.pin,
        card_uid: payload.card_uid,
        device_id: payload.device_id,
        timestamp: payload.timestamp,
      }),
    });
  } catch (err) {
    console.error('[/api/access] Erro ao contactar backend:', err);
    throw error(502, 'Erro ao contactar o servidor de controlo.');
  }

  const data = await apiResponse.json();

  if (!apiResponse.ok) {
    throw error(apiResponse.status, data.message ?? data.error ?? 'Erro do servidor.');
  }

  return json(data);
}
