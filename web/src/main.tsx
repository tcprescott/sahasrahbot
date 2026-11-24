import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './App'
import { reactErrorHandler, startTelemetry } from './telemetry'
import './styles/tokens.css'
import './styles/base.css'
import './kit/forms.css'
import './styles/app.css'

const root = document.getElementById('root')
if (!root) throw new Error('index.html is missing #root')
// Sentry starts first (when the server has it on), so errors during the first render are reported.
void startTelemetry().finally(() => {
  createRoot(root, {
    onUncaughtError: reactErrorHandler(),
    onCaughtError: reactErrorHandler(),
  }).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
})
