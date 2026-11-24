import { describe, expect, it } from 'vitest'
import { add, move, remove } from './ranking'

describe('ranking', () => {
  it('moves a candidate up and down, stopping at the ends', () => {
    expect(move([1, 2, 3], 3, -1)).toEqual([1, 3, 2])
    expect(move([1, 2, 3], 1, 1)).toEqual([2, 1, 3])
    expect(move([1, 2, 3], 1, -1)).toEqual([1, 2, 3])
    expect(move([1, 2, 3], 3, 1)).toEqual([1, 2, 3])
  })
  it('adds to the end once, and removes', () => {
    expect(add([1], 2)).toEqual([1, 2])
    expect(add([1, 2], 2)).toEqual([1, 2])
    expect(remove([1, 2, 3], 2)).toEqual([1, 3])
  })
})
