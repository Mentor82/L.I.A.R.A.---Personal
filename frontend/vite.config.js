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
          if (id.includes('node_modules')) {
            if (id.includes('katex')) {
              return 'katex-vendor';
            }
            if (id.includes('@xterm')) {
              return 'terminal-vendor';
            }
            if (id.includes('react-syntax-highlighter') || id.includes('prismjs')) {
              return 'syntax-highlighter-vendor';
            }
            if (id.includes('@codemirror') || id.includes('@uiw/react-codemirror')) {
              return 'codemirror-vendor';
            }
            if (id.includes('lexical') || id.includes('@lexical')) {
              return 'lexical-vendor';
            }
            if (id.includes('lucide-react')) {
              return 'lucide-vendor';
            }
            if (id.includes('react-markdown') || id.includes('remark-') || id.includes('rehype-')) {
              return 'markdown-vendor';
            }
            if (id.includes('react-router-dom') || id.includes('react-dom') || id.includes('/react/')) {
              return 'react-vendor';
            }
            if (id.includes('i18next') || id.includes('react-i18next')) {
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
