import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    // The dev server is reached through a proxied host in some
    // environments, so the origin cannot be fixed to localhost.
    allowedHosts: true,
    proxy: {
      '/api': {
        target: process.env.VITE_PROXY_TARGET || 'http://localhost:5000',
        changeOrigin: true,
      },
    },
  },
  build: {
    // Data costs are a real consideration for the people using this, so
    // the heavier libraries are split out and only fetched by the screens
    // that need them.
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined;
          if (id.includes('recharts') || id.includes('d3-') || id.includes('victory')) return 'charts';
          if (id.includes('framer-motion') || id.includes('motion-dom') || id.includes('motion-utils')) return 'motion';
          if (id.includes('date-fns')) return 'dates';
          if (id.includes('zod')) return 'validation';
          if (id.includes('react-hook-form') || id.includes('@hookform')) return 'forms';
          if (id.includes('@headlessui') || id.includes('@heroicons')) return 'ui';
          if (id.includes('react-router')) return 'router';
          if (id.includes('@tanstack')) return 'query';
          if (id.includes('axios')) return 'http';
          if (id.includes('react-hot-toast') || id.includes('goober')) return 'toast';
          return 'vendor';
        },
      },
    },
    chunkSizeWarningLimit: 300,
  },
});
