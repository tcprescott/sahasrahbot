import { describe, expect, it } from 'vitest'
import source from './icons.ts?raw'

function sorted(values: string[]): string[] {
  return [...values].sort((a, b) => (a < b ? -1 : a > b ? 1 : 0))
}

describe('icons.ts', () => {
  it('keeps the SVG imports in alphabetical order', () => {
    const files = [...source.matchAll(/^import \w+ from '@material-symbols\/svg-400\/outlined\/([^']+)\.svg\?react'$/gm)].map((m) => m[1] ?? '')
    expect(files.length).toBeGreaterThan(0)
    expect(files).toEqual(sorted(files))
  })

  it('keeps the ICONS entries in alphabetical order', () => {
    const block = source.slice(source.indexOf('export const ICONS = {'), source.indexOf('} satisfies'))
    const names = [...block.matchAll(/^ {2}'?([a-z0-9_]+)'?: /gm)].map((m) => m[1] ?? '')
    expect(names.length).toBeGreaterThan(0)
    expect(names).toEqual(sorted(names))
  })
})
