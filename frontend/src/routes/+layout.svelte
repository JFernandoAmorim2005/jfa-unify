<script>
  /**
   * +layout.svelte — Layout raiz da aplicação SvelteKit
   *
   * Responsável por:
   * - Importar estilos globais
   * - Inicializar a ligação MQTT ao montar
   * - Gerir o ciclo de vida global (ex: limpar ligações ao sair)
   */
  import { onMount, onDestroy } from 'svelte';
  import { mqttClient } from '$lib/services/mqtt.js';
  import { markAllDevicesOffline } from '$lib/stores/device.js';

  onMount(async () => {
    // Nota: A ligação MQTT é iniciada aqui para partilha entre todas as rotas.
    // O +page.svelte também chama connect() — é idempotente.
    // Listener de mudança de estado global
    const unsubscribe = mqttClient.onConnectionChange((status) => {
      if (status === 'disconnected' || status === 'error') {
        markAllDevicesOffline();
      }
    });

    return unsubscribe;
  });

  onDestroy(() => {
    mqttClient.disconnect();
  });
</script>

<!-- Slot para o conteúdo da rota activa -->
<slot />

<style>
  /* Estilos globais base */
  :global(html) {
    font-size: 16px;
    -webkit-text-size-adjust: 100%;
  }

  :global(body) {
    margin: 0;
    padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
                 'Helvetica Neue', Arial, sans-serif;
    background: #f0f2f5;
    color: #1a1a2e;
    line-height: 1.5;
  }

  :global(button) {
    font-family: inherit;
  }

  :global(input) {
    font-family: inherit;
  }

  /* Focus visible para acessibilidade */
  :global(:focus-visible) {
    outline: 2px solid #1a1a2e;
    outline-offset: 2px;
  }

  :global(:focus:not(:focus-visible)) {
    outline: none;
  }
</style>
