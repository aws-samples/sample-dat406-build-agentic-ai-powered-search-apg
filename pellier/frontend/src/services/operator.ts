/**
 * Pellier Operator API client.
 *
 * Reads are open; writes require a verified operator token, so a 401 here is a
 * real state the console renders rather than an error to swallow. Every field
 * comes from Aurora: there is no committed frontend copy of the client book,
 * because UI state is not evidence.
 */

import type { Membership } from '../data/membership'

import type { CapabilitySnapshot } from './operatorCapabilities'
import type {
  ConciergeConfig,
  ConciergeInvestigationStep,
  ConciergeSession,
  ConciergeTurn,
} from './operatorConcierge'

export type { CapabilitySnapshot, Capability, CapabilityState } from './operatorCapabilities'
export type {
  ConciergeConfig,
  ConciergeSession,
  ConciergeMessage,
  ConciergeArtifact,
  ConciergeInvestigationStep,
  ConciergeEvidenceItem,
  ConciergeTurn,
  TurnState,
} from './operatorConcierge'

export interface OperatorClient {
  customerId: string
  /** `CUST-JESSICA` -> `jessica`. Drives the portrait filename. */
  slug: string
  name: string
  membership: Membership
  spend12mo: number
  orderCount: number
  orderValue: number
  lastOrderAt: string | null
  note: string
  /** Set only where a real storefront handoff exists. */
  personaId: string | null
  /** Present on a single-client read. */
  openTicketCount?: number
  creditBalanceCents?: number
  creditBalance?: string
}

export interface OperatorOrder {
  orderId: number
  productId: string
  productName: string
  brand: string
  price: number
  quantity: number
  placedAt: string | null
  imageUrl: string
}

export interface OperatorTicket {
  ticketId: string
  subject: string
  status: 'open' | 'pending' | 'resolved' | 'closed'
  channel: string
  lastNote: string
  openedAt: string | null
  resolvedAt: string | null
}

export interface OperatorCredit {
  creditId: number
  amountCents: number
  /** Formatted once by the API so no surface re-derives currency from cents. */
  amount: string
  currency: string
  reason: string
  issuedBy: string | null
  createdAt: string | null
}

export interface OperatorBook {
  clients: OperatorClient[]
  total: number
  byMembership: Record<Membership, number>
}

export interface OperatorClientRecord {
  client: OperatorClient
  orders: OperatorOrder[]
  tickets: OperatorTicket[]
  credits: OperatorCredit[]
}

/** A governed write envelope, as the tool returned it. */
export interface OperatorActionResult {
  result: {
    status: 'success' | 'error' | 'policy_blocked' | 'idempotency_conflict'
    message?: string
    idempotent_replay?: boolean
    credit_id?: number
    amount?: string
    balance_cents?: number
    return_id?: number
    name?: string
    [key: string]: unknown
  }
  idempotencyKey: string
  actedBy: string | null
}

/**
 * The four assurance axes, exactly as the API resolved them.
 *
 * Independent on purpose. A single boolean would let a human decision imply an
 * authorization decision, which is the confusion this surface exists to
 * dismantle, so the console renders these verbatim and never derives one from
 * another.
 */
export interface ActionAssurance {
  human: 'CONFIRMATION_REQUIRED' | 'CONFIRMED' | 'DECLINED'
  /** ALLOW / DENY / WOULD_DENY come only from a real policy engine response. */
  policy: 'PENDING' | 'NOT_EVALUATED' | 'ALLOW' | 'DENY' | 'WOULD_DENY'
  aurora:
    | 'NOT_EVALUATED'
    | 'NOT_REACHED'
    | 'PERMITTED'
    | 'DENIED'
    | 'NOT_ENFORCED'
  evidence:
    | 'PENDING'
    | 'NO_EXECUTION'
    | 'RECEIPTED'
    | 'POLICY_PROOF'
    | 'ATTEMPT_RECEIPT'
}

