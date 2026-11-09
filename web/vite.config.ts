import { fileURLToPath } from 'node:url'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'
import { defineConfig } from 'vitest/config'

const API_TARGET = process.env.CONFPILOT_API ?? 'http://localhost:8000'
const here = (path: string): string => fileURLToPath(new URL(path, import.meta.url))

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg', 'apple-touch-icon.png'],
      manifest: {
        name: 'Nautilus',
        short_name: 'Nautilus',
        description: 'Live captions that explain the jargon you do not know yet.',
        lang: 'en',
        start_url: '/',
        scope: '/',
        display: 'standalone',
        orientation: 'portrait',
        background_color: '#0c1326',
        theme_color: '#0c1326',
        icons: [
          { src: 'icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'icon-512.png', sizes: '512x512', type: 'image/png' },
          { src: 'icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        // Hashed assets are immutable, so they are safe to precache. The HTML shell is not
        // precached: navigations go to the network first so a deploy is never stale.
        globPatterns: ['**/*.{js,css,woff2,svg,png}'],
        navigateFallback: null,
        cleanupOutdatedCaches: true,
        clientsClaim: true,
        skipWaiting: true,
        runtimeCaching: [
          {
            urlPattern: ({ request }) => request.mode === 'navigate',
            handler: 'NetworkFirst',
            options: { cacheName: 'app-shell', networkTimeoutSeconds: 3 },
          },
          {
            urlPattern: ({ url }) => url.pathname === '/api/glossary',
            handler: 'NetworkFirst',
            options: {
              cacheName: 'glossary',
              networkTimeoutSeconds: 2,
              expiration: { maxEntries: 2 },
            },
          },
        ],
      },
    }),
  ],
  resolve: {
    alias: {
      '@contracts': fileURLToPath(new URL('../contracts/types.ts', import.meta.url)),
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: true,
    // Tests import the shared glossary and fixtures, which live outside web/.
    fs: { allow: [here('.'), here('../content'), here('../contracts')] },
    proxy: {
      '/api': { target: API_TARGET, changeOrigin: true },
      '/ws': { target: API_TARGET, ws: true, changeOrigin: true },
    },
  },
  test: {
    environment: 'jsdom',
    globals: false,
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}', 'mock/**/*.test.ts'],
    css: false,
  },
})
