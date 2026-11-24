/**
 * Sentry in the browser: errors, session replays, page-load traces and API timings.
 *
 * The server decides whether any of this runs. It inlines its settings in the
 * index.html it serves (`window.__SAHASRAHBOT_SENTRY__`, so there's no round trip
 * before the first render); a page without them (a native wrapper's bundled
 * index.html, `npm run dev`) asks `GET /api/v1/telemetry`. With no DSN configured
 * (local runs, tests, the dev server) the answer is `null` and Sentry is never
 * initialised. The calls below are
 * all safe before or without init: the SDK drops what it isn't set up for.
 *
 * What it sends, to the same Sentry project as the server (as in Wizzrobe):
 * - Errors: uncaught errors and rejections, and React render errors
 *   (`reactErrorHandler` on the root, see main.tsx). Only stacks in our own
 *   scripts (`allowUrls`), so extensions and injected scripts stay out.
 * - Replays: the last minute before an error, all text and inputs masked and
 *   media blocked. Nothing is recorded for sessions without an error.
 * - Traces: page loads and navigations, named by route (`/ranked_choice/:electionId`),
 *   with web vitals. Calls to our own API carry the trace headers, so the
 *   server's spans for that request join the same trace.
 * - Metrics: `api.calls` / `api.duration` (ms) for every /api/v1 call, by
 *   `endpoint` (the OpenAPI path, `/api/v1/ranked-choice/{election_id}`), `method`
 *   and `status`, as the person's browser saw it.
 *
 * Every event is tagged `surface: browser`; server events are `surface: server`.
 */
import * as Sentry from '@sentry/react'
import type { Middleware } from 'openapi-fetch'
import { useEffect } from 'react'
import { Routes, createRoutesFromChildren, matchRoutes, useLocation, useNavigationType } from 'react-router-dom'
import { API_BASE, api, type GetBody } from './api/client'

let started = false

/** The `<Routes>` to use, so navigations are named by their route pattern. */
export const SentryRoutes = Sentry.withSentryReactRouterV7Routing(Routes)

/** For `createRoot`: report errors React catches in render, with the component stack. */
export const reactErrorHandler = Sentry.reactErrorHandler

/** Who is signed in, on every browser event. `null` when signed out. */
export function setTelemetryUser(user: { id: string; name: string } | null): void {
  Sentry.setUser(user ? { id: user.id, username: user.name } : null)
}

function apiOrigins(): (string | RegExp)[] {
  // Same-origin API calls (the website) and, for a native wrapper, the API's own origin.
  const targets: (string | RegExp)[] = [/^\/(?!\/)/, window.location.origin]
  if (API_BASE) targets.push(API_BASE)
  return targets
}

const requestStarted = new WeakMap<Request, number>()

/** Times each API call for `api.calls` / `api.duration`. */
export const apiMetrics: Middleware = {
  onRequest({ request }) {
    requestStarted.set(request, performance.now())
  },
  onResponse({ request, response, schemaPath }) {
    record(request, schemaPath, `${Math.floor(response.status / 100)}xx`)
  },
  onError({ request, schemaPath }) {
    record(request, schemaPath, 'network error')
  },
}

function record(request: Request, endpoint: string, status: string): void {
  const startedAt = requestStarted.get(request)
  if (!started || startedAt === undefined) return
  const attributes = { endpoint, method: request.method, status }
  Sentry.metrics.count('api.calls', 1, { attributes })
  Sentry.metrics.distribution('api.duration', performance.now() - startedAt, { unit: 'millisecond', attributes })
}

type Settings = NonNullable<GetBody<'/api/v1/telemetry'>['sentry']>

declare global {
  interface Window {
    __SAHASRAHBOT_SENTRY__?: Settings | null
  }
}

async function loadSettings(): Promise<Settings | null> {
  if (window.__SAHASRAHBOT_SENTRY__ !== undefined) return window.__SAHASRAHBOT_SENTRY__
  try {
    const result = await api.GET('/api/v1/telemetry')
    return result.data?.sentry ?? null
  } catch {
    return null
  }
}

/**
 * Load the server's Sentry settings and start the SDK. Call once, before rendering.
 * Never throws: monitoring must never stop the app from loading.
 */
export async function startTelemetry(): Promise<void> {
  if (started) return
  const config = await loadSettings()
  if (!config) return

  try {
    Sentry.init({
      dsn: config.dsn,
      environment: config.environment,
      release: config.release ?? undefined,
      // We set the user (id and name) ourselves; never IPs, cookies or request bodies.
      dataCollection: { userInfo: false, cookies: false, httpBodies: [] },
      sampleRate: config.sample_rate,
      tracesSampleRate: config.traces_sample_rate,
      tracePropagationTargets: apiOrigins(),
      allowUrls: [window.location.origin],
      integrations: [
        Sentry.reactRouterV7BrowserTracingIntegration({
          useEffect,
          useLocation,
          useNavigationType,
          createRoutesFromChildren,
          matchRoutes,
        }),
      ],
      replaysSessionSampleRate: 0,
      replaysOnErrorSampleRate: config.replay ? 1.0 : 0,
      initialScope: { tags: { surface: 'browser' } },
    })
    started = true
  } catch {
    return
  }
  api.use(apiMetrics)

  if (config.replay) {
    // In its own chunk: most page views never need the recorder's code up front.
    void import('./telemetryReplay').then(({ replayIntegration }) => Sentry.addIntegration(replayIntegration()))
  }
}
