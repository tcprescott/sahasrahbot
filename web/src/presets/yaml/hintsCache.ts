import { api, unwrap } from '../../api/client'
import type { Hint } from './hints'

const cache = new Map<string, Promise<readonly Hint[]>>()

/**
 * The suggestions for a randomizer, fetched once per page load. Suggestions are a
 * nicety: if they can't be fetched, the editor offers none and asks again next time.
 */
export function loadHints(randomizer: string): Promise<readonly Hint[]> {
  let found = cache.get(randomizer)
  if (!found) {
    found = api
      .GET('/api/v1/presets/randomizers/{randomizer}/hints', { params: { path: { randomizer } } })
      .then(unwrap)
      .then((body) => body.hints)
      .catch(() => {
        cache.delete(randomizer)
        return []
      })
    cache.set(randomizer, found)
  }
  return found
}

/** For tests: forget what was fetched. */
export function clearHints(): void {
  cache.clear()
}
