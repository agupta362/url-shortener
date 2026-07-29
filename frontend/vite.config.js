import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Local npm run dev: browser calls /api → Vite forwards to FastAPI
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8002',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
