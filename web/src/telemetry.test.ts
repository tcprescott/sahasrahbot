import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiMetrics, startTelemetry } from './telemetry'

afterEach(() => {
  delete window.__SAHASRAHBOT_SENTRY__
  vi.restoreAllMocks()
})

describe('telemetry', () => {
  it('stays off without asking the API when the page says Sentry is off', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch')
    window.__SAHASRAHBOT_SENTRY__ = null
    await startTelemetry()
    expect(fetchSpy).not.toHaveBeenCalled()
  })

  it('never throws when the settings request fails', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('offline'))
    await expect(startTelemetry()).resolves.toBeUndefined()
  })

  it('times API calls without breaking them while Sentry is off', () => {
    const request = new Request('http://localhost/api/v1/session')
    const params = { request, schemaPath: '/api/v1/session', params: {}, id: '1', options: {} }
    expect(() => {
      apiMetrics.onRequest?.(params as never)
      apiMetrics.onResponse?.({ ...params, response: new Response('{}') } as never)
    }).not.toThrow()
  })
})
