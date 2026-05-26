<script>
  import { createEventDispatcher } from 'svelte';
  import { signHmac } from '../utils/crypto.js';
  import { validatePin } from '../utils/validation.js';

  // Props
  export let deviceId = '';
  export let minLength = 4;
  export let maxLength = 12;

  const dispatch = createEventDispatcher();

  let pin = '';
  let errorMessage = '';
  let isLoading = false;
  let shakePin = false;

  // Indicador visual: dots preenchidos + slots vazios
  $: filledSlots = Array(pin.length).fill(true);
  $: emptySlots = Array(Math.max(minLength - pin.length, 0)).fill(false);

  function handleDigit(digit) {
    if (pin.length >= maxLength) return;
    pin += String(digit);
    errorMessage = '';
  }

  function handleDelete() {
    pin = pin.slice(0, -1);
    errorMessage = '';
  }

  function handleClear() {
    pin = '';
    errorMessage = '';
  }

  function triggerShake() {
    shakePin = true;
    setTimeout(() => { shakePin = false; }, 500);
  }

  async function handleSubmit() {
    const validation = validatePin(pin, minLength, maxLength);
    if (!validation.valid) {
      errorMessage = validation.message;
      triggerShake();
      return;
    }

    isLoading = true;
    errorMessage = '';

    try {
      const timestamp = Date.now();
      // Payload para HMAC-SHA256 signing
      const payload = { pin, device_id: deviceId, timestamp };
      const signature = await signHmac(JSON.stringify(payload));

      // TODO: Integração com POST /api/access/validate
      // O componente pai recebe o evento e executa o fetch via api.js
      dispatch('submit', { pin, device_id: deviceId, timestamp, signature });
    } catch (err) {
      errorMessage = 'Erro ao processar PIN. Tente novamente.';
      triggerShake();
    } finally {
      isLoading = false;
      pin = '';
    }
  }

  // Suporte a teclado físico
  function handleKeydown(event) {
    if (isLoading) return;
    if (event.key >= '0' && event.key <= '9') {
      handleDigit(event.key);
    } else if (event.key === 'Backspace') {
      handleDelete();
    } else if (event.key === 'Enter') {
      handleSubmit();
    } else if (event.key === 'Escape') {
      handleClear();
      dispatch('cancel');
    }
  }

  // Vibração em dispositivos móveis ao pressionar botão
  function vibrate() {
    if (typeof navigator !== 'undefined' && navigator.vibrate) {
      navigator.vibrate(30);
    }
  }

  function onDigitClick(digit) {
    vibrate();
    handleDigit(digit);
  }

  function onDeleteClick() {
    vibrate();
    handleDelete();
  }
</script>

<svelte:window on:keydown={handleKeydown} />

