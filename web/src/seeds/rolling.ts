import { api, unwrap, type GetBody } from '../api/client'
import type { paths } from '../api/schema'

type RollOp = paths['/api/v1/seeds']['post']
export type Seed = RollOp['responses'][201]['content']['application/json']
export type SeedLookup = GetBody<'/api/v1/seeds/{hash_id}'>
export type RollRequest = NonNullable<RollOp['requestBody']>['content']['application/json']
export type Rollable = RollRequest['randomizer']
export type Branch = NonNullable<RollRequest['branch']>

/** The randomizers the website can roll, in the order the Seeds page offers them. */
export const ROLLABLE: { id: Rollable; label: string }[] = [
  { id: 'alttpr', label: 'ALTTPR' },
  { id: 'alttprmystery', label: 'Mystery' },
  { id: 'sm', label: 'Super Metroid' },
  { id: 'smz3', label: 'SMZ3' },
]

export const isRollable = (randomizer: string): randomizer is Rollable => ROLLABLE.some((r) => r.id === randomizer)

export interface RollChoices {
  race: boolean
  hints: boolean
  allowQuickswap: boolean
  branch: Branch
  spoilerRace: boolean
}

export const DEFAULT_CHOICES: RollChoices = { race: false, hints: false, allowQuickswap: true, branch: 'live', spoilerRace: false }

/** Roll `preset` (a built-in name, or `namespace/name`) with the options that apply to its randomizer. */
export async function rollSeed(randomizer: Rollable, preset: string, c: RollChoices): Promise<Seed> {
  const body: RollRequest = { randomizer, preset, race: c.race }
  if (randomizer === 'alttpr') Object.assign(body, { hints: c.hints, allow_quickswap: c.allowQuickswap, branch: c.branch })
  if (randomizer === 'alttprmystery') body.allow_quickswap = c.allowQuickswap
  if (randomizer === 'smz3') body.spoiler_race = c.spoilerRace
  return unwrap(await api.POST('/api/v1/seeds', { body }))
}

/** A hash from what someone pasted: the hash itself, or a seed link (…/h/<hash>, …/seed/<hash>). */
export function hashFrom(text: string): string {
  const trimmed = text.trim()
  try {
    const url = new URL(trimmed)
    const parts = url.pathname.split('/').filter(Boolean)
    return parts.at(-1) ?? ''
  } catch {
    return trimmed
  }
}