/** One governed execution attempt. Each axis comes from its own artifact. */
export interface OperatorExecutionResult {
  reviewId: number
  rail: 'gateway-mcp' | 'in-process'
  executionTurnId: string
  idempotencyKey: string
  /** The operator AgentCore Policy authorizes. */
  actorPrincipal: string
  /** The customer Aurora RLS scopes. Null when the client has no mapping. */
  customerSubject: string | null
  assurance: ActionAssurance
  /** Why each axis is in its state, resolved server-side. */
  notes: Partial<Record<'policy' | 'aurora', string>>
  tool: string
  result: Record<string, unknown>
}

/**
 * A stored execution receipt: what the governance layers decided, and what decided it.
 *
 * This is the artifact migration 021 assumed existed and nothing wrote. Until it
 * shipped, a Cedar DENY left no durable trace anywhere — a denied call correctly writes
 * no `tool_audit` row and claims no idempotency key — so this surface reported
 * `policy: PENDING` for actions Cedar had refused.
 */
export interface OperatorExecutionReceipt {
  receiptId: number
  /**
   * The domain row this execution produced, joined on the write key. Null when the
   * execution wrote nothing — a denial, a refusal, or a non-writing tool.
   *
   * Needed because the client's return history and the return THIS review created live
   * in the same table: without it the record counted its own outcome among the
   * client's "previous damaged returns".
   */
  producedReturnId: number | null
  executionTurnId: string
  tool: string
  /** The Cedar action id evaluated, e.g. `<target>___initiate_return`. */
  gatewayActionId: string
  rail: 'gateway-mcp' | 'in-process'
  /** The operator AgentCore Policy authorized. */
  actorPrincipal: string
  /** The customer Aurora RLS scoped. Null when the client has no mapping. */
  customerSubject: string | null
  policyEngineId: string
  /** ENFORCE or LOG_ONLY at evaluation time. */
  gatewayMode: string
  /**
   * Forbid policies whose statement NAMES this action — not necessarily the one that
   * denied it. The same conditional forbid is listed beside an ALLOW, where it means
   * a rule was evaluated and did not apply.
   */
  matchingForbids: string[]
  idempotencyKey: string
  notes: Partial<Record<'policy' | 'aurora', string>>
  recordedAt: string | null
}

export type ReviewHumanState =
  | 'confirmation_required'
  | 'confirmed'
  | 'declined'

/** Workflow state and references. Never business truth. */
export interface OperatorReview {
  reviewId: number
  customerId: string
  customerName: string
  slug: string
  /** Set only for the three storefront-switchable heroes. */
  personaId: string | null
  action: string
  parameters: Record<string, unknown>
  status: 'pending' | 'approved' | 'rejected'
  humanState: ReviewHumanState
  assurance: ActionAssurance
  /** The originating shopper turn. Not shown by default; it is the proof link. */
  sourceTurnId: string | null
  /**
   * Claimed when execution BEGINS. Present with `execution: null` means an attempt
   * started and produced no verdict, which is its own state and not "never tried".
   */
  executionTurnId: string | null
  /**
   * The verdicts of the latest execution attempt, read from
   * `pellier.execution_receipts`, or null when none was attempted.
   *
   * Separate from `assurance` on purpose: the axes are the verdicts, this is what
   * produced them. An ALLOW without `gatewayMode` cannot be told apart from an
   * unenforced observation under LOG_ONLY.
   */
  execution: OperatorExecutionReceipt | null
  orderId: number | null
  issue: string
  recommendation: {
    primaryAction?: string
    rationale?: string
    secondarySuggestion?: {
      action: string
      amountCents?: number
      rationale?: string
    }
  }
  /** Fingerprint of the parameters shown, echoed back on confirm. */
  actionHash: string
  decidedBy: string | null
  requestedAt: string | null
  decidedAt: string | null
}

export interface OperatorReviewQueue {
  reviews: OperatorReview[]
  total: number
  pendingCount: number
}