<div class="pin-pad-overlay" on:click|self={() => dispatch('cancel')} role="dialog" aria-modal="true" aria-label="Entrada de PIN">
  <div class="pin-pad-modal">
    <button class="close-btn" on:click={() => dispatch('cancel')} aria-label="Fechar">✕</button>

    <h2 class="title">Enter PIN</h2>
    <p class="subtitle">Introduza o seu código de acesso</p>

    <!-- Indicador visual de PIN -->
    <div class="pin-display" class:shake={shakePin} aria-live="polite" aria-label="{pin.length} dígitos inseridos">
      {#each filledSlots as _}
        <span class="dot filled" aria-hidden="true">●</span>
      {/each}
      {#each emptySlots as _}
        <span class="dot empty" aria-hidden="true">○</span>
      {/each}
    </div>

    <!-- Grid de botões numéricos -->
    <div class="buttons" role="group" aria-label="Teclado numérico">
      {#each [1, 2, 3, 4, 5, 6, 7, 8, 9] as digit}
        <button
          class="num-btn"
          on:click={() => onDigitClick(digit)}
          disabled={isLoading}
          aria-label="Dígito {digit}"
        >
          {digit}
        </button>
      {/each}

      <button
        class="num-btn action-btn"
        on:click={onDeleteClick}
        disabled={isLoading || pin.length === 0}
        aria-label="Apagar último dígito"
      >
        ⌫
      </button>

      <button
        class="num-btn"
        on:click={() => onDigitClick(0)}
        disabled={isLoading}
        aria-label="Dígito 0"
      >
        0
      </button>

      <button
        class="num-btn action-btn clear-btn"
        on:click={handleClear}
        disabled={isLoading || pin.length === 0}
        aria-label="Limpar PIN"
      >
        ✕
      </button>
    </div>

    <!-- Botão de submissão -->
    <button
      class="submit-btn"
      disabled={pin.length < minLength || isLoading}
      on:click={handleSubmit}
      aria-busy={isLoading}
    >
      {#if isLoading}
        <span class="spinner" aria-hidden="true"></span>
        Validating...
      {:else}
        SUBMIT
      {/if}
    </button>

    {#if errorMessage}
      <p class="error-msg" role="alert">{errorMessage}</p>
    {/if}

    <p class="hint">{pin.length}/{maxLength} dígitos • mínimo {minLength}</p>
  </div>
</div>

<style>
  .pin-pad-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.55);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    backdrop-filter: blur(4px);
    padding: 1rem;
  }

  .pin-pad-modal {
    position: relative;
    display: flex;
    flex-direction: column;
    gap: 1rem;
    padding: 2rem 1.75rem;
    background: #ffffff;
    border-radius: 16px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.25);
    max-width: 340px;
    width: 100%;
    animation: slideUp 0.2s ease-out;
  }

  @keyframes slideUp {
    from { transform: translateY(20px); opacity: 0; }
    to   { transform: translateY(0);    opacity: 1; }
  }

  .close-btn {
    position: absolute;
    top: 0.75rem;
    right: 0.75rem;
    background: none;
    border: none;
    font-size: 1rem;
    color: #999;
    cursor: pointer;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    transition: background 0.15s;
  }

  .close-btn:hover {
    background: #f0f0f0;
    color: #333;
  }

  .title {
    font-size: 1.4rem;
    font-weight: 700;
    text-align: center;
    color: #1a1a2e;
    margin: 0;
  }

  .subtitle {
    font-size: 0.85rem;
    color: #666;
    text-align: center;
    margin: -0.5rem 0 0;
  }

  /* Indicador de dots */
  .pin-display {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 0.6rem;
    min-height: 3rem;
    transition: transform 0.1s;
  }

  .pin-display.shake {
    animation: shake 0.4s ease-in-out;
  }

  @keyframes shake {
    0%, 100% { transform: translateX(0); }
    20%       { transform: translateX(-8px); }
    40%       { transform: translateX(8px); }
    60%       { transform: translateX(-6px); }
    80%       { transform: translateX(6px); }
  }

  .dot {
    font-size: 1.6rem;
    line-height: 1;
    transition: transform 0.15s, color 0.15s;
  }

  .dot.filled {
    color: #1a1a2e;
    transform: scale(1.1);
  }

  .dot.empty {
    color: #d0d0d0;
  }

  /* Grid de botões */
  .buttons {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0.6rem;
  }

  .num-btn {
    padding: 1rem;
    font-size: 1.3rem;
    font-weight: 500;
    border: 1.5px solid #e8e8e8;
    border-radius: 10px;
    background: #f8f8f8;
    color: #1a1a2e;
    cursor: pointer;
    transition: background 0.12s, transform 0.08s, box-shadow 0.12s;
    user-select: none;
    -webkit-user-select: none;
  }

  .num-btn:hover:not(:disabled) {
    background: #ececec;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  }

  .num-btn:active:not(:disabled) {
    transform: scale(0.93);
    background: #e0e0e0;
  }

  .num-btn:disabled {
    opacity: 0.35;
    cursor: not-allowed;
  }

  .action-btn {
    background: #fff3f3;
    border-color: #ffcdd2;
    color: #c62828;
  }

  .action-btn:hover:not(:disabled) {
    background: #ffebee;
  }

  .clear-btn {
    font-size: 1rem;
  }

  /* Botão submit */
  .submit-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    padding: 0.9rem;
    font-size: 1rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    border: none;
    border-radius: 10px;
    background: #1a1a2e;
    color: #ffffff;
    cursor: pointer;
    transition: background 0.15s, transform 0.08s, box-shadow 0.15s;
  }

  .submit-btn:hover:not(:disabled) {
    background: #2d2d4a;
    box-shadow: 0 4px 14px rgba(26,26,46,0.35);
  }

  .submit-btn:active:not(:disabled) {
    transform: scale(0.97);
  }

  .submit-btn:disabled {
    background: #c8c8d0;
    cursor: not-allowed;
    box-shadow: none;
  }

  /* Spinner */
  .spinner {
    display: inline-block;
    width: 16px;
    height: 16px;
    border: 2px solid rgba(255,255,255,0.4);
    border-top-color: #fff;
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  /* Mensagem de erro */
  .error-msg {
    color: #c62828;
    font-size: 0.85rem;
    text-align: center;
    margin: 0;
    padding: 0.5rem;
    background: #ffebee;
    border-radius: 6px;
    animation: fadeIn 0.2s ease;
  }

  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(-4px); }
    to   { opacity: 1; transform: translateY(0); }
  }

  .hint {
    font-size: 0.75rem;
    color: #aaa;
    text-align: center;
    margin: 0;
  }
</style>
