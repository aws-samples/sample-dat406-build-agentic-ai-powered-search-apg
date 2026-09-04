/**
 * Micro-eval client: what a smaller rerank candidate pool costs.
 *
 * The endpoint runs the canonical Anna query at two pool sizes, repeated, and
 * reports retrieval quality and latency for each. The frontend does no
 * arithmetic on the query itself: every number here was measured server-side,
 * and an absent endpoint returns `null` so the card can say so.
 */

import { API_BASE_URL } from './apiBase'

/**
 * Both pools in one request. `repetitions` is deliberately absent: the
 * endpoint owns the default and reports back the count it actually ran, so a
 * number pinned here would only ever be a second, staler source of truth.
 */
const MICRO_EVAL_PATH =
  '/api/observatory/search-strategies/micro-eval?pool_k=20&pool_k=3'

export interface MicroEvalVariant {
  pool_k: number
  candidate_coverage: number
  context_precision: number
  mrr: number
  hard_constraint_violations: number
  short_result_rate: number
  citation_coverage: number
  latency_ms_p50: number
  latency_ms_p95: number
}

export interface MicroEvalResult {
  query: string
  limit: number
  repetitions: number
  variants: MicroEvalVariant[]
}

const NUMERIC_FIELDS: Array<keyof MicroEvalVariant> = [
  'pool_k',
  'candidate_coverage',
  'context_precision',
  'mrr',
  'hard_constraint_violations',
  'short_result_rate',
  'citation_coverage',
  'latency_ms_p50',
  'latency_ms_p95',
]

function isVariant(value: unknown): value is MicroEvalVariant {
  if (!value || typeof value !== 'object') return false
  const record = value as Record<string, unknown>
  return NUMERIC_FIELDS.every((field) => typeof record[field] === 'number')
}

function isResult(value: unknown): value is MicroEvalResult {
  if (!value || typeof value !== 'object') return false
  const record = value as Record<string, unknown>
  return (
    typeof record.query === 'string' &&
    // Any positive whole number: the endpoint chooses the count and reports
    // what it ran. Half a repetition, or none, describes no measurement.
    typeof record.repetitions === 'number' &&
    Number.isInteger(record.repetitions) &&
    record.repetitions > 0 &&
    Array.isArray(record.variants) &&
    record.variants.length > 0 &&
    record.variants.every(isVariant)
  )
}

/**
 * Run the micro-eval for pool_k 20 and 3.
 *
 * @param signal Optional abort signal for unmounting callers.
 * @returns The measured result, or `null` when the endpoint is missing or
 *   returned a shape this client does not recognise. Never a partial result:
 *   half a comparison invites a conclusion the run does not support.
 */
export async function fetchMicroEval(
  signal?: AbortSignal,
): Promise<MicroEvalResult | null> {
  try {
    const response = await fetch(`${API_BASE_URL}${MICRO_EVAL_PATH}`, { signal })
    if (!response.ok) return null
    const payload: unknown = await response.json()
    return isResult(payload) ? payload : null
  } catch {
    return null
  }
}

/** Percentage points between two 0..1 rates, rounded. */
function points(larger: number, smaller: number): number {
  return Math.round((larger - smaller) * 100)
}

/**
 * One line naming the trade the smaller pool makes.
 *
 * Latency is stated as saved time and quality as lost coverage, because that
 * is the direction of the decision a participant is being asked to weigh.
 */
export function poolCostReading(
  wide: MicroEvalVariant,
  narrow: MicroEvalVariant,
): string {
  const savedMs = Math.round(wide.latency_ms_p50 - narrow.latency_ms_p50)
  const savings =
    savedMs > 0
      ? `saves ${savedMs} ms at p50`
      : `costs ${Math.abs(savedMs)} ms at p50`
  const lost = points(wide.candidate_coverage, narrow.candidate_coverage)
  const violations =
    narrow.hard_constraint_violations - wide.hard_constraint_violations
  const violationClause =
    violations > 0
      ? ` and lets ${violations} hard-constraint ${
          violations === 1 ? 'violation' : 'violations'
        } through`
      : ''

  if (lost <= 0) {
    return (
      `Pool ${narrow.pool_k} ${savings} and gives up no candidate coverage on ` +
      `this query${violationClause}.`
    )
  }
  return (
    `Pool ${narrow.pool_k} ${savings} and gives up ${lost} points of ` +
    `candidate coverage${violationClause}.`
  )
}