export interface OperatorReviewDetail {
  review: OperatorReview
  /** Resolved from pellier.customers on read, never cached on the review. */
  client: {
    customerId: string
    name: string
    membership: Membership
    spend12mo: number
    note: string
    personaId: string | null
  }
  order: OperatorOrder | null
  product: {
    productId: string
    name: string
    brand: string
    price: number
    catalogQuantity: number
    imageUrl: string
  } | null
  /** Derived from live warehouse rows at read time. Never stored. */
  fulfilment: {
    totalUnits: number
    replacementAvailable: boolean
    /** False when no per-location row exists, so absence is not reported as zero. */
    availabilityVerified?: boolean
    warehouses: {
      warehouseId: string
      displayName: string
      city: string
      quantity: number
      shipWindowMin: number
      shipWindowMax: number
    }[]
  }
  /** pellier.orders has no status column; this is the real lifecycle. */
  returns: {
    returnId: number
    productId: string
    reason: string
    status: string
    requestedAt: string | null
    resolvedAt: string | null
  }[]
}

export interface OperatorReviewDecision {
  reviewId: number
  status: string
  humanState: ReviewHumanState
  decidedBy: string | null
  decidedAt: string | null
  assurance: ActionAssurance
}

export class OperatorApiError extends Error {
  constructor(
    public readonly code: string,
    public readonly status: number,
  ) {
    super(code)
    this.name = 'OperatorApiError'
  }

  /** True when the caller simply is not signed in as an operator. */
  get needsOperatorSignIn(): boolean {
    return this.status === 401 || this.status === 403
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch(path, {
      ...init,
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...init.headers },
    })
  } catch {
    throw new OperatorApiError('operator_unavailable', 503)
  }

  if (!response.ok) {
    let code =
      response.status === 401 || response.status === 403
        ? 'operator_sign_in_required'
        : 'operator_unavailable'
    try {
      const body = (await response.json()) as { detail?: string }
      if (body.detail) code = body.detail
    } catch {
      // Keep the status-derived code when the response is not JSON.
    }
    throw new OperatorApiError(code, response.status)
  }
  return response.json() as Promise<T>
}

export function fetchClientBook(): Promise<OperatorBook> {
  return request<OperatorBook>('/api/operator/clients')
}

export function fetchClientRecord(
  customerId: string,
): Promise<OperatorClientRecord> {
  return request<OperatorClientRecord>(
    `/api/operator/clients/${encodeURIComponent(customerId)}`,
  )
}

/**
 * What the Operator can actually do right now.
 *
 * Backend-derived from live Gateway and policy state. The frontend must never
 * decide this: `initiate_return` is currently published with zero matching permits
 * while `issue_credit` is not published at all, and only the control plane can tell
 * those apart.
 */
export function fetchCapabilities(): Promise<CapabilitySnapshot> {
  return request<CapabilitySnapshot>('/api/operator/capabilities')
}

/**
 * Whether the composer may submit a development turn.
 *
 * Deliberately separate from capabilities: that reports governed business
 * capability, this reports whether orchestration exists to answer a question yet.
 * Collapsing them would make a governance state look like a missing feature.
 */
export function fetchConciergeConfig(): Promise<ConciergeConfig> {
  return request<ConciergeConfig>('/api/operator/concierge/config')
}

/** The latest Concierge session for a client, or null when none exists. */
export async function fetchLatestConciergeSession(
  clientId: string,
): Promise<string | null> {
  const body = await request<{ sessionId: string | null }>(
    `/api/operator/clients/${encodeURIComponent(clientId)}/concierge/sessions/latest`,
  )
  return body.sessionId ?? null
}

export function fetchConciergeSession(
  clientId: string,
  sessionId: string,
): Promise<ConciergeSession> {
  return request<ConciergeSession>(
    `/api/operator/clients/${encodeURIComponent(clientId)}` +
      `/concierge/sessions/${encodeURIComponent(sessionId)}`,
  )
}

/** Created lazily, when the operator first interacts — never on page load. */
export function createConciergeSession(clientId: string): Promise<ConciergeSession> {
  return request<ConciergeSession>(
    `/api/operator/clients/${encodeURIComponent(clientId)}/concierge/sessions`,
    { method: 'POST' },
  )
}

/**
 * How a turn is submitted. The only way, from the browser.
 *
 * Streamed so the operator sees real progress instead of seven seconds of stillness.
 * The backend also exposes a non-streaming `/turns` for curl-based proof, but the
 * browser does not use it: two client paths to one turn would drift.
 *
 * SSE over `fetch` + `getReader()`, matching how `services/chat.ts` already consumes
 * the agent stream. `onStep` fires for work the backend has actually finished; the
 * single `running` event is a genuine state, not a simulated tick.
 */
