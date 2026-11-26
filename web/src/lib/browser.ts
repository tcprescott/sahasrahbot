/**
 * Leaving the app for a server page (Discord sign-in, sign out, a download).
 * One object so tests can replace it: jsdom can't navigate, and
 * `window.location.assign` can't be spied on.
 */
export const browser = {
  assign(url: string): void {
    window.location.assign(url)
  },
  /** Open a page somewhere else (a Discord message) in a new tab. */
  open(url: string): void {
    window.open(url, '_blank', 'noopener')
  },
}
