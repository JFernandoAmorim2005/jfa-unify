/**
 * stores/auth.js — Store de autenticação
 *
 * Persiste o JWT token em sessionStorage (tab) ou localStorage (opção keepAlive).
 * Nunca persiste a password ou o PIN em memória após autenticação.
 */

import { writable, derived } from 'svelte/store';

const STORAGE_KEY = 'jfa_auth_token';
const SESSION_KEY = 'jfa_auth_session';

// ─── Helpers de storage ───────────────────────────────────────────────────────

function readStoredToken() {
  if (typeof window === 'undefined') return null;
  // Sessão tem prioridade sobre localStorage
  return sessionStorage.getItem(STORAGE_KEY)
    ?? localStorage.getItem(STORAGE_KEY)
    ?? null;
}

function persistToken(token, keepAlive = false) {
  if (typeof window === 'undefined') return;
  if (!token) {
    sessionStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(STORAGE_KEY);
    return;
  }
  if (keepAlive) {
    localStorage.setItem(STORAGE_KEY, token);
  } else {
    sessionStorage.setItem(STORAGE_KEY, token);
  }
}

// ─── Stores ──────────────────────────────────────────────────────────────────

/** @type {import('svelte/store').Writable<string | null>} */
export const authToken = writable(readStoredToken());

/**
 * Payload descodificado do JWT (sem verificação de assinatura — apenas leitura client-side).
 * A verificação real é feita pelo servidor em cada pedido.
 *
 * @type {import('svelte/store').Readable<JwtPayload | null>}
 */
export const authUser = derived(authToken, ($token) => {
  if (!$token) return null;
  try {
    const parts = $token.split('.');
    if (parts.length !== 3) return null;
    const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));
    return payload;
  } catch {
    return null;
  }
});

/**
 * Verdadeiro se o utilizador está autenticado e o token não expirou.
 *
 * @type {import('svelte/store').Readable<boolean>}
 */
export const isAuthenticated = derived(authUser, ($user) => {
  if (!$user) return false;
  if ($user.exp && Date.now() / 1000 > $user.exp) return false;
  return true;
});

// ─── Acções ──────────────────────────────────────────────────────────────────

/**
 * Define o token JWT após autenticação bem-sucedida.
 *
 * @param {string} token
 * @param {boolean} keepAlive — se true, persiste em localStorage
 */
export function setAuthToken(token, keepAlive = false) {
  authToken.set(token);
  persistToken(token, keepAlive);
}

/**
 * Limpa o token e termina a sessão.
 */
export function clearAuth() {
  authToken.set(null);
  persistToken(null);
}

/**
 * @typedef {Object} JwtPayload
 * @property {string} sub — user ID
 * @property {string} [email]
 * @property {string[]} [roles]
 * @property {number} [exp] — unix timestamp de expiração
 * @property {number} [iat] — unix timestamp de emissão
 */
