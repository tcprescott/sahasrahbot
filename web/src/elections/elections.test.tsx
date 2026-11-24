import { screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { ElectionDetail, ElectionResults, ElectionSummary } from '../api/client'
import { fail, USERS } from '../test/fakeApi'
import { currentPath, main, renderApp } from '../test/renderApp'
import { closesText, fromLocalInput, methodText, ordinal, toLocalInput, votes } from './labels'

const SERVERS = { servers: [{ id: '100000000000000001', name: 'Dev Server' }] }
const OPTIONS = {
  channels: [
    { id: '300', name: '#elections' },
    { id: '301', name: '#general' },
  ],
  roles: [{ id: '77', name: '@Voter' }],
}

const summary = (overrides: Partial<ElectionSummary> = {}): ElectionSummary => ({
  id: 12,
  title: 'Committee',
  guild_id: '100000000000000001',
  guild_name: 'Dev Server',
  method: 'stv',
  seats: 3,
  status: 'open',
  closes_at: null,
  closed_at: null,
  ballots: 42,
  ...overrides,
})

const detail = (overrides: Partial<ElectionDetail> = {}): ElectionDetail => ({
  ...summary(),
  description: 'Pick three.',
  channel_id: '300',
  message_id: '900',
  voter_role_id: null,
  show_vote_count: true,
  candidates: [
    { id: 1, name: 'Andy' },
    { id: 2, name: 'Bea' },
    { id: 3, name: 'Coral' },
    { id: 4, name: 'Dmitri' },
  ],
  locked: false,
  ...overrides,
})

const admin = (routes: Record<string, unknown> = {}) => ({
  signedIn: USERS.alice,
  routes: { 'GET /api/v1/elections/servers': SERVERS, 'GET /api/v1/elections/servers/100000000000000001': OPTIONS, ...routes },
})

describe('labels', () => {
  it('names methods, rounds and places', () => {
    expect(methodText('stv', 3)).toBe('Ranked (STV), 3 seats')
    expect(methodText('stv', 1)).toBe('Ranked (STV)')
    expect(methodText('approval', 1)).toBe('Approval')
    expect([1, 2, 3, 4, 11, 12, 13, 21, 22, 23].map(ordinal)).toEqual(['1st', '2nd', '3rd', '4th', '11th', '12th', '13th', '21st', '22nd', '23rd'])
    expect([3, 2.25].map(votes)).toEqual(['3', '2.3'])
    expect(closesText({ status: 'open', closes_at: null, closed_at: null })).toBe('No closing time')
    expect(closesText({ status: 'closed', closes_at: null, closed_at: null })).toBe('Closed')
    expect(closesText({ status: 'closed', closes_at: null, closed_at: '2026-11-02T00:00:00Z' })).toMatch(/^Closed .*2026/)
  })

  it('turns a closing time into the datetime input and back', () => {
    const iso = '2030-01-02T03:04:00.000Z'
    expect(fromLocalInput(toLocalInput(iso))).toBe(iso)
    expect(toLocalInput(null)).toBe('')
    expect(fromLocalInput('')).toBeNull()
  })
})

describe('the Elections tab', () => {
  it('is shown to someone who administers a server', async () => {
    renderApp('/', admin())
    const [rail] = screen.getAllByRole('navigation', { name: 'Main' })
    expect(await within(rail!).findByRole('link', { name: 'Elections' })).toBeTruthy()
  })

  it('is hidden from everyone else', async () => {
    const { api } = renderApp('/', { signedIn: USERS.alice, routes: { 'GET /api/v1/elections/servers': { servers: [] } } })
    await waitFor(() => expect(api.callsTo('GET /api/v1/elections/servers')).toHaveLength(1))
    expect(screen.queryByRole('link', { name: 'Elections' })).toBeNull()
  })

  it("isn't asked about when nobody is signed in", async () => {
    const { api } = renderApp('/')
    await screen.findByRole('heading', { level: 1 })
    expect(api.callsTo('GET /api/v1/elections/servers')).toHaveLength(0)
  })
})

describe('elections list', () => {
  const list = [
    summary(),
    summary({ id: 11, title: 'Mystery weights', method: 'approval', seats: 1, status: 'draft', ballots: 0, closes_at: '2030-01-02T03:04:00Z' }),
    summary({ id: 9, title: 'Charity game', method: 'plurality', seats: 1, status: 'closed', closed_at: '2026-11-02T00:00:00Z', ballots: 133 }),
  ]

  it('shows open elections first and filters the rest', async () => {
    const { user } = renderApp('/elections', admin({ 'GET /api/v1/elections': { elections: list } }))
    expect(await screen.findByRole('link', { name: 'Committee' })).toBeTruthy()
    expect(screen.queryByText('Charity game')).toBeNull()
    expect(main().textContent).toContain('Ranked (STV), 3 seats')
    await user.click(screen.getByRole('button', { name: /Drafts/ }))
    expect(screen.getByRole('link', { name: 'Mystery weights' }).getAttribute('href')).toBe('/elections/11/edit')
    await user.click(screen.getByRole('button', { name: /Closed/ }))
    expect(screen.getByRole('link', { name: 'Charity game' }).getAttribute('href')).toBe('/elections/9/results')
    await user.click(screen.getByRole('button', { name: /All/ }))
    expect(screen.getAllByRole('row')).toHaveLength(4)
    await user.click(screen.getByRole('link', { name: 'New election' }))
    expect(currentPath()).toBe('/elections/new')
  })

  it('starts on All when nothing is open, and says when a filter is empty', async () => {
    const { user } = renderApp('/elections', admin({ 'GET /api/v1/elections': { elections: [list[2]] } }))
    expect(await screen.findByRole('link', { name: 'Charity game' })).toBeTruthy()
    await user.click(screen.getByRole('button', { name: /Open/ }))
    expect(screen.getByText('Nothing here')).toBeTruthy()
  })

  it('closes an election after confirming', async () => {
    const { user, api } = renderApp('/elections', admin({ 'GET /api/v1/elections': { elections: list }, 'POST /api/v1/elections/12/close': detail({ status: 'closed' }) }))
    await user.click(await screen.findByRole('button', { name: 'More for Committee' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Close and count now' }))
    await user.click(await screen.findByRole('button', { name: 'Close and count' }))
    await waitFor(() => expect(api.callsTo('POST /api/v1/elections/12/close')).toHaveLength(1))
    await waitFor(() => expect(api.callsTo('GET /api/v1/elections')).toHaveLength(2))
  })

  it('deletes after confirming and shows a failure', async () => {
    const { user, api } = renderApp('/elections', admin({ 'GET /api/v1/elections': { elections: list }, 'DELETE /api/v1/elections/12': fail(403, 'Only administrators of that server can manage its elections.') }))
    await user.click(await screen.findByRole('button', { name: 'More for Committee' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Delete' }))
    await user.click(await screen.findByRole('button', { name: 'Delete' }))
    expect((await screen.findByRole('alert')).textContent).toContain('Only administrators')
    expect(api.callsTo('DELETE /api/v1/elections/12')).toHaveLength(1)
  })

  it('opens the ballot and the results from the row menu', async () => {
    const { user } = renderApp('/elections', admin({ 'GET /api/v1/elections': { elections: list } }))
    await user.click(await screen.findByRole('button', { name: 'More for Committee' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Open the ballot' }))
    expect(currentPath()).toBe('/ranked_choice/12')
  })

  it('explains who can run elections', async () => {
    renderApp('/elections', { signedIn: USERS.alice, routes: { 'GET /api/v1/elections/servers': { servers: [] }, 'GET /api/v1/elections': { elections: [] } } })
    expect(await screen.findByText(/run by server Administrators/)).toBeTruthy()
    expect(screen.queryByRole('link', { name: 'New election' })).toBeNull()
  })
})

describe('opening the form from the /rankedchoice create command', () => {
  const TWO = { servers: [{ id: '100000000000000001', name: 'Dev Server' }, { id: '100000000000000002', name: 'Other Server' }] }
  const routes = {
    'GET /api/v1/elections/servers': TWO,
    'GET /api/v1/elections/servers/100000000000000002': OPTIONS,
  }

  it('starts on the linked server and channel', async () => {
    renderApp('/elections/new?server=100000000000000002&channel=301', admin(routes))
    await waitFor(() => expect((screen.getByLabelText('Post it in') as HTMLSelectElement).value).toBe('301'))
    expect((screen.getByLabelText('Server') as HTMLSelectElement).value).toBe('100000000000000002')
  })

  it('uses the first channel when the bot cannot post in the linked one', async () => {
    renderApp('/elections/new?server=100000000000000002&channel=999', admin(routes))
    await waitFor(() => expect((screen.getByLabelText('Post it in') as HTMLSelectElement).value).toBe('300'))
  })

  it('ignores a server the viewer does not administer', async () => {
    renderApp('/elections/new?server=555&channel=301', admin(routes))
    await waitFor(() => expect((screen.getByLabelText('Server') as HTMLSelectElement).value).toBe('100000000000000001'))
    await waitFor(() => expect((screen.getByLabelText('Post it in') as HTMLSelectElement).value).toBe('300'))
  })
})

describe('creating an election', () => {
  const fill = async (user: ReturnType<typeof renderApp>['user']) => {
    await user.type(await screen.findByLabelText('Title'), 'Committee')
    await user.type(screen.getByLabelText('Candidate 1'), 'Andy')
    await user.type(screen.getByLabelText('Candidate 2'), 'Bea')
  }

  it('saves a draft with the form as filled in', async () => {
    const { user, api } = renderApp(
      '/elections/new',
      admin({ 'POST /api/v1/elections': detail({ id: 20, status: 'draft' }), 'GET /api/v1/elections/20': detail({ id: 20, status: 'draft', ballots: 0 }) }),
    )
    await fill(user)
    await waitFor(() => expect((screen.getByLabelText('Post it in') as HTMLSelectElement).value).toBe('300'))
    await user.click(screen.getByRole('button', { name: 'Add candidate' }))
    await user.type(screen.getByLabelText('Candidate 3'), 'Coral')
    await user.click(screen.getByRole('button', { name: 'Move Coral up' }))
    await user.click(screen.getByRole('button', { name: 'Remove Bea' }))
    await user.clear(screen.getByLabelText('Winners'))
    await user.type(screen.getByLabelText('Winners'), '1')
    await user.selectOptions(screen.getByLabelText('Who can vote'), '77')
    await user.type(screen.getByLabelText('Description'), 'Pick well.')
    await user.click(screen.getByRole('checkbox', { name: /Show the number of ballots/ }))
    await user.click(screen.getByRole('button', { name: 'Save draft' }))

    await waitFor(() => expect(currentPath()).toBe('/elections/20/edit'))
    expect(api.callsTo('POST /api/v1/elections')[0]?.body).toEqual({
      guild_id: '100000000000000001',
      channel_id: '300',
      title: 'Committee',
      description: 'Pick well.',
      candidates: ['Andy', 'Coral'],
      method: 'stv',
      seats: 1,
      voter_role_id: '77',
      closes_at: null,
      show_vote_count: false,
    })
    expect(await screen.findByText('Draft saved. Nothing is posted yet.')).toBeTruthy()
  })

  it('creates and posts, with a closing time, then goes back to the list', async () => {
    const { user, api } = renderApp(
      '/elections/new',
      admin({
        'POST /api/v1/elections': detail({ id: 20, status: 'draft' }),
        'POST /api/v1/elections/20/publish': detail({ id: 20 }),
        'GET /api/v1/elections': { elections: [summary({ id: 20 })] },
      }),
    )
    await fill(user)
    await user.click(screen.getByRole('radio', { name: /Approval/ }))
    expect(screen.queryByLabelText('Winners')).toBeNull()
    await user.type(screen.getByLabelText('Closes'), '2030-01-02T03:04')
    await user.click(screen.getByRole('button', { name: 'Create and post' }))
    expect(await screen.findByText('“Committee” is posted in Discord.')).toBeTruthy()
    expect(currentPath()).toBe('/elections')
    const body = api.callsTo('POST /api/v1/elections')[0]?.body as { method: string; closes_at: string; seats: number }
    expect(body.method).toBe('approval')
    expect(body.seats).toBe(1)
    expect(body.closes_at).toBe(new Date('2030-01-02T03:04').toISOString())
    expect(api.callsTo('POST /api/v1/elections/20/publish')).toHaveLength(1)
  })

  it('keeps a draft when posting fails and says why', async () => {
    const { user } = renderApp(
      '/elections/new',
      admin({
        'POST /api/v1/elections': detail({ id: 20, status: 'draft' }),
        'POST /api/v1/elections/20/publish': fail(400, "SahasrahBot isn't allowed to post in that channel."),
        'GET /api/v1/elections/20': detail({ id: 20, status: 'draft', ballots: 0 }),
      }),
    )
    await fill(user)
    await user.click(screen.getByRole('button', { name: 'Create and post' }))
    expect((await screen.findByRole('alert')).textContent).toContain('Saved as a draft, but not posted')
    expect(currentPath()).toBe('/elections/20/edit')
  })

  it('shows why the server refused the form', async () => {
    const { user } = renderApp('/elections/new', admin({ 'POST /api/v1/elections': fail(400, 'Give the election a title.') }))
    await user.click(await screen.findByRole('button', { name: 'Save draft' }))
    expect((await screen.findByRole('alert')).textContent).toContain('Give the election a title.')
    expect(currentPath()).toBe('/elections/new')
  })

  it('adds a pasted list of names', async () => {
    const { user } = renderApp('/elections/new', admin())
    await user.click(await screen.findByRole('button', { name: 'Paste a list' }))
    await user.type(screen.getByLabelText('One candidate per line'), 'Andy{enter}{enter}Bea {enter}Coral')
    await user.click(screen.getByRole('button', { name: 'Add 3' }))
    expect(['Candidate 1', 'Candidate 2', 'Candidate 3'].map((n) => (screen.getByLabelText(n) as HTMLInputElement).value)).toEqual(['Andy', 'Bea', 'Coral'])
    expect(screen.queryByLabelText('Candidate 4')).toBeNull()
  })

  it("says who can't run elections", async () => {
    renderApp('/elections/new', { signedIn: USERS.alice, routes: { 'GET /api/v1/elections/servers': { servers: [] } } })
    expect(await screen.findByText("You can't run elections")).toBeTruthy()
  })
})

describe('editing an election', () => {
  it('saves changes to an open election and keeps its server and channel', async () => {
    const { user, api } = renderApp('/elections/12/edit', admin({ 'GET /api/v1/elections/12': detail(), 'PUT /api/v1/elections/12': detail({ title: 'Committee 2027' }) }))
    expect(await screen.findByRole('heading', { level: 1, name: 'Committee' })).toBeTruthy()
    expect((screen.getByLabelText('Server') as HTMLSelectElement).disabled).toBe(true)
    expect((screen.getByLabelText('Post it in') as HTMLSelectElement).disabled).toBe(true)
    expect(screen.queryByRole('button', { name: 'Create and post' })).toBeNull()
    await user.type(screen.getByLabelText('Title'), ' 2027')
    await user.click(screen.getByRole('button', { name: 'Save changes' }))
    expect(await screen.findByText('Saved. The Discord post is updated.')).toBeTruthy()
    expect((api.callsTo('PUT /api/v1/elections/12')[0]?.body as { title: string }).title).toBe('Committee 2027')
  })

  it('locks the candidates and method once people have voted', async () => {
    renderApp('/elections/12/edit', admin({ 'GET /api/v1/elections/12': detail({ locked: true }) }))
    expect(await screen.findByText("People have voted, so the candidates can't change.")).toBeTruthy()
    expect(screen.queryByLabelText('Candidate 1')).toBeNull()
    expect((screen.getByRole('radio', { name: /Approval/ }) as HTMLInputElement).disabled).toBe(true)
  })

  it('posts a draft and clears its closing time', async () => {
    const { user, api } = renderApp(
      '/elections/11/edit',
      admin({
        'GET /api/v1/elections/11': detail({ id: 11, status: 'draft', closes_at: '2030-01-02T03:04:00Z', message_id: null }),
        'PUT /api/v1/elections/11': detail({ id: 11, status: 'draft' }),
        'POST /api/v1/elections/11/publish': detail({ id: 11 }),
        'GET /api/v1/elections': { elections: [] },
      }),
    )
    await user.click(await screen.findByRole('button', { name: 'No closing time' }))
    await user.click(screen.getByRole('button', { name: 'Create and post' }))
    await waitFor(() => expect(currentPath()).toBe('/elections'))
    expect((api.callsTo('PUT /api/v1/elections/11')[0]?.body as { closes_at: null }).closes_at).toBeNull()
  })

  it('saves a draft in place', async () => {
    const { user } = renderApp(
      '/elections/11/edit',
      admin({ 'GET /api/v1/elections/11': detail({ id: 11, status: 'draft' }), 'PUT /api/v1/elections/11': detail({ id: 11, status: 'draft' }) }),
    )
    await user.click(await screen.findByRole('button', { name: 'Save draft' }))
    expect(await screen.findByText('Draft saved. Nothing is posted yet.')).toBeTruthy()
  })

  it('closes from the Actions menu and shows the results', async () => {
    const { user } = renderApp(
      '/elections/12/edit',
      admin({
        'GET /api/v1/elections/12': detail(),
        'POST /api/v1/elections/12/close': detail({ status: 'closed' }),
        'GET /api/v1/elections/12/results': RESULTS,
      }),
    )
    await user.click(await screen.findByRole('button', { name: 'Actions' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Close and count now' }))
    await user.click(await screen.findByRole('button', { name: 'Close and count' }))
    await waitFor(() => expect(currentPath()).toBe('/elections/12/results'))
  })

  it('deletes from the Actions menu', async () => {
    const { user } = renderApp(
      '/elections/12/edit',
      admin({ 'GET /api/v1/elections/12': detail(), 'DELETE /api/v1/elections/12': { ok: true }, 'GET /api/v1/elections': { elections: [] } }),
    )
    await user.click(await screen.findByRole('button', { name: 'Actions' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Delete' }))
    await user.click(await screen.findByRole('button', { name: 'Delete' }))
    expect(await screen.findByText('“Committee” is deleted.')).toBeTruthy()
  })

  it('sends a closed election to its results', async () => {
    const { user } = renderApp('/elections/12/edit', admin({ 'GET /api/v1/elections/12': detail({ status: 'closed' }) }))
    expect(await screen.findByText('This election has closed')).toBeTruthy()
    await user.click(screen.getByRole('link', { name: 'See the results' }))
    expect(currentPath()).toBe('/elections/12/results')
  })
})

const RESULTS: ElectionResults = {
  id: 12,
  title: 'Committee',
  description: null,
  method: 'stv',
  seats: 2,
  closed_at: '2026-12-01T20:00:00Z',
  guild_name: 'Dev Server',
  candidates: [
    { id: 1, name: 'Andy' },
    { id: 2, name: 'Bea' },
    { id: 3, name: 'Coral' },
    { id: 4, name: 'Dmitri' },
  ],
  tally: {
    method: 'stv',
    seats: 2,
    ballots: 9,
    quota: 3,
    winners: [1, 3],
    tie_broken: true,
    rounds: [
      { candidates: [{ id: 1, votes: 4, status: 'elected' }, { id: 3, votes: 2, status: 'hopeful' }, { id: 2, votes: 2, status: 'hopeful' }, { id: 4, votes: 1, status: 'hopeful' }], exhausted: 0 },
      { candidates: [{ id: 1, votes: 3, status: 'elected' }, { id: 2, votes: 2.5, status: 'hopeful' }, { id: 3, votes: 2.25, status: 'hopeful' }, { id: 4, votes: 1, status: 'eliminated' }], exhausted: 0.25 },
      { candidates: [{ id: 1, votes: 3, status: 'elected' }, { id: 3, votes: 3.25, status: 'elected' }, { id: 2, votes: 2.5, status: 'eliminated' }, { id: 4, votes: 0, status: 'eliminated' }], exhausted: 0.25 },
    ],
  },
}

describe('results', () => {
  it('shows the winners, steps through the rounds and lists every round', async () => {
    const { user } = renderApp('/elections/12/results', { routes: { 'GET /api/v1/elections/12/results': RESULTS } })
    expect(await screen.findByRole('heading', { level: 1, name: 'Committee' })).toBeTruthy()
    expect(main().textContent).toContain('Ranked (STV), 2 seats · 9 ballots')
    expect(screen.getByText('1. Andy')).toBeTruthy()
    expect(screen.getByText('2. Coral')).toBeTruthy()
    expect(screen.getByText(/There was a tie/)).toBeTruthy()

    expect(screen.getByText('Round 3 of 3')).toBeTruthy()
    expect(screen.getByText(/Coral reaches the quota and is elected/)).toBeTruthy()
    expect(screen.getByText(/Bea has the fewest votes/)).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'Previous round' }))
    expect(screen.getByText(/Dmitri has the fewest votes/)).toBeTruthy()
    expect(screen.getByText(/0.3 votes have no next choice left/)).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'Previous round' }))
    expect(screen.getByText(/Andy reaches the quota/)).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Previous round' }).hasAttribute('disabled')).toBe(true)
    await user.click(screen.getByRole('button', { name: 'Next round' }))
    expect(screen.getByText('Round 2 of 3')).toBeTruthy()
    expect(screen.getByLabelText('Dmitri: 1 votes, out')).toBeTruthy()

    const table = screen.getByRole('table')
    const row = (name: string) => within(table).getByRole('rowheader', { name }).closest('tr')!.textContent
    expect(row('Andy')).toBe('Andy4 ✓33')
    expect(row('Dmitri')).toBe('Dmitri11 out–')
    expect(row('Coral')).toBe('Coral22.33.3 ✓')
  })

  it('shows a one-round count with no quota', async () => {
    renderApp('/elections/9/results', {
      routes: {
        'GET /api/v1/elections/9/results': {
          ...RESULTS,
          id: 9,
          method: 'approval',
          seats: 1,
          tally: { method: 'approval', seats: 1, ballots: 3, quota: null, winners: [2], tie_broken: false, rounds: [{ candidates: [{ id: 2, votes: 3, status: 'elected' }, { id: 1, votes: 1, status: 'hopeful' }], exhausted: 0 }] },
        },
      },
    })
    expect(await screen.findByRole('heading', { name: 'Winner' })).toBeTruthy()
    expect(screen.getByText('Each bar is how many voters ticked that candidate.')).toBeTruthy()
    expect(screen.queryByRole('table')).toBeNull()
    expect(screen.queryByText(/Round 1 of/)).toBeNull()
  })

  it('says when nobody voted', async () => {
    renderApp('/elections/9/results', {
      routes: {
        'GET /api/v1/elections/9/results': {
          ...RESULTS,
          method: 'plurality',
          tally: { method: 'plurality', seats: 1, ballots: 0, quota: null, winners: [], tie_broken: false, rounds: [{ candidates: [], exhausted: 0 }] },
        },
      },
    })
    expect(await screen.findByText('No ballots were cast.')).toBeTruthy()
    expect(screen.getByText('Each bar is how many voters picked that candidate.')).toBeTruthy()
  })

  it('says results wait until voting closes', async () => {
    renderApp('/elections/12/results', { routes: { 'GET /api/v1/elections/12/results': fail(403, 'Results are shown when voting closes.') } })
    expect(await screen.findByText('Results are shown when voting closes.')).toBeTruthy()
  })
})
