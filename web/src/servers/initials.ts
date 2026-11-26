/** Up to two letters for a server's badge: the first letters of its first two words. */
export function initials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean)
  return (
    words
      .slice(0, 2)
      .map((w) => Array.from(w)[0])
      .join('')
      .toUpperCase() || '?'
  )
}
