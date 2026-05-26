/**
 * services/mqtt.js — WebSocket MQTT wrapper para SvelteKit
 *
 * Utiliza mqtt.js (https://github.com/mqttjs/MQTT.js) via WebSocket.
 * O broker é configurado via VITE_MQTT_WS_URL (ex: ws://localhost:9001 ou wss://broker/mqtt).
 *
 * Instalação: npm install mqtt
 *
 * TODO: Adicionar autenticação MQTT (username/password ou JWT via CONNECT)
 * TODO: Implementar reconexão com backoff exponencial personalizado
 */

// Importação lazy para evitar erros SSR (mqtt.js é client-only)
let mqttLib = null;

async function getMqttLib() {
  if (mqttLib) return mqttLib;
  // Importação dinâmica — só executa no browser
  mqttLib = await import('mqtt');
  return mqttLib;
}

// ─── Configuração ────────────────────────────────────────────────────────────

const BROKER_URL = import.meta.env.VITE_MQTT_WS_URL ?? 'ws://localhost:9001';
const CLIENT_ID  = `jfa-web-${Math.random().toString(36).slice(2, 10)}`;

const DEFAULT_OPTIONS = {
  clientId: CLIENT_ID,
  clean: true,
  reconnectPeriod: 3000,     // ms entre reconexões automáticas
  connectTimeout: 10000,     // ms timeout de ligação inicial
  keepalive: 30,             // segundos
  // TODO: username e password via env vars se o broker exigir autenticação
  // username: import.meta.env.VITE_MQTT_USER,
  // password: import.meta.env.VITE_MQTT_PASS,
};

// ─── Estado interno ──────────────────────────────────────────────────────────

/** @type {import('mqtt').MqttClient | null} */
let client = null;

/** @type {Map<string, Set<Function>>} */
const topicHandlers = new Map();

/** @type {Set<Function>} */
const connectionListeners = new Set();

let _status = 'disconnected'; // 'connecting' | 'connected' | 'disconnected' | 'error'

// ─── Ligação ──────────────────────────────────────────────────────────────────

/**
 * Estabelece ligação ao broker MQTT via WebSocket.
 * Idempotente — se já ligado, retorna silenciosamente.
 *
 * @returns {Promise<void>}
 */
export async function connect() {
  if (client && _status === 'connected') return;
  if (_status === 'connecting') return;

  _status = 'connecting';
  notifyConnectionListeners('connecting');

  const mqtt = await getMqttLib();

  client = mqtt.connect(BROKER_URL, DEFAULT_OPTIONS);

  client.on('connect', () => {
    _status = 'connected';
    notifyConnectionListeners('connected');

    // Re-subscrever todos os tópicos registados após reconexão
    for (const [topic] of topicHandlers) {
      client.subscribe(topic, { qos: 1 }, (err) => {
        if (err) console.error(`[MQTT] Erro ao subscrever ${topic}:`, err);
      });
    }
  });

  client.on('message', (topic, payload) => {
    const message = payload.toString();
    dispatchMessage(topic, message);
  });

  client.on('disconnect', () => {
    _status = 'disconnected';
    notifyConnectionListeners('disconnected');
  });

  client.on('offline', () => {
    _status = 'disconnected';
    notifyConnectionListeners('disconnected');
  });

  client.on('error', (err) => {
    _status = 'error';
    notifyConnectionListeners('error');
    console.error('[MQTT] Erro de ligação:', err);
  });
}

/**
 * Termina a ligação ao broker.
 */
export function disconnect() {
  if (!client) return;
  client.end(true);
  client = null;
  _status = 'disconnected';
  notifyConnectionListeners('disconnected');
}

// ─── Pub/Sub ──────────────────────────────────────────────────────────────────

/**
 * Subscreve um tópico MQTT.
 * Suporta wildcards MQTT (+, #).
 *
 * @param {string} topic — ex: 'devices/+/card', 'devices/abc123/heartbeat'
 * @param {(message: string, topic: string) => void} handler
 * @param {{ qos?: 0|1|2 }} options
 */
