import { describe, expect, it } from 'vitest'
import { ago } from './time'

describe('ago', () => {
  const now = new Date('2026-11-24T12:00:00Z')
  it('picks the largest whole unit', () => {
    expect(ago('2026-11-21T12:00:00Z', now)).toMatch(/3 days ago/)
    expect(ago('2026-11-24T11:00:00Z', now)).toMatch(/1 hour ago|an hour ago/)
    expect(ago('2026-11-24T11:59:50Z', now)).toMatch(/this minute|now/)
  })
  it('is empty without a date', () => {
    expect(ago(null, now)).toBe('')
  })
})
