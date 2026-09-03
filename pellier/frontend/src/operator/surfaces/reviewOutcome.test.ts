import { describe, expect, it } from 'vitest'
import { outcomeKind } from './ReviewQueue'
import type { OperatorReview } from '../../services/operator'

function review(overrides: Partial<OperatorReview> = {}): OperatorReview {
  return {
    reviewId: 1,
    customerId: 'CUST-THEO',
    customerName: 'Theo',
    slug: 'theo',
    personaId: 'theo',
    action: 'initiate_return',
    parameters: {},
    status: 'pending',
    humanState: 'confirmation_required',
    assurance: {
      human: 'CONFIRMATION_REQUIRED',
      policy: 'PENDING',
      aurora: 'NOT_EVALUATED',
      evidence: 'PENDING',
    },
    sourceTurnId: null,
    execution: null,
    ...overrides,
  } as OperatorReview
}

describe('outcomeKind', () => {
  it('keeps a proposal pending until a person decides', () => {
    expect(outcomeKind(review())).toBe('pending')
  })

  it('tells a policy refusal apart from a carried-out write', () => {
    const confirmed = {
      humanState: 'confirmed' as const,
      execution: { startedAt: '2026-09-03T00:00:00Z' } as unknown as OperatorReview['execution'],
    }
    expect(
      outcomeKind(
        review({
          ...confirmed,
          assurance: { human: 'CONFIRMED', policy: 'DENY', aurora: 'NOT_REACHED', evidence: 'POLICY_PROOF' },
        } as Partial<OperatorReview>),
      ),
    ).toBe('refused')
    expect(
      outcomeKind(
        review({
          ...confirmed,
          assurance: { human: 'CONFIRMED', policy: 'ALLOW', aurora: 'PERMITTED', evidence: 'RECEIPTED' },
        } as Partial<OperatorReview>),
      ),
    ).toBe('executed')
    expect(
      outcomeKind(
        review({
          ...confirmed,
          assurance: { human: 'CONFIRMED', policy: 'ALLOW', aurora: 'DENIED', evidence: 'RECEIPTED' },
        } as Partial<OperatorReview>),
      ),
    ).toBe('refused')
  })

  it('marks a confirmed but unexecuted review as approved', () => {
    expect(outcomeKind(review({ humanState: 'confirmed', execution: null }))).toBe('approved')
    expect(outcomeKind(review({ humanState: 'declined' }))).toBe('declined')
  })
})
