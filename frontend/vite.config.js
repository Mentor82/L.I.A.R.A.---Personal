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
        manualChunks: {
          // Core React libraries
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          
          // i18n
          'i18n': ['react-i18next', 'i18next', 'i18next-browser-languagedetector'],
          
          // Markdown rendering
          'markdown': ['react-markdown', 'remark-gfm', 'rehype-raw'],
          
          // Terminal components (xterm is large)
          'terminal': ['@xterm/xterm', '@xterm/addon-fit', '@xterm/addon-web-links'],
        }
      }
    },
    chunkSizeWarningLimit: 600
  }
})