export function subscribe(topic, handler, options = { qos: 1 }) {
  if (!topicHandlers.has(topic)) {
    topicHandlers.set(topic, new Set());
  }
  topicHandlers.get(topic).add(handler);

  if (client && _status === 'connected') {
    client.subscribe(topic, options, (err) => {
      if (err) console.error(`[MQTT] Erro ao subscrever ${topic}:`, err);
    });
  }
  // Se não ligado, a subscrição será feita quando a ligação for estabelecida
}

/**
 * Cancela a subscrição de um handler específico.
 * Se não restar nenhum handler para o tópico, cancela a subscrição MQTT.
 *
 * @param {string} topic
 * @param {Function} handler
 */
export function unsubscribe(topic, handler) {
  const handlers = topicHandlers.get(topic);
  if (!handlers) return;

  handlers.delete(handler);

  if (handlers.size === 0) {
    topicHandlers.delete(topic);
    if (client && _status === 'connected') {
      client.unsubscribe(topic);
    }
  }
}

/**
 * Publica uma mensagem num tópico MQTT.
 *
 * @param {string} topic
 * @param {string | object} payload — objecto será serializado para JSON
 * @param {{ qos?: 0|1|2, retain?: boolean }} options
 */
export function publish(topic, payload, options = { qos: 1, retain: false }) {
  if (!client || _status !== 'connected') {
    console.warn(`[MQTT] Não ligado — mensagem descartada para ${topic}`);
    return;
  }

  const message = typeof payload === 'object' ? JSON.stringify(payload) : String(payload);
  client.publish(topic, message, options);
}

// ─── Listeners de estado de ligação ──────────────────────────────────────────

/**
 * Regista um callback para mudanças de estado de ligação.
 *
 * @param {(status: 'connecting'|'connected'|'disconnected'|'error') => void} listener
 * @returns {() => void} — função para remover o listener
 */
export function onConnectionChange(listener) {
  connectionListeners.add(listener);
  // Emite o estado actual imediatamente
  listener(_status);
  return () => connectionListeners.delete(listener);
}

/**
 * Retorna o estado actual da ligação.
 *
 * @returns {'connecting'|'connected'|'disconnected'|'error'}
 */
export function getStatus() {
  return _status;
}

// ─── Helpers internos ────────────────────────────────────────────────────────

function notifyConnectionListeners(status) {
  for (const listener of connectionListeners) {
    try { listener(status); } catch (err) {
      console.error('[MQTT] Erro em connection listener:', err);
    }
  }
}

/**
 * Despacha mensagem recebida para os handlers registados.
 * Suporta wildcards simples (+) e multi-nível (#).
 *
 * @param {string} receivedTopic
 * @param {string} message
 */
function dispatchMessage(receivedTopic, message) {
  for (const [pattern, handlers] of topicHandlers) {
    if (topicMatches(pattern, receivedTopic)) {
      for (const handler of handlers) {
        try {
          handler(message, receivedTopic);
        } catch (err) {
          console.error(`[MQTT] Erro em handler para ${receivedTopic}:`, err);
        }
      }
    }
  }
}

/**
 * Verifica se um tópico MQTT corresponde a um padrão com wildcards.
 *
 * @param {string} pattern — ex: 'devices/+/card', 'devices/#'
 * @param {string} topic   — ex: 'devices/abc/card'
 * @returns {boolean}
 */
function topicMatches(pattern, topic) {
  if (pattern === topic) return true;

  // Converter padrão MQTT em regex
  const regexStr = pattern
    .replace(/[.+?^${}()|[\]\\]/g, (c) => c === '+' ? '[^/]+' : `\\${c}`)
    .replace(/#$/, '.*')
    .replace(/#/, '(?:[^/]*/)*');

  try {
    return new RegExp(`^${regexStr}$`).test(topic);
  } catch {
    return false;
  }
}

// ─── Instância exportada (conveniente para uso em componentes) ────────────────

/**
 * Objecto cliente MQTT com interface simplificada.
 * Alternativa ao uso das funções individuais.
 *
 * Exemplo de uso:
 *   import { mqttClient } from '$lib/services/mqtt.js';
 *   await mqttClient.connect();
 *   mqttClient.subscribe('devices/+/card', handler);
 */
export const mqttClient = {
  connect,
  disconnect,
  subscribe,
  unsubscribe,
  publish,
  onConnectionChange,
  get status() { return getStatus(); },
};
