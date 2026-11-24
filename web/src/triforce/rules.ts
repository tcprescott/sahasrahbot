/**
 * The characters the game can show in a triforce text, mirroring
 * alttprbot/services/triforce_texts.py (the server checks too).
 */
export const LINE =
  /^[A-Za-z0-9 ?!,….~～'↑↓→←あいうえおやゆよかきくけこわをんさしすせそがぎぐたちつてとげござなにぬねのじずぜはひふへほぞだぢまみむめもづでどらりるれろばびぶべぼぱぴぷぺぽゃゅょっぁぃぅぇぉアイウエオヤユヨカキクケコワヲンサシスセソガギグタチツテトゲゴザナニヌネノジズゼハヒフヘホゾダマミムメモヅデドラリルレロバビブベボパピプペポャュョッァィゥェォ-]*$/u

export const MAX_LINE = 19

export function lineProblem(line: string): string | null {
  if ([...line].length > MAX_LINE) return `Too long: ${MAX_LINE} characters at most.`
  if (!LINE.test(line)) return "Has a character the game can't show."
  return null
}
