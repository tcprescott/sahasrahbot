import { screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { Election } from '../api/client'
import { fail, USERS } from '../test/fakeApi'
import { currentPath, main, renderApp } from '../test/renderApp'

const BALLOT = '/api/v1/elections/7/ballot'

const election = (overrides: Partial<Election> = {}): Election => ({
  id: 7,
  title: 'Best boss',
  description: null,
  private: false,
  method: 'stv',
  seats: 1,
  closes_at: null,
  guild_name: 'Dev Server',
  voted_at: null,
  candidates: [
    { id: 1, name: 'Agahnim' },
    { id: 2, name: 'Moldorm' },
    { id: 3, name: 'Trinexx' },
  ],
  ballot: null,
  ...overrides,
})

const open = (overrides: Partial<Election> = {}, routes = {}) =>
  renderApp('/ranked_choice/7', { signedIn: USERS.alice, routes: { [`GET ${BALLOT}`]: election(overrides), ...routes } })

const ranked = () =>
  within(screen.getByRole('list', { name: 'Your ranking' }))
    .queryAllByRole('listitem')
    .map((row) => row.querySelector('.ballot__name')?.textContent)

describe('ranked ballot', () => {
  it.each([
    [{}, 'One will win.'],
    [{ seats: 3 }, '3 will win.'],
    [{ description: 'Vote for your favourite.' }, 'Vote for your favourite.'],
  ])('explains the election (%j)', async (overrides, lede) => {
    open(overrides)
    expect(await screen.findByRole('heading', { level: 1, name: 'Best boss' })).toBeTruthy()
    expect(main().textContent).toContain(lede)
    expect(main().textContent).toContain('Dev Server')
    expect(main().textContent).toContain('until an admin ends the vote')
  })

  it('says when voting closes', async () => {
    open({ closes_at: '2030-01-02T03:04:00Z' })
    expect(await screen.findByText(/Closes .*2030.* You can change your ballot until then/)).toBeTruthy()
  })

  it('ranks by tapping, reorders with the arrows and takes out with a second tap', async () => {
    const { user } = open()
    await user.click(await screen.findByRole('button', { name: 'Rank Trinexx' }))
    await user.click(screen.getByRole('button', { name: 'Rank Agahnim' }))
    expect(ranked()).toEqual(['Trinexx', 'Agahnim'])
    expect(screen.getByText('2 ranked')).toBeTruthy()
    expect(screen.getByText('2nd choice')).toBeTruthy()
    expect(screen.getByText('Not ranked')).toBeTruthy()

    expect(screen.getByRole('button', { name: 'Move Trinexx up' }).hasAttribute('disabled')).toBe(true)
    expect(screen.getByRole('button', { name: 'Move Agahnim down' }).hasAttribute('disabled')).toBe(true)
    await user.click(screen.getByRole('button', { name: 'Move Agahnim up' }))
    expect(ranked()).toEqual(['Agahnim', 'Trinexx'])
    await user.click(screen.getByRole('button', { name: 'Move Agahnim down' }))
    expect(ranked()).toEqual(['Trinexx', 'Agahnim'])

    await user.click(screen.getByRole('button', { name: 'Take Trinexx out of your ranking' }))
    expect(ranked()).toEqual(['Agahnim'])
    expect(screen.getByRole('button', { name: 'Rank Trinexx' })).toBeTruthy()
  })

  it('Clear empties the ranking', async () => {
    const { user } = open()
    for (const name of ['Agahnim', 'Moldorm', 'Trinexx']) await user.click(await screen.findByRole('button', { name: `Rank ${name}` }))
    expect(screen.queryByRole('list', { name: 'Not ranked' })).toBeNull()
    await user.click(screen.getByRole('button', { name: 'Clear' }))
    expect(ranked()).toEqual([])
    expect(screen.getByText('None ranked')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Submit ballot' }).hasAttribute('disabled')).toBe(true)
  })

  it('submits the ranking and then shows the ballot as cast', async () => {
    const { user, api } = open({}, { [`PUT ${BALLOT}`]: election({ ballot: [2, 1] }) })
    await user.click(await screen.findByRole('button', { name: 'Rank Moldorm' }))
    await user.click(screen.getByRole('button', { name: 'Rank Agahnim' }))
    api.on(`GET ${BALLOT}`, election({ ballot: [2, 1], voted_at: '2026-11-24T16:00:00Z' }))
    await user.click(screen.getByRole('button', { name: 'Submit ballot' }))

    expect(await screen.findByText(/Your ballot is in/)).toBeTruthy()
    expect(api.callsTo(`PUT ${BALLOT}`)[0]?.body).toEqual({ choices: [2, 1] })
    expect(screen.getByText(/^Submitted /)).toBeTruthy()
    const cast = screen.getByRole('heading', { name: 'Your ballot' }).closest('section')!
    expect(within(cast).getAllByRole('listitem').map((li) => li.textContent)).toEqual(['1Moldorm', '2Agahnim'])
    expect(screen.queryByRole('button', { name: /^Rank/ })).toBeNull()
  })

  it('shows why the ballot was refused and lets the voter try again', async () => {
    const { user } = open({}, { [`PUT ${BALLOT}`]: fail(400, 'This election has closed.') })
    await user.click(await screen.findByRole('button', { name: 'Rank Moldorm' }))
    await user.click(screen.getByRole('button', { name: 'Submit ballot' }))
    expect((await screen.findByRole('alert')).textContent).toContain('This election has closed.')
    await waitFor(() => expect(screen.getByRole('button', { name: 'Submit ballot' }).hasAttribute('disabled')).toBe(false))
    expect(ranked()).toEqual(['Moldorm'])
  })
})

describe('changing a ballot', () => {
  it('shows the ballot read-only, then lets the voter change it or keep it', async () => {
    const { user, api } = open({ ballot: [3, 1], closes_at: '2030-01-02T03:04:00Z' }, { [`PUT ${BALLOT}`]: election({ ballot: [1] }) })
    expect(await screen.findByText(/You can change it until .*2030/)).toBeTruthy()
    expect(screen.getByText('Submitted')).toBeTruthy()

    await user.click(screen.getByRole('button', { name: 'Change ballot' }))
    expect(ranked()).toEqual(['Trinexx', 'Agahnim'])
    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(screen.getByRole('heading', { name: 'Your ballot' })).toBeTruthy()

    await user.click(screen.getByRole('button', { name: 'Change ballot' }))
    await user.click(screen.getByRole('button', { name: 'Take Trinexx out of your ranking' }))
    api.on(`GET ${BALLOT}`, election({ ballot: [1] }))
    await user.click(screen.getByRole('button', { name: 'Update ballot' }))
    expect(await screen.findByRole('heading', { name: 'Your ballot' })).toBeTruthy()
    expect(api.callsTo(`PUT ${BALLOT}`)[0]?.body).toEqual({ choices: [1] })
  })
})

describe('approval and plurality ballots', () => {
  it('ticks any number of tiles for approval', async () => {
    const { user, api } = open({ method: 'approval' }, { [`PUT ${BALLOT}`]: election({ method: 'approval', ballot: [1, 3] }) })
    expect(await screen.findByText(/Tick every option/)).toBeTruthy()
    await user.click(screen.getByRole('checkbox', { name: 'Agahnim' }))
    await user.click(screen.getByRole('checkbox', { name: 'Moldorm' }))
    await user.click(screen.getByRole('checkbox', { name: 'Trinexx' }))
    await user.click(screen.getByRole('checkbox', { name: 'Moldorm' }))
    api.on(`GET ${BALLOT}`, election({ method: 'approval', ballot: [1, 3] }))
    await user.click(screen.getByRole('button', { name: 'Submit ballot' }))
    expect(api.callsTo(`PUT ${BALLOT}`)[0]?.body).toEqual({ choices: [1, 3] })
    const cast = (await screen.findByRole('heading', { name: 'Your ballot' })).closest('section')!
    expect(within(cast).getAllByRole('listitem').map((li) => li.textContent)).toEqual(['Agahnim', 'Trinexx'])
  })

  it('picks exactly one tile for plurality', async () => {
    const { user, api } = open({ method: 'plurality' }, { [`PUT ${BALLOT}`]: election({ method: 'plurality', ballot: [2] }) })
    expect(await screen.findByText('Pick one. The most votes wins.')).toBeTruthy()
    await user.click(screen.getByRole('radio', { name: 'Agahnim' }))
    await user.click(screen.getByRole('radio', { name: 'Moldorm' }))
    expect((screen.getByRole('radio', { name: 'Agahnim' }) as HTMLInputElement).checked).toBe(false)
    await user.click(screen.getByRole('button', { name: 'Submit vote' }))
    expect(api.callsTo(`PUT ${BALLOT}`)[0]?.body).toEqual({ choices: [2] })
  })
})

describe('when voting is not possible', () => {
  it('sends a voter to the results once voting has closed', async () => {
    const { user } = renderApp('/ranked_choice/7', { signedIn: USERS.alice, routes: { [`GET ${BALLOT}`]: fail(404, 'This election has closed.') } })
    expect(await screen.findByText('Voting has closed')).toBeTruthy()
    await user.click(screen.getByRole('link', { name: 'See the results' }))
    expect(currentPath()).toBe('/elections/7/results')
  })

  it('says when the election is gone', async () => {
    renderApp('/ranked_choice/7', { signedIn: USERS.alice, routes: { [`GET ${BALLOT}`]: fail(404, '') } })
    expect(await screen.findByText("This election doesn't exist.")).toBeTruthy()
  })

  it("passes on the server's reason when the voter isn't allowed in", async () => {
    renderApp('/ranked_choice/7', {
      signedIn: USERS.alice,
      routes: { [`GET ${BALLOT}`]: fail(403, "You don't have the role this election needs to vote.") },
    })
    expect(await screen.findByText("You can't open this")).toBeTruthy()
    expect(main().textContent).toContain("You don't have the role")
  })
})
