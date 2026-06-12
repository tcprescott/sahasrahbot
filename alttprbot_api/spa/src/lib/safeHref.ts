/**
 * Return a safe href for a user-supplied URL.
 *
 * Permalink and VoD URLs are sourced from the database (runners submit their own
 * VoD links), so a malicious value could carry a `javascript:` / `data:` scheme
 * that executes on click. Allow only http(s); anything else collapses to '#'.
 */
export function safeHref(url: string | null | undefined): string {
  if (!url) return '#';
  try {
    const p = new URL(url, window.location.origin);
    return p.protocol === 'http:' || p.protocol === 'https:' ? p.toString() : '#';
  } catch {
    return '#';
  }
}
