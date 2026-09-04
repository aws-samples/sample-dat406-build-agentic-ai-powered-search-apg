/**
 * The Observatory and the Operator desk never render text below 11px.
 *
 * WORKSHOP.md states this to co-speakers as a shipped property of the surface,
 * and until this test existed nothing enforced it. Half the Observatory had
 * drifted to caption sizes and 22% of the Operator desk sat below 10px --
 * stat tiles, table headers, definition terms, status chips -- which is what
 * made two surfaces that share the storefront's palette and typefaces read as
 * a different, smaller product.
 *
 * 11px is the storefront's eyebrow size. Below it, tracked uppercase stops
 * being text and becomes texture, and on a 14-inch workshop laptop at the back
 * of a room it stops being anything at all.
 *
 * If you need a smaller size, the answer is almost always that weight, colour
 * or letter-spacing should carry the distinction instead. If it genuinely is
 * not, add the file to ALLOWED_BELOW_FLOOR with the reason.
 */
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { dirname, extname, join, relative, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const HERE = dirname(fileURLToPath(import.meta.url))
const SRC = resolve(HERE, '..')

const SCAN_ROOTS = [
  join(SRC, 'observatory'),
  join(SRC, 'operator'),
  join(SRC, 'styles', 'observatory-arch.css'),
]

const SCAN_EXTENSIONS = new Set(['.css', '.ts', '.tsx'])

/** Files permitted to fall below the floor, each with a stated reason. */
const ALLOWED_BELOW_FLOOR = new Map<string, string>([
  // (empty today; add with a reason rather than lowering the floor)
])

const FLOOR_PX = 11

// `font-size: 9.5px` in CSS and `fontSize: '10px'` in inline React styles.
// Matches only explicit px values -- rem, em, clamp() and var() are resolved
// elsewhere and are not what drifted.
const CSS_PX = /font-size:\s*(\d+(?:\.\d+)?)px/g
const INLINE_PX = /fontSize:\s*'(\d+(?:\.\d+)?)px'/g

function walk(target: string): string[] {
  const stats = statSync(target, { throwIfNoEntry: false })
  if (!stats) return []
  if (stats.isFile()) return SCAN_EXTENSIONS.has(extname(target)) ? [target] : []
  return readdirSync(target).flatMap((entry) => walk(join(target, entry)))
}

interface Violation {
  file: string
  line: number
  size: number
  text: string
}

function findViolations(): Violation[] {
  const violations: Violation[] = []
  for (const file of SCAN_ROOTS.flatMap(walk)) {
    const rel = relative(SRC, file)
    if (ALLOWED_BELOW_FLOOR.has(rel)) continue
    // Test files describe sizes rather than shipping them.
    if (/\.(test|spec)\.[tj]sx?$/.test(file)) continue

    const lines = readFileSync(file, 'utf8').split('\n')
    lines.forEach((line, index) => {
      for (const pattern of [CSS_PX, INLINE_PX]) {
        pattern.lastIndex = 0
        let match: RegExpExecArray | null
        while ((match = pattern.exec(line)) !== null) {
          const size = Number.parseFloat(match[1])
          if (size < FLOOR_PX) {
            violations.push({
              file: rel,
              line: index + 1,
              size,
              text: line.trim().slice(0, 80),
            })
          }
        }
      }
    })
  }
  return violations
}

describe('Observatory and Operator type floor', () => {
  it('renders no text below 11px', () => {
    const violations = findViolations()
    const report = violations
      .map((v) => `  ${v.file}:${v.line}  ${v.size}px  ${v.text}`)
      .join('\n')
    expect(
      violations,
      violations.length
        ? `Text below the ${FLOOR_PX}px floor:\n${report}\n\n` +
            'WORKSHOP.md tells co-speakers these surfaces never go below ' +
            `${FLOOR_PX}px. Use --text-label, or let weight, colour and ` +
            'letter-spacing carry the distinction instead.'
        : '',
    ).toEqual([])
  })

  it('scans the files it claims to scan', () => {
    // A guard whose glob silently stops matching passes forever. This asserts
    // the scan actually reaches the two surfaces and a representative file in
    // each, so an empty result means "clean", never "looked nowhere".
    const scanned = SCAN_ROOTS.flatMap(walk).map((f) => relative(SRC, f))
    expect(scanned.length).toBeGreaterThan(50)
    expect(scanned).toContain(join('observatory', 'styles', 'base.css'))
    expect(scanned).toContain(join('operator', 'styles', 'operator.css'))
  })
})
