import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Configuration for AWS Workshop Studio with CloudFront + VSCode Server
export default defineConfig({
  // CRITICAL: Set base path for production builds to work with CloudFront /ports/5173/ routing
  base: process.env.NODE_ENV === 'production' ? '/ports/5173/' : '/',
  
  plugins: [react()],
  
  server: {
    host: true,  // Allow all hosts (required for CloudFront)
    port: 5173,
    strictPort: true,
    
    // API proxy
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  
  build: {
    outDir: 'dist',
    sourcemap: true,
    // Cache busting: Add hash to filenames for workshop reliability
    rollupOptions: {
      output: {
        entryFileNames: 'assets/[name].[hash].js',
        chunkFileNames: 'assets/[name].[hash].js',
        assetFileNames: 'assets/[name].[hash].[ext]'
      }
    }
  },
})
