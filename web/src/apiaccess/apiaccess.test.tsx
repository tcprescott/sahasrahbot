import { screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { ApiTokenRow } from '../api/client'
import { fail, reply, USERS } from '../test/fakeApi'
import { main, renderApp } from '../test/renderApp'

const MCP = 'https://sahasrahbot.test/mcp'

const token = (overrides: Partial<ApiTokenRow> = {}): ApiTokenRow => ({
  id: 5,
  name: 'My script',
  kind: 'token',
  read_only: true,
  prefix: 'sb_pat_ab12',
  created_at: '2026-11-01T00:00:00Z',
  last_used_at: null,
  expires_at: null,
  ...overrides,
})

const client = token({ id: 6, name: 'Claude', kind: 'client', read_only: false, prefix: null })

describe('API access page', () => {
  it('lists tokens and clients and shows the MCP address and setup', async () => {
    renderApp('/me/api', { signedIn: USERS.alice, routes: { 'GET /api/v1/tokens': { tokens: [token(), client], mcp_url: MCP } } })
    expect(await screen.findByRole('heading', { level: 1, name: 'API access' })).toBeTruthy()
    const page = main()
    expect(within(page).getAllByText(MCP).length).toBeGreaterThan(0)
    expect(within(page).getByText(`claude mcp add --transport http sahasrahbot ${MCP}`)).toBeTruthy()
    expect(within(page).getByText('My script')).toBeTruthy()
    expect(within(page).getByText('Read only')).toBeTruthy()
    expect(within(page).getByText('Can make changes')).toBeTruthy()
    expect(within(page).getByText('Until you disconnect')).toBeTruthy()
    expect(within(page).getByRole('link', { name: 'API docs' }).getAttribute('href')).toBe('/api/v1/docs')
  })

  it('says when there are none yet', async () => {
    renderApp('/me/api', { signedIn: USERS.alice, routes: { 'GET /api/v1/tokens': { tokens: [], mcp_url: MCP } } })
    expect(await screen.findByText('No tokens or clients yet')).toBeTruthy()
  })

  it('copies the MCP address', async () => {
    const { user } = renderApp('/me/api', { signedIn: USERS.alice, routes: { 'GET /api/v1/tokens': { tokens: [], mcp_url: MCP } } })
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    await user.click(await screen.findByRole('button', { name: 'Copy the MCP address' }))
    expect(writeText).toHaveBeenCalledWith(MCP)
    expect(await screen.findByRole('button', { name: 'Copied' })).toBeTruthy()
  })

  it('makes a token and shows it once', async () => {
    const made = token({ id: 7, name: 'Bot', read_only: false, expires_at: '2027-02-22T00:00:00Z' })
    const { user, api } = renderApp('/me/api', {
      signedIn: USERS.alice,
      routes: {
        'GET /api/v1/tokens': { tokens: [], mcp_url: MCP },
        'POST /api/v1/tokens': { token: 'sb_pat_secretvalue', row: made },
      },
    })
    await user.click(await screen.findByRole('button', { name: 'New token' }))
    await user.type(screen.getByLabelText('Name'), 'Bot')
    await user.click(screen.getByRole('radio', { name: /Read and make changes/ }))
    await user.selectOptions(screen.getByLabelText('Expires'), '365')
    await user.click(screen.getByRole('button', { name: 'Make token' }))
    expect(await screen.findByText('sb_pat_secretvalue')).toBeTruthy()
    expect(screen.getByText(/only time you'll see it/)).toBeTruthy()
    expect(api.callsTo('POST /api/v1/tokens')[0]?.body).toEqual({ name: 'Bot', read_only: false, expires_in_days: 365 })
    await user.click(screen.getByRole('button', { name: 'Done' }))
    await waitFor(() => expect(api.callsTo('GET /api/v1/tokens')).toHaveLength(2))
  })

  it('makes a read-only token that never expires', async () => {
    const { user, api } = renderApp('/me/api', {
      signedIn: USERS.alice,
      routes: {
        'GET /api/v1/tokens': { tokens: [], mcp_url: MCP },
        'POST /api/v1/tokens': { token: 'sb_pat_x', row: token() },
      },
    })
    await user.click(await screen.findByRole('button', { name: 'New token' }))
    await user.type(screen.getByLabelText('Name'), 'Reader')
    await user.selectOptions(screen.getByLabelText('Expires'), 'never')
    await user.click(screen.getByRole('button', { name: 'Make token' }))
    await screen.findByText('sb_pat_x')
    expect(api.callsTo('POST /api/v1/tokens')[0]?.body).toEqual({ name: 'Reader', read_only: true, expires_in_days: null })
  })

  it('shows why a token could not be made', async () => {
    const { user } = renderApp('/me/api', {
      signedIn: USERS.alice,
      routes: { 'GET /api/v1/tokens': { tokens: [], mcp_url: MCP }, 'POST /api/v1/tokens': fail(400, 'Give the token a name.') },
    })
    await user.click(await screen.findByRole('button', { name: 'New token' }))
    await user.click(screen.getByRole('button', { name: 'Make token' }))
    expect((await screen.findByRole('alert')).textContent).toContain('Give the token a name.')
  })

  it('revokes a token after confirming', async () => {
    const { user, api } = renderApp('/me/api', {
      signedIn: USERS.alice,
      routes: { 'GET /api/v1/tokens': { tokens: [token()], mcp_url: MCP }, 'DELETE /api/v1/tokens/5': reply(204) },
    })
    await user.click(await screen.findByRole('button', { name: 'More for My script' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Revoke' }))
    expect(screen.getByRole('heading', { name: 'Revoke this token?' })).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'Revoke' }))
    await waitFor(() => expect(api.callsTo('DELETE /api/v1/tokens/5')).toHaveLength(1))
    await waitFor(() => expect(api.callsTo('GET /api/v1/tokens')).toHaveLength(2))
  })

  it('disconnects a client and shows a failure', async () => {
    const { user } = renderApp('/me/api', {
      signedIn: USERS.alice,
      routes: { 'GET /api/v1/tokens': { tokens: [client], mcp_url: MCP }, 'DELETE /api/v1/tokens/6': fail(404, "That token doesn't exist.") },
    })
    await user.click(await screen.findByRole('button', { name: 'More for Claude' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Disconnect' }))
    await user.click(screen.getByRole('button', { name: 'Disconnect' }))
    expect((await screen.findByRole('alert')).textContent).toContain("That token doesn't exist.")
  })

  it('is linked from the profile', async () => {
    renderApp('/me', {
      signedIn: USERS.alice,
      routes: {
        'GET /api/v1/me': { user: USERS.alice, racetime_linked: false, racetime_id: null, preset_namespace: null, moderated_triforce_pools: [] },
      },
    })
    expect((await screen.findByRole('link', { name: 'API access' })).getAttribute('href')).toBe('/me/api')
  })
})

describe('AI client consent', () => {
  const routes = { 'GET /api/v1/oauth/requests/abc': { client_name: 'Claude', redirect_target: 'claude.ai' } }

  it('sends a signed-out visitor to sign in first', async () => {
    const { assigned } = renderApp('/oauth/consent?txn=abc')
    await waitFor(() => expect(assigned).toEqual([`/login/?next=${encodeURIComponent('/oauth/consent?txn=abc')}`]))
  })

  it('approves read-only by default', async () => {
    const { user, api, assigned } = renderApp('/oauth/consent?txn=abc', {
      signedIn: USERS.alice,
      routes: { ...routes, 'POST /api/v1/oauth/requests/abc/approve': { redirect_url: 'https://claude.ai/cb?code=1&state=s' } },
    })
    expect(await screen.findByRole('heading', { level: 1, name: 'Claude wants to use your SahasrahBot account' })).toBeTruthy()
    expect(screen.getByText('claude.ai')).toBeTruthy()
    expect(screen.getByText('alice')).toBeTruthy()
    expect(screen.queryByRole('navigation')).toBeNull()
    await user.click(screen.getByRole('button', { name: 'Approve' }))
    await waitFor(() => expect(assigned).toEqual(['https://claude.ai/cb?code=1&state=s']))
    expect(api.callsTo('POST /api/v1/oauth/requests/abc/approve')[0]?.body).toEqual({ allow_changes: false })
  })

  it('approves changes when the box is ticked', async () => {
    const { user, api } = renderApp('/oauth/consent?txn=abc', {
      signedIn: USERS.alice,
      routes: { ...routes, 'POST /api/v1/oauth/requests/abc/approve': { redirect_url: 'https://claude.ai/cb' } },
    })
    await user.click(await screen.findByRole('checkbox', { name: /Also let it make changes as you/ }))
    await user.click(screen.getByRole('button', { name: 'Approve' }))
    await waitFor(() => expect(api.callsTo('POST /api/v1/oauth/requests/abc/approve')[0]?.body).toEqual({ allow_changes: true }))
  })

  it('denies', async () => {
    const { user, assigned } = renderApp('/oauth/consent?txn=abc', {
      signedIn: USERS.alice,
      routes: { ...routes, 'POST /api/v1/oauth/requests/abc/deny': { redirect_url: 'https://claude.ai/cb?error=access_denied' } },
    })
    await user.click(await screen.findByRole('button', { name: 'Deny' }))
    await waitFor(() => expect(assigned).toEqual(['https://claude.ai/cb?error=access_denied']))
  })

  it('shows an expired request', async () => {
    renderApp('/oauth/consent?txn=abc', {
      signedIn: USERS.alice,
      routes: { 'GET /api/v1/oauth/requests/abc': fail(404, 'This request has expired. Start connecting again from your AI client.') },
    })
    expect(await screen.findByText(/This request has expired/)).toBeTruthy()
  })

  it('shows a failed answer and lets you try again', async () => {
    const { user } = renderApp('/oauth/consent?txn=abc', {
      signedIn: USERS.alice,
      routes: { ...routes, 'POST /api/v1/oauth/requests/abc/approve': fail(404, 'This request has expired.') },
    })
    await user.click(await screen.findByRole('button', { name: 'Approve' }))
    expect((await screen.findByRole('alert')).textContent).toContain('This request has expired.')
    expect((screen.getByRole('button', { name: 'Approve' }) as HTMLButtonElement).disabled).toBe(false)
  })
})
