import { describe, expect, it } from 'vitest'
import { lineProblem } from './rules'

describe('lineProblem', () => {
  it('accepts letters, numbers, punctuation and kana up to 19 characters', () => {
    expect(lineProblem('HELLO, WORLD!')).toBeNull()
    expect(lineProblem('ゼルダ')).toBeNull()
    expect(lineProblem('')).toBeNull()
  })
  it('rejects long lines and characters the game lacks', () => {
    expect(lineProblem('x'.repeat(20))).toMatch(/Too long/)
    expect(lineProblem('café')).toMatch(/character/)
  })
})
