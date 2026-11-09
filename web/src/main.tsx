import '@fontsource-variable/atkinson-hyperlegible-next/index.css'
import '@fontsource/young-serif/400.css'
import './index.css'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { registerSW } from 'virtual:pwa-register'
import { applyDemoLink } from './room/demo'
import { initTelemetry } from './telemetry/dash0'

// Monitoring starts first so it sees the whole session; it is a no-op when not configured.
void initTelemetry()

registerSW({ immediate: true })

const root = document.getElementById('root')
if (!root) throw new Error('Nautilus could not start: the #root element is missing.')

// A demo link (?demo=returning or ?demo=new) must set up storage before the app reads it,
// so the app module (and the profile store it creates on import) loads afterwards.
void applyDemoLink().finally(async () => {
  const { default: App } = await import('./App.tsx')
  createRoot(root).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
})
