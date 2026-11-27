/**
 * The typed client for SahasrahBot's JSON API (/api/v1). Types come from
 * src/api/schema.d.ts, generated from the backend's OpenAPI schema by
 * `npm run gen:api` (not committed; CI generates it).
 *
 * Signing in is the Quart app's Discord OAuth flow (/login/), which leaves a
 * session cookie; every call here sends it. Calls that change something carry
 * X-Requested-With, which the API requires so another site can't make them.
 */
import createClient from 'openapi-fetch'
import type { paths } from './schema'

export const CSRF_HEADER = 'X-Requested-With'

/**
 * Where the API and the sign-in routes live. Empty (the default) means this
 * origin, as on the website; a native wrapper would build with VITE_API_BASE.
 */
export const API_BASE: string = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, '') ?? ''

async function sameOriginFetch(request: Request): Promise<Response> {
  const next = new Request(request, { credentials: 'same-origin' })
  if (!['GET', 'HEAD'].includes(next.method)) next.headers.set(CSRF_HEADER, 'SahasrahBot')
  return fetch(next)
}

export const api = createClient<paths>({ baseUrl: API_BASE, fetch: sameOriginFetch })

type Json<T> = T extends { content: { 'application/json': infer B } } ? B : never

/** The JSON body a GET path answers with. */
export type GetBody<P extends keyof paths> = paths[P] extends { get: { responses: { 200: infer R } } } ? Json<R> : never

export type SessionUser = NonNullable<GetBody<'/api/v1/session'>['user']>
export type Profile = GetBody<'/api/v1/me'>
export type Namespace = GetBody<'/api/v1/presets/namespaces/{namespace}'>
export type PresetSummary = Namespace['presets'][number]
export type Preset = GetBody<'/api/v1/presets/namespaces/{namespace}/{randomizer}/{preset}'>
export type Election = GetBody<'/api/v1/elections/{election_id}/ballot'>
export type ElectionMethod = Election['method']
export type ElectionSummary = GetBody<'/api/v1/elections'>['elections'][number]
export type ElectionDetail = GetBody<'/api/v1/elections/{election_id}'>
export type ElectionResults = GetBody<'/api/v1/elections/{election_id}/results'>
export type ServerOption = GetBody<'/api/v1/elections/servers'>['servers'][number]
export type RoleMenu = GetBody<'/api/v1/role-menus/{menu_id}'>
export type RoleMenuStyle = RoleMenu['style']
export type RoleMenuServerOptions = GetBody<'/api/v1/role-menus/servers/{guild_id}'>
export type ServerDetail = GetBody<'/api/v1/servers/{guild_id}'>
export type ServerRole = ServerDetail['roles'][number]
export type ServerSettings = GetBody<'/api/v1/servers/{guild_id}/settings'>
export type Inquiry = GetBody<'/api/v1/servers/{guild_id}/inquiries'>['inquiries'][number]
/** One line of POST /servers/{guild_id}/inquiries/check. */
export interface InquiryCheck {
  ok: boolean
  text: string
}
export type TriforcePool = GetBody<'/api/v1/triforce-texts/{pool}'>
export type TriforceText = TriforcePool['mine'][number]
export type SubmissionForm = GetBody<'/api/v1/tournaments/{event}/submission-form'>
export type ApiTokenList = GetBody<'/api/v1/tokens'>
export type ApiTokenRow = ApiTokenList['tokens'][number]
export type OAuthRequest = GetBody<'/api/v1/oauth/requests/{txn}'>
export type AuditOptions = GetBody<'/api/v1/audit/options'>
export type AuditPage = GetBody<'/api/v1/audit'>
export type AuditEntry = AuditPage['entries'][number]

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message)
  }
}

/** The message a person should see for a failed call: the server's `error` when it has one. */
export function errorMessage(error: unknown, status: number): string {
  const message = (error as { error?: unknown } | undefined)?.error
  if (typeof message === 'string') return message
  if (status === 0) return "Couldn't reach SahasrahBot. Check your connection and try again."
  return 'Something went wrong. Try again.'
}

/** Unwrap an openapi-fetch result, throwing ApiError with a readable message. */
export function unwrap<T>(result: { data?: T; error?: unknown; response: Response }): T {
  if (result.response.ok && (result.data !== undefined || result.response.status === 204)) return result.data as T
  throw new ApiError(errorMessage(result.error, result.response.status), result.response.status)
}

/** Where to send someone to sign in, coming back to `path` afterwards. */
export function loginUrl(path: string = window.location.pathname + window.location.search): string {
  return `${API_BASE}/login/?next=${encodeURIComponent(path)}`
}
