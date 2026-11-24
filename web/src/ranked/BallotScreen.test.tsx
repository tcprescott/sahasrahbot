import { screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { Election } from '../api/client'
import { fail, USERS } from '../test/fakeApi'
import { main, renderApp } from '../test/renderApp'

const ELECTION = '/api/v1/ranked-choice/7'
const BALLOT = `${ELECTION}/ballot`

const election = (overrides: Partial<Election> = {}): Election => ({
  id: 7,
  title: 'Best boss',
  description: null,
  private: false,
  seats: 1,
  candidates: [
    { id: 1, name: 'Agahnim' },
    { id: 2, name: 'Moldorm' },
    { id: 3, name: 'Trinexx' },
  ],
  ballot: null,
  ...overrides,
})

const open = (overrides: Partial<Election> = {}, routes = {}) =>
  renderApp('/ranked_choice/7', { signedIn: USERS.alice, routes: { [`GET ${ELECTION}`]: election(overrides), ...routes } })

const ranked = () => {
  const panel = screen.getByRole('heading', { name: 'Your ranking' }).closest('section')!
  return within(panel)
    .queryAllByRole('listitem')
    .map((row) => row.querySelector('.ballot__name')?.textContent)
}

describe('ballot', () => {
  it.each([
    [{}, 'One winner will be chosen.'],
    [{ seats: 3 }, '3 winners will be chosen.'],
    [{ description: 'Vote for your favourite.' }, 'Vote for your favourite.'],
  ])('explains the election (%j)', async (overrides, lede) => {
    open(overrides)
    expect(await screen.findByRole('heading', { level: 1, name: 'Best boss' })).toBeTruthy()
    expect(main().textContent).toContain(lede)
  })

  it('ranks, reorders and unranks candidates', async () => {
    const { user } = open()
    await user.click(await screen.findByRole('button', { name: 'Rank Trinexx' }))
    await user.click(screen.getByRole('button', { name: 'Rank Agahnim' }))
    expect(ranked()).toEqual(['Trinexx', 'Agahnim'])
    expect(screen.getByText('Not submitted')).toBeTruthy()

    expect(screen.getByRole('button', { name: 'Move Trinexx up' }).hasAttribute('disabled')).toBe(true)
    expect(screen.getByRole('button', { name: 'Move Agahnim down' }).hasAttribute('disabled')).toBe(true)
    await user.click(screen.getByRole('button', { name: 'Move Agahnim up' }))
    expect(ranked()).toEqual(['Agahnim', 'Trinexx'])
    await user.click(screen.getByRole('button', { name: 'Move Agahnim down' }))
    expect(ranked()).toEqual(['Trinexx', 'Agahnim'])

    await user.click(screen.getByRole('button', { name: 'Unrank Trinexx' }))
    expect(ranked()).toEqual(['Agahnim'])
    expect(screen.getByRole('button', { name: 'Rank Trinexx' })).toBeTruthy()
  })

  it('hides Not ranked once everyone is ranked, and Clear empties the ranking', async () => {
    const { user } = open()
    for (const name of ['Agahnim', 'Moldorm', 'Trinexx']) await user.click(await screen.findByRole('button', { name: `Rank ${name}` }))
    expect(screen.queryByRole('heading', { name: 'Not ranked' })).toBeNull()
    await user.click(screen.getByRole('button', { name: 'Clear' }))
    expect(ranked()).toEqual([])
    expect(screen.getByText('Pick candidates below to rank them.')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Submit ballot' }).hasAttribute('disabled')).toBe(true)
  })

  it('submits the ranking and then shows the ballot as cast', async () => {
    const { user, api } = open({}, { [`POST ${BALLOT}`]: { ok: true } })
    await user.click(await screen.findByRole('button', { name: 'Rank Moldorm' }))
    await user.click(screen.getByRole('button', { name: 'Rank Agahnim' }))
    api.on(`GET ${ELECTION}`, election({ ballot: [2, 1] }))
    await user.click(screen.getByRole('button', { name: 'Submit ballot' }))

    expect(await screen.findByText(/your ballot is in/)).toBeTruthy()
    expect(api.callsTo(`POST ${BALLOT}`)[0]?.body).toEqual({ ranking: [2, 1] })
    expect(screen.getByText('Submitted')).toBeTruthy()
    const cast = screen.getByRole('heading', { name: 'Your ballot' }).closest('section')!
    expect(within(cast).getAllByRole('listitem').map((li) => li.textContent)).toEqual(['1Moldorm', '2Agahnim'])
    expect(screen.queryByRole('button', { name: /Rank/ })).toBeNull()
  })

  it('shows why the ballot was refused and lets the voter try again', async () => {
    const { user } = open({}, { [`POST ${BALLOT}`]: fail(400, 'This election has closed.') })
    await user.click(await screen.findByRole('button', { name: 'Rank Moldorm' }))
    await user.click(screen.getByRole('button', { name: 'Submit ballot' }))
    expect((await screen.findByRole('alert')).textContent).toContain('This election has closed.')
    await waitFor(() => expect(screen.getByRole('button', { name: 'Submit ballot' }).hasAttribute('disabled')).toBe(false))
    expect(ranked()).toEqual(['Moldorm'])
  })

  it('says when the election is gone', async () => {
    renderApp('/ranked_choice/7', { signedIn: USERS.alice, routes: { [`GET ${ELECTION}`]: fail(404, '') } })
    expect(await screen.findByText("This election doesn't exist or has closed.")).toBeTruthy()
  })

  it("passes on the server's reason when the voter isn't allowed in", async () => {
    renderApp('/ranked_choice/7', {
      signedIn: USERS.alice,
      routes: { [`GET ${ELECTION}`]: fail(403, 'Only members of Voters can vote in this election.') },
    })
    expect(await screen.findByText("You can't open this")).toBeTruthy()
    expect(main().textContent).toContain('Only members of Voters can vote')
  })
})
