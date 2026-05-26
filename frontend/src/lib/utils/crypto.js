/**
 * utils/crypto.js — HMAC-SHA256 client-side via Web Crypto API
 *
 * A chave secreta é lida de VITE_HMAC_SECRET (variável de ambiente de build).
 * ATENÇÃO: Em produção, o HMAC client-side serve apenas para autenticidade de
 * request (anti-replay + integridade). A validação final é sempre feita no
 * servidor com a chave secreta real.
 *
 * TODO: Considerar migrar assinatura para endpoint proxy (/api/access/+server.js)
 *       para que a chave nunca seja exposta ao browser.
 */

const ENCODER = new TextEncoder();

/**
 * Obtém a chave HMAC-SHA256 a partir da variável de ambiente.
 * A chave é derivada uma vez e reutilizada via WeakRef/cache simples.
 *
 * @returns {Promise<CryptoKey>}
 */
let _cachedKey = null;

async function getHmacKey() {
  if (_cachedKey) return _cachedKey;

  // Em SvelteKit, variáveis VITE_* são substituídas em build-time
  const secret = import.meta.env.VITE_HMAC_SECRET ?? '';

  if (!secret) {
    console.warn('[crypto] VITE_HMAC_SECRET não definido — assinatura HMAC desactivada');
    return null;
  }

  const keyMaterial = ENCODER.encode(secret);

  _cachedKey = await crypto.subtle.importKey(
    'raw',
    keyMaterial,
    { name: 'HMAC', hash: 'SHA-256' },
    false,           // não exportável
    ['sign', 'verify']
  );

  return _cachedKey;
}

/**
 * Assina uma string com HMAC-SHA256.
 * Retorna a assinatura em hexadecimal (lowercase).
 *
 * @param {string} message — texto a assinar
 * @returns {Promise<string>} — hex da assinatura, ou '' se VITE_HMAC_SECRET não definido
 */
export async function signHmac(message) {
  const key = await getHmacKey();
  if (!key) return '';

  const data = ENCODER.encode(message);
  const signatureBuffer = await crypto.subtle.sign('HMAC', key, data);
  return bufferToHex(signatureBuffer);
}

/**
 * Verifica uma assinatura HMAC-SHA256.
 *
 * @param {string} message — texto original
 * @param {string} hexSignature — assinatura hex a verificar
 * @returns {Promise<boolean>}
 */
export async function verifyHmac(message, hexSignature) {
  const key = await getHmacKey();
  if (!key) return false;

  try {
    const data = ENCODER.encode(message);
    const signatureBuffer = hexToBuffer(hexSignature);
    return await crypto.subtle.verify('HMAC', key, signatureBuffer, data);
  } catch {
    return false;
  }
}

/**
 * Gera um nonce aleatório de 16 bytes em hexadecimal.
 * Útil para anti-replay em payloads HMAC.
 *
 * @returns {string}
 */
export function generateNonce() {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return bufferToHex(bytes.buffer);
}

/**
 * Constrói o payload canónico para assinar, incluindo nonce e timestamp.
 * O servidor deve replicar esta construção para verificar.
 *
 * @param {object} data — campos do payload
 * @returns {{ payload: object, canonical: string }}
 */
export function buildSignedPayload(data) {
  const nonce = generateNonce();
  const timestamp = Date.now();
  const payload = { ...data, nonce, timestamp };

  // Canonical string: JSON com chaves ordenadas (determinístico)
  const canonical = JSON.stringify(payload, Object.keys(payload).sort());
  return { payload, canonical };
}

// ─── Helpers internos ────────────────────────────────────────────────────────

function bufferToHex(buffer) {
  return Array.from(new Uint8Array(buffer))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
}

function hexToBuffer(hex) {
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < hex.length; i += 2) {
    bytes[i / 2] = parseInt(hex.slice(i, i + 2), 16);
  }
  return bytes.buffer;
}
