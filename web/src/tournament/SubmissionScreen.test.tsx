import { screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { SubmissionForm } from '../api/client'
import { fail, USERS } from '../test/fakeApi'
import { renderApp } from '../test/renderApp'

const FORM = '/api/v1/tournaments/alttprleague/submission-form'
const SUBMIT = '/api/v1/tournaments/alttprleague/submissions'

const form: SubmissionForm = {
  event: 'alttprleague',
  fields: [
    {
      key: 'preset',
      label: 'Preset',
      options: [
        { value: 'open', label: 'Open' },
        { value: 'standard', label: 'Standard' },
      ],
    },
    { key: 'dungeon', label: 'Dungeon items', options: [{ value: 'mcs', label: 'Maps, compasses, small keys' }] },
  ],
}

const open = (path = '/submit/alttprleague?episode_id=12345', routes = {}) =>
  renderApp(path, { signedIn: USERS.alice, routes: { [`GET ${FORM}`]: form, ...routes } })

describe('race settings form', () => {
  it("fills the episode in from the link and needs every setting", async () => {
    const { user } = open()
    const episode = await screen.findByRole('textbox', { name: 'SpeedGaming episode' })
    expect((episode as HTMLInputElement).value).toBe('12345')
    const submit = screen.getByRole('button', { name: 'Submit settings' })
    expect(submit.hasAttribute('disabled')).toBe(true)

    const preset = screen.getByRole('combobox', { name: 'Preset' })
    expect(within(preset).getAllByRole('option').map((o) => o.textContent)).toEqual(['Choose…', 'Open', 'Standard'])
    await user.selectOptions(preset, 'standard')
    expect(submit.hasAttribute('disabled')).toBe(true)
    await user.selectOptions(screen.getByRole('combobox', { name: 'Dungeon items' }), 'mcs')
    expect(submit.hasAttribute('disabled')).toBe(false)

    await user.clear(episode)
    await user.type(episode, '12a')
    expect(submit.hasAttribute('disabled')).toBe(true)
  })

  it('sends the settings and confirms who the race is', async () => {
    const { user, api } = open('/submit/alttprleague', {
      [`POST ${SUBMIT}`]: { event: 'alttprleague', episode_id: 777, versus: 'alice vs bob' },
    })
    await user.type(await screen.findByRole('textbox', { name: 'SpeedGaming episode' }), ' 777 ')
    await user.selectOptions(screen.getByRole('combobox', { name: 'Preset' }), 'open')
    await user.selectOptions(screen.getByRole('combobox', { name: 'Dungeon items' }), 'mcs')
    await user.click(screen.getByRole('button', { name: 'Submit settings' }))

    expect(await screen.findByText(/settings for alice vs bob are in/)).toBeTruthy()
    expect(api.callsTo(`POST ${SUBMIT}`)[0]?.body).toEqual({ episode_id: 777, settings: { preset: 'open', dungeon: 'mcs' } })
  })

  it('shows why the settings were refused', async () => {
    const { user } = open(undefined, { [`POST ${SUBMIT}`]: fail(400, "You aren't a player in episode 12345.") })
    await user.selectOptions(await screen.findByRole('combobox', { name: 'Preset' }), 'open')
    await user.selectOptions(screen.getByRole('combobox', { name: 'Dungeon items' }), 'mcs')
    await user.click(screen.getByRole('button', { name: 'Submit settings' }))
    expect((await screen.findByRole('alert')).textContent).toContain("You aren't a player in episode 12345.")
  })

  it("says when the event doesn't take settings here", async () => {
    renderApp('/submit/alttprleague', { signedIn: USERS.alice, routes: { [`GET ${FORM}`]: fail(404, '') } })
    expect(await screen.findByText("This event doesn't take race settings here.")).toBeTruthy()
  })
})
