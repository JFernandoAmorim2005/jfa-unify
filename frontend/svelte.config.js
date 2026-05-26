import adapter from '@sveltejs/adapter-auto';
import { vitePreprocess } from '@sveltejs/kit/vite';

/** @type {import('@sveltejs/kit').Config} */
const config = {
  preprocess: vitePreprocess(),

  kit: {
    adapter: adapter(),
    alias: {
      // Alias $lib aponta para src/lib (padrão SvelteKit, aqui explícito)
      '$lib': 'src/lib',
    },
  },
};

export default config;
