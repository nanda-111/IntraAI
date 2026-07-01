import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  build: {
    chunkSizeWarningLimit: 1500,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return
          // Split ant-design-vue (the heaviest lib) into its own chunk
          if (id.includes('ant-design-vue') || id.includes('@ant-design/icons-vue')) {
            return 'vendor-antd'
          }
          // Core framework — keep separate so app pages can cache independently
          if (id.includes('/vue/') || id.includes('/vue-router/') || id.includes('/pinia/')) {
            return 'vendor-vue'
          }
          if (id.includes('markdown-it') || id.includes('dompurify')) {
            return 'vendor-markdown'
          }
          // Everything else (axios, etc.)
          return 'vendor'
        },
      },
    },
  },
})
