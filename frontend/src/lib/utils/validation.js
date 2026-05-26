/**
 * utils/validation.js — Validação de PIN e UID de cartão NFC/RFID
 */

// ─── PIN ─────────────────────────────────────────────────────────────────────

/**
 * Valida o formato e comprimento de um PIN.
 *
 * @param {string} pin
 * @param {number} minLength — padrão 4
 * @param {number} maxLength — padrão 12
 * @returns {{ valid: boolean, message: string }}
 */
export function validatePin(pin, minLength = 4, maxLength = 12) {
  if (typeof pin !== 'string') {
    return { valid: false, message: 'PIN inválido.' };
  }

  if (pin.length < minLength) {
    return {
      valid: false,
      message: `O PIN deve ter pelo menos ${minLength} dígitos.`,
    };
  }

  if (pin.length > maxLength) {
    return {
      valid: false,
      message: `O PIN não pode exceder ${maxLength} dígitos.`,
    };
  }

  if (!/^\d+$/.test(pin)) {
    return {
      valid: false,
      message: 'O PIN deve conter apenas dígitos numéricos.',
    };
  }

  if (isSequentialPin(pin)) {
    return {
      valid: false,
      message: 'PIN demasiado simples. Evite sequências (ex: 1234, 9876).',
    };
  }

  if (isRepeatedPin(pin)) {
    return {
      valid: false,
      message: 'PIN demasiado simples. Evite repetições (ex: 1111, 2222).',
    };
  }

  return { valid: true, message: '' };
}

/**
 * Verifica se o PIN é uma sequência crescente ou decrescente.
 * Ex: "1234", "4567", "9876"
 *
 * @param {string} pin
 * @returns {boolean}
 */
export function isSequentialPin(pin) {
  if (pin.length < 4) return false;
  const digits = pin.split('').map(Number);

  // Verificar sequência crescente
  let ascending = true;
  let descending = true;

  for (let i = 1; i < digits.length; i++) {
    if (digits[i] !== digits[i - 1] + 1) ascending = false;
    if (digits[i] !== digits[i - 1] - 1) descending = false;
    if (!ascending && !descending) break;
  }

  return ascending || descending;
}

/**
 * Verifica se o PIN tem todos os dígitos iguais.
 * Ex: "1111", "9999"
 *
 * @param {string} pin
 * @returns {boolean}
 */
export function isRepeatedPin(pin) {
  return pin.split('').every(d => d === pin[0]);
}

/**
 * Calcula a força do PIN numa escala de 0-100.
 * Útil para feedback visual (não bloqueia submissão).
 *
 * @param {string} pin
 * @returns {{ score: number, label: 'weak' | 'fair' | 'good' | 'strong' }}
 */
export function pinStrength(pin) {
  if (!pin || pin.length < 4) return { score: 0, label: 'weak' };

  let score = 0;

  // Comprimento
  score += Math.min(pin.length * 8, 40); // até 40 pts por comprimento

  // Variedade de dígitos únicos
  const uniqueDigits = new Set(pin.split('')).size;
  score += uniqueDigits * 5; // até 50 pts

  // Penalização por sequências e repetições
  if (isSequentialPin(pin)) score -= 20;
  if (isRepeatedPin(pin))   score -= 30;

  score = Math.max(0, Math.min(100, score));

  const label = score >= 75 ? 'strong'
    : score >= 50 ? 'good'
    : score >= 25 ? 'fair'
    : 'weak';

  return { score, label };
}

// ─── Card UID ────────────────────────────────────────────────────────────────

/**
 * Valida o formato de um UID de cartão NFC/RFID.
 * Aceita 4, 7 ou 10 bytes em hex (8, 14 ou 20 caracteres).
 *
 * @param {string} uid
 * @returns {{ valid: boolean, message: string, byteLength: number | null }}
 */
export function validateCardUid(uid) {
  if (!uid || typeof uid !== 'string') {
    return { valid: false, message: 'UID inválido.', byteLength: null };
  }

  const clean = uid.replace(/[\s:-]/g, '').toUpperCase();

  if (!/^[0-9A-F]+$/.test(clean)) {
    return {
      valid: false,
      message: 'UID deve conter apenas caracteres hexadecimais (0-9, A-F).',
      byteLength: null,
    };
  }

  // Tamanhos válidos NFC: 4 bytes (8 hex), 7 bytes (14 hex), 10 bytes (20 hex)
  const VALID_LENGTHS = [8, 14, 20];
  if (!VALID_LENGTHS.includes(clean.length)) {
    return {
      valid: false,
      message: `Comprimento inválido (${clean.length} chars). Esperado: 8, 14 ou 20 caracteres hex.`,
      byteLength: null,
    };
  }

  return {
    valid: true,
    message: '',
    byteLength: clean.length / 2,
  };
}

/**
 * Normaliza um UID para formato canónico uppercase sem separadores.
 *
 * @param {string} uid
 * @returns {string}
 */
export function normalizeCardUid(uid) {
  if (!uid) return '';
  return uid.replace(/[\s:-]/g, '').toUpperCase();
}

// ─── Device ID ───────────────────────────────────────────────────────────────

/**
 * Valida um device ID (UUID v4 ou identificador alphanumérico).
 *
 * @param {string} deviceId
 * @returns {boolean}
 */
export function isValidDeviceId(deviceId) {
  if (!deviceId || typeof deviceId !== 'string') return false;

  // UUID v4
  const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
  if (uuidPattern.test(deviceId)) return true;

  // Identificador alfanumérico simples (ex: "DEV-001", "door_main")
  const alphanumPattern = /^[a-zA-Z0-9_-]{3,64}$/;
  return alphanumPattern.test(deviceId);
}
