/**
 * Render the whole app at a URL, as a visitor would land on it, against a
 * fake API. Screen tests go through here so routing, the shell and sign-in are
 * exercised for real.
 *
 *   const { api, user } = renderApp('/me', { signedIn: USERS.alice, routes: { 'GET /api/v1/me': profile } })
 *   await screen.findByRole('heading', { name: 'alice' })
 */
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import type { SessionUser } from '../api/client'
import { App } from '../App'
import { browser } from '../lib/browser'
import { fakeApi, type Handler } from './fakeApi'

export interface RenderOptions {
  signedIn?: SessionUser | null
  routes?: Record<string, Handler>
  /** Lay the page out as on a phone (below 768px). */
  phone?: boolean
  /** What the device says about dark mode. */
  prefersDark?: boolean
}

export function renderApp(path: string, { signedIn = null, routes = {}, phone = false, prefersDark = false }: RenderOptions = {}) {
  window.history.replaceState({}, '', path)
  vi.stubGlobal('matchMedia', (query: string) => ({
    matches: (query.includes('max-width') && phone) || (query.includes('prefers-color-scheme: dark') && prefersDark),
    media: query,
    addEventListener: () => {},
    removeEventListener: () => {},
  }))
  // jsdom can't leave the page; record where the app sends the browser instead.
  const assigned: string[] = []
  vi.spyOn(browser, 'assign').mockImplementation((url) => void assigned.push(url))
  vi.spyOn(browser, 'openTab').mockImplementation((url) => void assigned.push(url))
  const api = fakeApi(routes, signedIn)
  const result = render(<App />)
  return { ...result, api, assigned, user: userEvent.setup() }
}

/** The path the app is showing now (after client-side navigation). */
export const currentPath = () => window.location.pathname + window.location.search

/** The page's main region: the shell has two copies of the nav, so scope queries here. */
export const main = () => screen.getByRole('main')
