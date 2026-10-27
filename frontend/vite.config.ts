import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    target: 'es2019',
    cssTarget: 'safari13',
  },
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
