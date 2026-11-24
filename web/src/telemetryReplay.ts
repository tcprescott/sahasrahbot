/** Sentry Session Replay, loaded on its own after start-up (see telemetry.ts). */
import { replayIntegration as sentryReplay } from '@sentry/react'

export function replayIntegration() {
  // Everything a person types or reads stays on their screen: text and inputs masked, media blocked.
  return sentryReplay({ maskAllText: true, maskAllInputs: true, blockAllMedia: true })
}
