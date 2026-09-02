import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    allowedHosts: ['liara', '192.168.178.50', 'localhost', 'liara.mw-dresden.myfritz.link'],
    proxy: {
      '/api': {
        target: 'http://localhost:8100',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  },
  build: {
    minify: 'terser',
    cssMinify: true,
    rolldownOptions: {
      output: {
        manualChunks(id) {
          const normalized = id.replace(/\\/g, '/');
          if (normalized.includes('/node_modules/')) {
            // Only split isolated standalone heavy engines (no peer dependency cycles)
            if (normalized.includes('/katex/')) {
              return 'katex-vendor';
            }
            if (normalized.includes('/@xterm/') || normalized.includes('/xterm/')) {
              return 'terminal-vendor';
            }
            if (normalized.includes('@codemirror') || normalized.includes('@uiw/react-codemirror')) {
              return 'codemirror-vendor';
            }
            if (normalized.includes('cytoscape')) {
              return 'cytoscape-vendor';
            }
          }
        }
      }
    },
    // Accommodate standalone visualization engines without false-positive warnings
    chunkSizeWarningLimit: 1000
  }
})
