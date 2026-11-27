// Runs before every Vitest file (vite.config.ts `test.setupFiles`).
import { cleanup, configure } from '@testing-library/react'
import { afterEach, vi } from 'vitest'

// jsdom has no layout, so Radix's menus and dialogs need these to open.
class NoopResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver ??= NoopResizeObserver as unknown as typeof ResizeObserver
Element.prototype.scrollIntoView ??= function scrollIntoView() {}
Element.prototype.hasPointerCapture ??= () => false
Element.prototype.releasePointerCapture ??= () => {}
// CodeMirror (the preset YAML editor) measures text with Range, which jsdom can't lay out.
const noRect = () => new DOMRect(0, 0, 0, 0)
Range.prototype.getBoundingClientRect ??= noRect
Range.prototype.getClientRects ??= () => Object.assign([], { item: () => null }) as unknown as DOMRectList
// jsdom's Blob has no text() (the YAML field reads a chosen file with it).
Blob.prototype.text ??= function text(this: Blob) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = () => reject(reader.error ?? new Error('read failed'))
    reader.readAsText(this)
  })
}

// The app calls its API by path ('/api/v1/...'), as a browser resolves against
// the page. Node's Request needs an absolute URL, so resolve it the same way.
const NodeRequest = globalThis.Request
globalThis.Request = class PageRequest extends NodeRequest {
  constructor(input: RequestInfo | URL, init?: RequestInit) {
    super(typeof input === 'string' ? new URL(input, window.location.href) : input, init)
  }
}

// findBy*/waitFor give up after 1s by default. The first screen a test file renders
// loads its route's modules cold and makes several API calls, which can take longer
// than that on a busy CI runner, so allow 5s.
configure({ asyncUtilTimeout: 5000 })

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
  window.localStorage.clear()
  delete document.documentElement.dataset.theme
})
