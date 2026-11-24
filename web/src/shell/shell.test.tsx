import { screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { USERS, never } from '../test/fakeApi'
import { currentPath, renderApp } from '../test/renderApp'
import { titleFor } from './tabs'

describe('top bar title', () => {
  it.each([
    ['/', 'Home'],
    ['/presets/manage/synack', 'Presets'],
    ['/me', 'Me'],
    ['/purgeme', 'Me'],
    ['/ranked_choice/3', 'Vote'],
    ['/triforcetexts/sgl', 'Triforce texts'],
    ['/submit/alttprleague', 'Race settings'],
    ['/nowhere', 'SahasrahBot'],
  ])('%s is titled %s', (path, title) => {
    expect(titleFor(path)).toBe(title)
  })
})

describe('navigation', () => {
  it('marks the current tab in both the rail and the tab bar', async () => {
    renderApp('/presets', { routes: { 'GET /api/v1/presets/namespaces': { namespaces: [] } } })
    const navs = screen.getAllByRole('navigation', { name: 'Main' })
    expect(navs).toHaveLength(2)
    for (const nav of navs) {
      expect(within(nav).getByRole('link', { name: 'Presets' }).getAttribute('aria-current')).toBe('page')
      expect(within(nav).getByRole('link', { name: 'Home' }).getAttribute('aria-current')).toBeNull()
    }
    // the docs link is only on the rail
    expect(within(navs[0]!).getByRole('link', { name: /Docs/ }).getAttribute('href')).toBe('https://sahasrahbot.synack.live/')
    expect(within(navs[1]!).queryByRole('link', { name: /Docs/ })).toBeNull()
  })

  it('moves between pages without a reload', async () => {
    const { user } = renderApp('/', { routes: { 'GET /api/v1/presets/namespaces': { namespaces: [] } } })
    const [rail] = screen.getAllByRole('navigation', { name: 'Main' })
    await user.click(within(rail!).getByRole('link', { name: 'Presets' }))
    expect(currentPath()).toBe('/presets')
    expect(await screen.findByRole('heading', { level: 1, name: 'Presets' })).toBeTruthy()
  })
})

describe('user menu', () => {
  it('offers Sign in, back to this page, when signed out', async () => {
    renderApp('/presets?x=1', { routes: { 'GET /api/v1/presets/namespaces': { namespaces: [] } } })
    const signIn = await screen.findByRole('link', { name: 'Sign in' })
    expect(signIn.getAttribute('href')).toBe('/login/?next=%2Fpresets%3Fx%3D1')
  })

  it('shows initials when the user has no avatar', async () => {
    renderApp('/', { signedIn: USERS.alice })
    const pill = await screen.findByRole('button', { name: 'Account menu for alice' })
    expect(pill.textContent).toContain('AL')
  })

  it("shows the user's Discord avatar", async () => {
    renderApp('/', { signedIn: USERS.bob })
    const pill = await screen.findByRole('button', { name: 'Account menu for Bob the Builder' })
    expect(pill.querySelector('img')?.getAttribute('src')).toBe('https://cdn.test/bob.png')
  })

  it('goes to Me', async () => {
    const { user } = renderApp('/', { signedIn: USERS.alice, routes: { 'GET /api/v1/me': never } })
    await user.click(await screen.findByRole('button', { name: 'Account menu for alice' }))
    expect(screen.getByText('Signed in as alice')).toBeTruthy()
    await user.click(screen.getByRole('menuitem', { name: 'Me' }))
    expect(currentPath()).toBe('/me')
  })

  it('signs out through the server', async () => {
    const { user, assigned } = renderApp('/', { signedIn: USERS.alice })
    await user.click(await screen.findByRole('button', { name: 'Account menu for alice' }))
    await user.click(screen.getByRole('menuitem', { name: 'Sign out' }))
    expect(assigned).toEqual(['/logout/'])
  })
})

describe('theme', () => {
  it('follows the device until a theme is picked', async () => {
    renderApp('/', { prefersDark: true })
    await screen.findByRole('link', { name: 'Sign in' })
    expect(document.documentElement.dataset.theme).toBe('dark')
  })

  it('remembers the theme picked, and forgets it on Match my device', async () => {
    const { user } = renderApp('/')
    const pick = async (name: string) => {
      await user.click(await screen.findByRole('button', { name: 'Theme' }))
      await user.click(screen.getByRole('menuitem', { name }))
    }
    await pick('Theme: Dark')
    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(window.localStorage.getItem('sb.theme')).toBe('dark')

    await user.click(screen.getByRole('button', { name: 'Theme' }))
    expect(screen.getByRole('menuitem', { name: '✓ Theme: Dark' })).toBeTruthy()
    await user.keyboard('{Escape}')

    await pick('Theme: Match my device')
    expect(document.documentElement.dataset.theme).toBe('light')
    expect(window.localStorage.getItem('sb.theme')).toBeNull()
  })

  it('starts from the remembered theme', async () => {
    window.localStorage.setItem('sb.theme', 'light')
    renderApp('/', { prefersDark: true })
    await screen.findByRole('link', { name: 'Sign in' })
    expect(document.documentElement.dataset.theme).toBe('light')
  })
})
