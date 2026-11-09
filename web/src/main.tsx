import '@fontsource-variable/atkinson-hyperlegible-next/index.css'
import '@fontsource/young-serif/400.css'
import './index.css'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { registerSW } from 'virtual:pwa-register'
import App from './App.tsx'

registerSW({ immediate: true })

const root = document.getElementById('root')
if (!root) throw new Error('ConfPilot could not start: the #root element is missing.')

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
