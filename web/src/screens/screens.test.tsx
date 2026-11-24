import { screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { Profile } from '../api/client'
import { fail, never, USERS } from '../test/fakeApi'
import { currentPath, main, renderApp } from '../test/renderApp'

const profile = (overrides: Partial<Profile> = {}): Profile => ({
  user: USERS.alice,
  racetime_linked: false,
  racetime_id: null,
  preset_namespace: null,
  moderated_triforce_pools: [],
  ...overrides,
})

describe('home', () => {
  it('greets a signed-in user by name', async () => {
    renderApp('/', { signedIn: USERS.alice })
    expect(await screen.findByRole('heading', { level: 1, name: 'Hi, alice' })).toBeTruthy()
  })

  it('links to presets, racetime linking and the bot invite', async () => {
    renderApp('/')
    expect(screen.getByRole('heading', { level: 1, name: 'SahasrahBot' })).toBeTruthy()
    expect(screen.getByRole('link', { name: 'My presets' }).getAttribute('href')).toBe('/presets/me')
    expect(screen.getByRole('link', { name: 'Link racetime.gg' }).getAttribute('href')).toBe('/racetime/verification/initiate')
    expect(screen.getByRole('link', { name: 'Invite to Discord' }).getAttribute('href')).toContain('client_id=572269659290861578')
  })
})

describe('pages that need a sign-in', () => {
  it.each(['/me', '/purgeme', '/presets/me', '/ranked_choice/1', '/triforcetexts/sgl', '/submit/alttpr?episode_id=5'])(
    '%s sends a signed-out visitor to Discord and back',
    async (path) => {
      const { assigned } = renderApp(path)
      expect(await screen.findByText('Taking you to Discord to sign in')).toBeTruthy()
      expect(assigned).toEqual([`/login/?next=${encodeURIComponent(path)}`])
    },
  )

  it('treats a failed session check as signed out', async () => {
    const { assigned } = renderApp('/me', { routes: { 'GET /api/v1/session': fail(500, 'down') } })
    await waitFor(() => expect(assigned).toEqual(['/login/?next=%2Fme']))
  })
})

describe('error, not found and old URLs', () => {
  it('shows the message the server sent', () => {
    renderApp('/error?code=403&message=Not%20a%20moderator')
    expect(screen.getByRole('heading', { level: 1, name: "You can't do that" })).toBeTruthy()
    expect(screen.getByRole('alert').textContent).toBe('Not a moderator')
    expect(screen.getByRole('link', { name: 'Sign in again' }).getAttribute('href')).toBe('/login/?next=%2Fme')
  })

  it('falls back for an unknown code and no message', () => {
    renderApp('/error?code=418')
    expect(screen.getByRole('heading', { level: 1, name: 'Something went wrong' })).toBeTruthy()
    expect(screen.getByRole('alert').textContent).toBe('Something went wrong on our side. Try again later.')
  })

  it('says so for a page that does not exist', () => {
    renderApp('/definitely/not/here')
    expect(screen.getByText("There's nothing here")).toBeTruthy()
  })

  it('sends /logout home', () => {
    renderApp('/logout')
    expect(currentPath()).toBe('/')
  })

  it('sends the old namespace URL to the manage page', () => {
    renderApp('/presets/synack', { routes: { 'GET /api/v1/presets/namespaces/synack': never() } })
    expect(currentPath()).toBe('/presets/manage/synack')
  })
})

describe('me', () => {
  it('shows an unlinked account with nothing else', async () => {
    renderApp('/me', { signedIn: USERS.alice, routes: { 'GET /api/v1/me': profile() } })
    expect(await screen.findByRole('heading', { level: 1, name: 'alice' })).toBeTruthy()
    expect(screen.getByText('Not linked')).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Link racetime.gg' })).toBeTruthy()
    expect(screen.getByText("You haven't made any presets yet.")).toBeTruthy()
    expect(screen.queryByRole('heading', { name: 'Triforce texts you moderate' })).toBeNull()
  })

  it('shows the racetime link, namespace and moderated pools', async () => {
    renderApp('/me?racetime=Runner%231234', {
      signedIn: USERS.alice,
      routes: {
        'GET /api/v1/me': profile({
          racetime_linked: true,
          racetime_id: 'rt-1',
          preset_namespace: 'alice',
          moderated_triforce_pools: ['sgl 2026'],
        }),
      },
    })
    expect(await screen.findByText('rt-1')).toBeTruthy()
    expect(main().textContent).toContain('Linked racetime.gg account Runner#1234')
    expect(screen.getByRole('link', { name: 'Link again' })).toBeTruthy()
    expect(screen.getByText('alice', { selector: '.code' })).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Review' }).getAttribute('href')).toBe('/triforcetexts/sgl%202026/moderation')
  })

  it('offers Try again when the profile fails to load', async () => {
    const { api, user } = renderApp('/me', { signedIn: USERS.alice, routes: { 'GET /api/v1/me': fail(500, 'Database is down') } })
    expect((await screen.findByRole('alert')).textContent).toContain('Database is down')
    api.on('GET /api/v1/me', profile())
    await user.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByRole('heading', { level: 1, name: 'alice' })).toBeTruthy()
  })
})

describe('delete my data', () => {
  const routes = { 'GET /api/v1/me': profile() }

  it('keeps the data and goes back to Me', async () => {
    const { user, api } = renderApp('/purgeme', { signedIn: USERS.alice, routes })
    await user.click(await screen.findByRole('button', { name: 'Keep my data' }))
    expect(currentPath()).toBe('/me')
    expect(api.callsTo('POST /api/v1/me/purge')).toHaveLength(0)
  })

  it('confirms, deletes, signs out and goes home', async () => {
    const { user, api } = renderApp('/purgeme', { signedIn: USERS.alice, routes: { ...routes, 'POST /api/v1/me/purge': { ok: true } } })
    await user.click(await screen.findByRole('button', { name: 'Delete my data' }))
    const dialog = screen.getByRole('dialog', { name: 'Delete your data?' })
    expect(dialog.textContent).toContain('deleted for good')
    api.on('GET /api/v1/session', { user: null })
    await user.click(screen.getByRole('button', { name: 'Delete and sign out' }))

    await waitFor(() => expect(currentPath()).toBe('/'))
    const [purge] = api.callsTo('POST /api/v1/me/purge')
    expect(purge?.headers.get('X-Requested-With')).toBe('SahasrahBot')
    expect(api.callsTo('GET /api/v1/session')).toHaveLength(2)
    expect(await screen.findByRole('heading', { level: 1, name: 'SahasrahBot' })).toBeTruthy()
  })

  it('shows why the delete failed and stays', async () => {
    const { user } = renderApp('/purgeme', {
      signedIn: USERS.alice,
      routes: { ...routes, 'POST /api/v1/me/purge': fail(500, 'Could not delete your presets.') },
    })
    await user.click(await screen.findByRole('button', { name: 'Delete my data' }))
    await user.click(screen.getByRole('button', { name: 'Delete and sign out' }))
    expect((await screen.findByRole('alert')).textContent).toContain('Could not delete your presets.')
    expect(currentPath()).toBe('/purgeme')
  })
})
