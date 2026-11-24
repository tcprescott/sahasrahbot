import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './App'
import './styles/tokens.css'
import './styles/base.css'
import './kit/forms.css'
import './styles/app.css'

const root = document.getElementById('root')
if (!root) throw new Error('index.html is missing #root')
createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