export async function streamConciergeTurn(
  clientId: string,
  sessionId: string,
  message: string,
  transportKey: string,
  onStep: (step: ConciergeInvestigationStep) => void,
): Promise<ConciergeTurn & Record<string, unknown>> {
  const response = await fetch(
    `/api/operator/clients/${encodeURIComponent(clientId)}` +
      `/concierge/sessions/${encodeURIComponent(sessionId)}/turns/stream`,
    {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, transportKey }),
    },
  )
  if (!response.ok || !response.body) {
    throw new OperatorApiError('operator_unavailable', response.status || 503)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let final: (ConciergeTurn & Record<string, unknown>) | null = null

  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    // SSE frames are separated by a blank line.
    const frames = buffer.split('\n\n')
    buffer = frames.pop() ?? ''
    for (const frame of frames) {
      let event = ''
      let data = ''
      for (const line of frame.split('\n')) {
        if (line.startsWith('event: ')) event = line.slice(7).trim()
        else if (line.startsWith('data: ')) data += line.slice(6)
      }
      if (!data) continue
      const parsed = JSON.parse(data)
      if (event === 'step') onStep(parsed as ConciergeInvestigationStep)
      else if (event === 'complete') final = parsed
      else if (event === 'error') {
        throw new OperatorApiError(parsed.detail ?? 'operator_unavailable', 500)
      }
    }
  }

  if (!final) throw new OperatorApiError('operator_unavailable', 500)
  return final
}

export function fetchReviewQueue(): Promise<OperatorReviewQueue> {
  return request<OperatorReviewQueue>('/api/operator/reviews')
}

export function fetchReview(reviewId: number): Promise<OperatorReviewDetail> {
  return request<OperatorReviewDetail>(
    `/api/operator/reviews/${encodeURIComponent(String(reviewId))}`,
  )
}

/**
 * Confirm the exact proposed action.
 *
 * `actionHash` is the fingerprint the console displayed. Echoing it is what
 * makes the confirmation bind to those parameters: if any material value moved,
 * the server refuses with `parameters_changed` rather than applying a stale
 * consent to new values.
 *
 * This records a human decision. It performs no business mutation.
 */
export function confirmReview(
  reviewId: number,
  actionHash: string,
): Promise<OperatorReviewDecision> {
  return request<OperatorReviewDecision>(
    `/api/operator/reviews/${encodeURIComponent(String(reviewId))}/confirm`,
    { method: 'POST', body: JSON.stringify({ actionHash }) },
  )
}

/** Decline. Nothing is submitted anywhere; no fingerprint is required. */
export function declineReview(
  reviewId: number,
): Promise<OperatorReviewDecision> {
  return request<OperatorReviewDecision>(
    `/api/operator/reviews/${encodeURIComponent(String(reviewId))}/decline`,
    { method: 'POST' },
  )
}

/**
 * Execute the confirmed action through the governed rail.
 *
 * Carries no action parameters. The customer, tool, reason, and amount all come
 * from the persisted review, so a browser cannot execute a different mutation
 * than the one a human confirmed. `expectedActionHash` is stale-view protection
 * only.
 */
export function executeReview(
  reviewId: number,
  expectedActionHash?: string,
): Promise<OperatorExecutionResult> {
  return request<OperatorExecutionResult>(
    `/api/operator/reviews/${encodeURIComponent(String(reviewId))}/execute`,
    {
      method: 'POST',
      body: JSON.stringify(
        expectedActionHash ? { expectedActionHash } : {},
      ),
    },
  )
}

export function issueCredit(input: {
  customerId: string
  amountCents: number
  reason: string
  /** Supply a stable key so a double-click applies once. */
  idempotencyKey?: string
}): Promise<OperatorActionResult> {
  return request<OperatorActionResult>('/api/operator/actions/issue-credit', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export function resolveReturn(input: {
  customerId: string
  productId: number
  reason: string
  idempotencyKey?: string
}): Promise<OperatorActionResult> {
  return request<OperatorActionResult>(
    '/api/operator/actions/resolve-return',
    { method: 'POST', body: JSON.stringify(input) },
  )
}
