/** Pure helpers for editing a ranking (a list of candidate ids, most preferred first). */

export function move(ranking: number[], id: number, by: -1 | 1): number[] {
  const at = ranking.indexOf(id)
  const to = at + by
  if (at < 0 || to < 0 || to >= ranking.length) return ranking
  const next = [...ranking]
  next[at] = next[to] as number
  next[to] = id
  return next
}

export function add(ranking: number[], id: number): number[] {
  return ranking.includes(id) ? ranking : [...ranking, id]
}

export function remove(ranking: number[], id: number): number[] {
  return ranking.filter((x) => x !== id)
}
