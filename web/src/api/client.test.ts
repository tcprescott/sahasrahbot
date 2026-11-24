import { describe, expect, it } from 'vitest'
import { fakeApi, reply } from '../test/fakeApi'
import { ApiError, api, errorMessage, loginUrl, unwrap } from './client'

describe('unwrap', () => {
  it('returns the body of a success', () => {
    expect(unwrap({ data: { a: 1 }, response: new Response('{}') })).toEqual({ a: 1 })
  })

  it('accepts an empty 204', () => {
    expect(unwrap({ data: undefined, response: new Response(null, { status: 204 }) })).toBeUndefined()
  })

  it("throws ApiError with the server's message and status", () => {
    const failed = () => unwrap({ error: { error: 'No such preset.' }, response: new Response('', { status: 404 }) })
    expect(failed).toThrow(ApiError)
    expect(failed).toThrow('No such preset.')
    try {
      failed()
    } catch (e) {
      expect((e as ApiError).status).toBe(404)
    }
  })
})

describe('errorMessage', () => {
  it.each([
    [{ error: 'Readable' }, 400, 'Readable'],
    [{ error: 42 }, 500, 'Something went wrong. Try again.'],
    [undefined, 0, "Couldn't reach SahasrahBot. Check your connection and try again."],
    ['<html>', 502, 'Something went wrong. Try again.'],
  ])('%j with status %i reads "%s"', (body, status, message) => {
    expect(errorMessage(body, status)).toBe(message)
  })
})

describe('loginUrl', () => {
  it('comes back to the given path, or this page', () => {
    window.history.replaceState({}, '', '/ranked_choice/4?x=1')
    expect(loginUrl()).toBe('/login/?next=%2Franked_choice%2F4%3Fx%3D1')
    expect(loginUrl('/me')).toBe('/login/?next=%2Fme')
  })
})

describe('requests', () => {
  it('marks changes with the CSRF header and leaves reads alone', async () => {
    const server = fakeApi({ 'POST /api/v1/me/purge': reply(204) })
    await api.GET('/api/v1/session')
    await api.POST('/api/v1/me/purge')
    const [read, write] = server.calls
    expect(read?.headers.get('X-Requested-With')).toBeNull()
    expect(write?.headers.get('X-Requested-With')).toBe('SahasrahBot')
  })
})
