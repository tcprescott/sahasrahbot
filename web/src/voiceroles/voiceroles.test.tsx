import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { VoiceRoles } from '../api/client'
import { fail, reply, USERS } from '../test/fakeApi'
import { main, renderApp } from '../test/renderApp'

const LIST = 'GET /api/v1/servers/5/voice-roles'

const DATA: VoiceRoles = {
  voice_roles: [
    { id: 1, voice_channel_id: '10', voice_channel_name: 'Race 1', role_id: '21', role_name: '@In Race 1', problem: null },
    { id: 2, voice_channel_id: '99', voice_channel_name: null, role_id: '21', role_name: '@In Race 1', problem: 'This voice channel no longer exists.' },
  ],
  voice_channels: [
    { id: '10', name: 'Race 1' },
    { id: '11', name: 'Race 2' },
  ],
  roles: [
    { id: '20', name: '@Staff', assignable: false },
    { id: '21', name: '@In Race 1', assignable: true },
    { id: '22', name: '@In Race 2', assignable: true },
  ],
}

function open(routes: Record<string, unknown> = {}) {
  return renderApp('/servers/5/voice-roles', { signedIn: USERS.alice, routes: { [LIST]: DATA, ...routes } })
}

describe('Voice roles tab', () => {
  it('lists the voice roles and flags the broken ones', async () => {
    open()
    const page = main()
    expect(await within(page).findByText('Race 1')).toBeTruthy()
    expect(within(page).getByText('Deleted channel')).toBeTruthy()
    expect(within(page).getByText(/This voice channel no longer exists/)).toBeTruthy()
    expect(within(page).getAllByText('@In Race 1')).toHaveLength(2)
  })

  it('shows an empty state', async () => {
    open({ [LIST]: { ...DATA, voice_roles: [] } })
    expect(await screen.findByText('No voice roles yet')).toBeTruthy()
  })

  it('adds a voice role with only the roles the bot can give', async () => {
    const added = { id: 3, voice_channel_id: '11', voice_channel_name: 'Race 2', role_id: '22', role_name: '@In Race 2', problem: null }
    const { api } = open({ 'POST /api/v1/servers/5/voice-roles': reply(201, added) })
    fireEvent.click(await screen.findByRole('button', { name: 'Add voice role' }))
    const dialog = await screen.findByRole('dialog', { name: 'Add voice role' })
    const roleSelect = within(dialog).getByLabelText('Role to give')
    expect(within(roleSelect).queryByText('@Staff')).toBeNull()
    expect(within(dialog).getByText(/Only roles below SahasrahBot’s role are listed/)).toBeTruthy()

    fireEvent.click(within(dialog).getByRole('button', { name: 'Add voice role' }))
    expect(await within(dialog).findByText('Pick a voice channel and a role.')).toBeTruthy()
    expect(api.callsTo('POST /api/v1/servers/5/voice-roles')).toHaveLength(0)

    fireEvent.change(within(dialog).getByLabelText('Voice channel'), { target: { value: '11' } })
    fireEvent.change(roleSelect, { target: { value: '22' } })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Add voice role' }))
    expect(await screen.findByText(/Race 2 now gives @In Race 2/)).toBeTruthy()
    expect(api.callsTo('POST /api/v1/servers/5/voice-roles')[0]?.body).toEqual({ voice_channel_id: '11', role_id: '22' })
    expect(api.callsTo(LIST)).toHaveLength(2)
  })

  it("shows the server's reason when adding fails", async () => {
    open({ 'POST /api/v1/servers/5/voice-roles': fail(400, 'Race 1 already gives @In Race 1.') })
    fireEvent.click(await screen.findByRole('button', { name: 'Add voice role' }))
    const dialog = await screen.findByRole('dialog', { name: 'Add voice role' })
    fireEvent.change(within(dialog).getByLabelText('Voice channel'), { target: { value: '10' } })
    fireEvent.change(within(dialog).getByLabelText('Role to give'), { target: { value: '21' } })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Add voice role' }))
    expect(await within(dialog).findByText('Race 1 already gives @In Race 1.')).toBeTruthy()
  })

  it('removes a voice role after confirming', async () => {
    const { api, user } = open({ 'DELETE /api/v1/servers/5/voice-roles/1': reply(204) })
    await user.click(await screen.findByRole('button', { name: 'More for Race 1 and @In Race 1' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Remove' }))
    expect(await screen.findByText(/Race 1 will stop giving @In Race 1/)).toBeTruthy()
    await user.click(await screen.findByRole('button', { name: 'Remove' }))
    await waitFor(() => expect(api.callsTo('DELETE /api/v1/servers/5/voice-roles/1')).toHaveLength(1))
    await waitFor(() => expect(api.callsTo(LIST)).toHaveLength(2))
  })

  it('says when you are not an admin there', async () => {
    open({ [LIST]: fail(403, 'Only administrators of that server can manage its voice roles.') })
    expect(await screen.findByText('Only administrators of that server can manage its voice roles.')).toBeTruthy()
  })
})
