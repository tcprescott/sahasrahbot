import { describe, expect, it } from 'vitest'
import { findYamlProblem } from './problem'

describe('findYamlProblem', () => {
  it.each(['', '   \n', 'settings:\n  mode: open\n', 'a: 1\na: 2\n'])('accepts %j', (text) => {
    expect(findYamlProblem(text)).toBeNull() // empty is not a problem; PyYAML lets a later duplicate key win
  })

  it('says plainly where a colon is missing', () => {
    expect(findYamlProblem('settings:\n  mode open\n  goal: ganon\n')).toEqual({
      line: 2,
      column: 3,
      from: 12,
      to: expect.any(Number),
      message: 'a key here is missing its colon, or the line is indented wrongly',
    })
  })

  it.each([
    ['a:\n\t- b\n', 2, 'indent with spaces, not tabs'],
    ['a: b: c\n', 1, 'a value and a new key are on the same line; put the key on a line of its own'],
    ['a: 1\n---\nb: 2\n', 2, 'a preset is one YAML document, but this has more than one (a second ---)'],
    ['a: "open\n', 2, 'missing closing "quote'], // found where the text runs out
  ])('explains %j', (text, line, message) => {
    expect(findYamlProblem(text)).toMatchObject({ line, message })
  })
})
