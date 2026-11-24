import { screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { TriforcePool, TriforceText } from '../api/client'
import type { Call } from '../test/fakeApi'
import { fail, USERS } from '../test/fakeApi'
import { currentPath, main, renderApp } from '../test/renderApp'

const POOL = '/api/v1/triforce-texts/sgl'
const MODERATION = `${POOL}/moderation`

const text = (id: number, status: TriforceText['status'], lines = ['HELLO', 'WORLD', '']): TriforceText => ({
  id,
  lines,
  status,
  submitted: '2026-11-20T12:00:00Z',
  author: `runner${id}`,
})

const pool = (overrides: Partial<TriforcePool> = {}): TriforcePool => ({
  pool: 'sgl',
  max_line_length: 19,
  is_moderator: false,
  mine: [],
  ...overrides,
})

const line = (n: number) => screen.getByRole('textbox', { name: `Line ${n}` })

describe('writing a triforce text', () => {
  it('previews the text as it is typed', async () => {
    const { user } = renderApp('/triforcetexts/sgl', { signedIn: USERS.alice, routes: { [`GET ${POOL}`]: pool() } })
    expect(await screen.findByRole('img', { name: 'Triforce text: blank' })).toBeTruthy()
    await user.type(line(1), 'I AM ERROR')
    await user.type(line(3), '↑↓→←')
    expect(screen.getByRole('img', { name: 'Triforce text: I AM ERROR / ↑↓→←' })).toBeTruthy()
    expect(main().textContent).toContain('10/19')
  })

  it('flags lines the game cannot show and blocks sending them', async () => {
    const { user } = renderApp('/triforcetexts/sgl', { signedIn: USERS.alice, routes: { [`GET ${POOL}`]: pool() } })
    const send = await screen.findByRole('button', { name: 'Send for review' })
    expect(send.hasAttribute('disabled')).toBe(true) // blank

    await user.type(line(1), 'semicolons;')
    expect(line(1).getAttribute('aria-invalid')).toBe('true')
    expect(screen.getByText("Has a character the game can't show.")).toBeTruthy()
    expect(send.hasAttribute('disabled')).toBe(true)

    await user.clear(line(1))
    await user.type(line(1), 'A'.repeat(20))
    expect(screen.getByText('Too long: 19 characters at most.')).toBeTruthy()
    expect(main().querySelector('.char-count--over')?.textContent).toBe('20/19')

    await user.clear(line(1))
    await user.type(line(1), 'OK')
    expect(line(1).getAttribute('aria-invalid')).toBe('false')
    expect(send.hasAttribute('disabled')).toBe(false)
  })

  it('sends the three lines, clears the form and lists the text', async () => {
    const { user, api } = renderApp('/triforcetexts/sgl', {
      signedIn: USERS.alice,
      routes: { [`GET ${POOL}`]: pool(), [`POST ${POOL}/submissions`]: text(9, 'pending') },
    })
    await user.type(await screen.findByRole('textbox', { name: 'Line 1' }), 'HELLO')
    await user.type(line(2), 'WORLD')
    api.on(`GET ${POOL}`, pool({ mine: [text(9, 'pending')] }))
    await user.click(screen.getByRole('button', { name: 'Send for review' }))

    expect(await screen.findByText(/The event's staff review every text/)).toBeTruthy()
    expect(api.callsTo(`POST ${POOL}/submissions`)[0]?.body).toEqual({ lines: ['HELLO', 'WORLD', ''] })
    expect((line(1) as HTMLInputElement).value).toBe('')
    const sent = await screen.findByRole('heading', { name: "What you've sent" })
    expect(within(sent.closest('section')!).getByText('Waiting for review')).toBeTruthy()
  })

  it('shows why a text was refused and keeps it', async () => {
    const { user } = renderApp('/triforcetexts/sgl', {
      signedIn: USERS.alice,
      routes: { [`GET ${POOL}`]: pool(), [`POST ${POOL}/submissions`]: fail(400, 'You have sent too many texts today.') },
    })
    await user.type(await screen.findByRole('textbox', { name: 'Line 1' }), 'HELLO')
    await user.click(screen.getByRole('button', { name: 'Send for review' }))
    expect((await screen.findByRole('alert')).textContent).toContain('too many texts today')
    expect((line(1) as HTMLInputElement).value).toBe('HELLO')
  })

  it.each([
    ['approved', 'Approved'],
    ['rejected', 'Not used'],
  ] as const)('labels a %s text "%s"', async (status, label) => {
    renderApp('/triforcetexts/sgl', { signedIn: USERS.alice, routes: { [`GET ${POOL}`]: pool({ mine: [text(1, status)] }) } })
    expect(await screen.findByText(label)).toBeTruthy()
  })

  it('links moderators to the review page, and nobody else', async () => {
    renderApp('/triforcetexts/sgl', { signedIn: USERS.alice, routes: { [`GET ${POOL}`]: pool({ is_moderator: true }) } })
    expect((await screen.findByRole('link', { name: 'Review submissions' })).getAttribute('href')).toBe('/triforcetexts/sgl/moderation')
  })

  it('has no review link for a regular player', async () => {
    renderApp('/triforcetexts/sgl', { signedIn: USERS.alice, routes: { [`GET ${POOL}`]: pool() } })
    await screen.findByRole('heading', { level: 1, name: 'Triforce text' })
    expect(screen.queryByRole('link', { name: 'Review submissions' })).toBeNull()
  })
})

describe('moderating triforce texts', () => {
  const byStatus = (texts: Record<string, TriforceText[]>) => (call: Call) => {
    const status = call.query.get('status') ?? 'pending'
    return { pool: 'sgl', status, texts: texts[status] ?? [] }
  }

  it('shows texts waiting for review first', async () => {
    const { api } = renderApp('/triforcetexts/sgl/moderation', {
      signedIn: USERS.alice,
      routes: { [`GET ${MODERATION}`]: byStatus({ pending: [text(1, 'pending')] }) },
    })
    expect(await screen.findByText('runner1')).toBeTruthy()
    expect(api.callsTo(`GET ${MODERATION}`)[0]?.query.get('status')).toBe('pending')
    expect(screen.getByRole('button', { name: 'To review' }).getAttribute('aria-pressed')).toBe('true')
  })

  it('switches between filters, keeping the choice in the URL', async () => {
    const { user } = renderApp('/triforcetexts/sgl/moderation', {
      signedIn: USERS.alice,
      routes: { [`GET ${MODERATION}`]: byStatus({ all: [text(1, 'approved'), text(2, 'rejected')] }) },
    })
    expect(await screen.findByText("You're all caught up.")).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'Approved' }))
    expect(currentPath()).toBe('/triforcetexts/sgl/moderation?approved=approved')
    expect(await screen.findByText('Nothing here')).toBeTruthy()

    await user.click(screen.getByRole('button', { name: 'All' }))
    expect(await screen.findByText('runner2')).toBeTruthy()
    // on All, each text says where it stands, and the button for its current state is off
    const rows = within(main().querySelector('.triforce-list')!).getAllByRole('listitem')
    expect(within(rows[0]!).getByText('Approved', { selector: '.chip' })).toBeTruthy()
    expect(within(rows[0]!).getByRole('button', { name: 'Approve' }).hasAttribute('disabled')).toBe(true)
    expect(within(rows[1]!).getByText('Not used', { selector: '.chip' })).toBeTruthy()
    expect(within(rows[1]!).getByRole('button', { name: "Don't use" }).hasAttribute('disabled')).toBe(true)

    await user.click(screen.getByRole('button', { name: 'To review' }))
    expect(currentPath()).toBe('/triforcetexts/sgl/moderation')
  })

  it.each([
    ['Approve', true],
    ["Don't use", false],
  ])('%s sends the decision and reloads the list', async (button, approved) => {
    const pending = { pending: [text(1, 'pending')] }
    const { user, api } = renderApp('/triforcetexts/sgl/moderation', {
      signedIn: USERS.alice,
      routes: { [`GET ${MODERATION}`]: byStatus(pending), [`POST ${MODERATION}/1`]: text(1, approved ? 'approved' : 'rejected') },
    })
    await screen.findByText('runner1')
    api.on(`GET ${MODERATION}`, byStatus({}))
    await user.click(screen.getByRole('button', { name: button }))

    expect(await screen.findByText("You're all caught up.")).toBeTruthy()
    expect(api.callsTo(`POST ${MODERATION}/1`)[0]?.body).toEqual({ approved })
  })

  it('shows why a decision failed', async () => {
    const { user } = renderApp('/triforcetexts/sgl/moderation', {
      signedIn: USERS.alice,
      routes: {
        [`GET ${MODERATION}`]: byStatus({ pending: [text(1, 'pending')] }),
        [`POST ${MODERATION}/1`]: fail(403, "You don't moderate this pool."),
      },
    })
    await user.click(await screen.findByRole('button', { name: 'Approve' }))
    expect((await screen.findByRole('alert')).textContent).toContain("You don't moderate this pool.")
    await waitFor(() => expect(screen.getByRole('button', { name: 'Approve' }).hasAttribute('disabled')).toBe(false))
  })

  it('names an unknown author', async () => {
    renderApp('/triforcetexts/sgl/moderation', {
      signedIn: USERS.alice,
      routes: { [`GET ${MODERATION}`]: byStatus({ pending: [{ ...text(1, 'pending'), author: null }] }) },
    })
    expect(await screen.findByText('Unknown')).toBeTruthy()
  })
})
