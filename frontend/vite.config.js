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
    rollupOptions: {
      output: {
        manualChunks(id) {
          const normalized = id.replace(/\\/g, '/');
          if (normalized.includes('/node_modules/')) {
            if (
              normalized.includes('/react/') ||
              normalized.includes('/react-dom/') ||
              normalized.includes('/react-router/') ||
              normalized.includes('/react-router-dom/') ||
              normalized.includes('/scheduler/') ||
              normalized.includes('/use-sync-external-store/') ||
              normalized.includes('/@remix-run/router/')
            ) {
              return 'react-vendor';
            }
            if (normalized.includes('/katex/')) {
              return 'katex-vendor';
            }
            if (normalized.includes('/@xterm/') || normalized.includes('/xterm/')) {
              return 'terminal-vendor';
            }
            if (normalized.includes('react-syntax-highlighter') || normalized.includes('prismjs')) {
              return 'syntax-highlighter-vendor';
            }
            if (normalized.includes('@codemirror') || normalized.includes('@uiw/react-codemirror')) {
              return 'codemirror-vendor';
            }
            if (normalized.includes('lexical') || normalized.includes('@lexical')) {
              return 'lexical-vendor';
            }
            if (normalized.includes('lucide-react')) {
              return 'lucide-vendor';
            }
            if (normalized.includes('react-markdown') || normalized.includes('remark-') || normalized.includes('rehype-')) {
              return 'markdown-vendor';
            }
            if (normalized.includes('i18next') || normalized.includes('react-i18next')) {
              return 'i18n-vendor';
            }
          }
        }
      }
    },
    // Mermaid and Cynefin stand-alone engines are ~675kB minified by design.
    // Setting limit to 800kB cleanly accommodates them without false-positive warnings.
    chunkSizeWarningLimit: 800
  }
})
