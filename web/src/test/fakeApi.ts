/**
 * A fake SahasrahBot API for screen tests: stubs `fetch` with a table of
 * routes ("GET /api/v1/me") and records every call, so a test can say what the
 * server answers and check what the screen sent.
 */
import { vi } from 'vitest'
import type { SessionUser } from '../api/client'

export interface Call {
  method: string
  path: string
  query: URLSearchParams
  body: unknown
  headers: Headers
}

/** An answer with a status other than 200. A plain value is a 200 with that JSON body. */
export class Reply {
  constructor(
    readonly status: number,
    readonly body?: unknown,
  ) {}
}

export const reply = (status: number, body?: unknown) => new Reply(status, body)
export const fail = (status: number, error: string) => new Reply(status, { error })

type Answer = unknown
export type Handler = Answer | ((call: Call) => Answer | Promise<Answer>)

export interface FakeApi {
  calls: Call[]
  /** Calls to one route, e.g. `api.callsTo('POST /api/v1/me/purge')`. */
  callsTo: (route: string) => Call[]
  /** Replace or add a route's answer mid-test. */
  on: (route: string, handler: Handler) => void
}

export const USERS = {
  alice: { id: '91000000000000001', name: 'alice', avatar_url: null },
  bob: { id: '91000000000000002', name: 'Bob the Builder', avatar_url: 'https://cdn.test/bob.png' },
} satisfies Record<string, SessionUser>

/**
 * Stub `fetch`. `user` answers /api/v1/session (null: signed out); a route left
 * out answers 404 with an error naming it, which the screen shows.
 */
export function fakeApi(routes: Record<string, Handler> = {}, user: SessionUser | null = null): FakeApi {
  const table = new Map<string, Handler>([['GET /api/v1/session', { user }], ...Object.entries(routes)])
  const calls: Call[] = []

  vi.stubGlobal('fetch', async (input: Request) => {
    const url = new URL(input.url)
    const text = await input.text()
    const call: Call = {
      method: input.method,
      path: url.pathname,
      query: url.searchParams,
      body: text ? JSON.parse(text) : undefined,
      headers: input.headers,
    }
    calls.push(call)
    const route = `${call.method} ${call.path}`
    const handler = table.get(route)
    if (handler === undefined) return json(404, { error: `No fake for ${route}` })
    const answer = typeof handler === 'function' ? await handler(call) : handler
    if (answer instanceof Reply) return answer.body === undefined ? new Response(null, { status: answer.status }) : json(answer.status, answer.body)
    return json(200, answer)
  })

  return {
    calls,
    callsTo: (route) => calls.filter((c) => `${c.method} ${c.path}` === route),
    on: (route, handler) => void table.set(route, handler),
  }
}

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

/** A handler that never answers: the screen stays loading. */
export const never = () => new Promise<never>(() => {})
