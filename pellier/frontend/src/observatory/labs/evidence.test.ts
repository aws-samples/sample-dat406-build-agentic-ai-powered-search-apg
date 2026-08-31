import { describe, expect, it } from 'vitest';

import {
  classifyEvidence,
  provenanceForEvidence,
  type EvidenceClassificationInput,
} from './evidence';

describe('classifyEvidence', () => {
  const base: EvidenceClassificationInput = {
    decisionAuthoritative: true,
    invocationCorrelated: true,
    executionObserved: true,
  };

  it.each([
    [{ ...base, decision: 'ALLOW' }, 'ALLOW_EXECUTED'],
    [
      { ...base, decision: 'DENY', executionObserved: false },
      'DENY_NOT_EXECUTED',
    ],
    [
      { ...base, decision: 'ALLOW', executionObserved: false },
      'ALLOW_WITHOUT_EXECUTION',
    ],
    [{ ...base, decision: 'DENY' }, 'DENY_EXECUTED'],
    [
      {
        ...base,
        decision: 'DENY',
        decisionAuthoritative: false,
        invocationCorrelated: false,
        executionObserved: false,
      },
      'UNKNOWN_NO_EXECUTION',
    ],
    [{ ...base, decision: 'ALLOW', identityMatches: false }, 'IDENTITY_MISMATCH'],
    [{ ...base, decision: 'ALLOW', stateMatches: false }, 'STATE_MISMATCH'],
  ] as const)('classifies %j as %s', (input, expected) => {
    expect(classifyEvidence(input)).toBe(expected);
  });
});

describe('provenanceForEvidence', () => {
  it('keeps fixture, authoritative, telemetry, derived, and unknown distinct', () => {
    expect(provenanceForEvidence('Seeded demonstration receipt')).toBe('Fixture');
    expect(provenanceForEvidence('Warehouse quantity: 12')).toBe('Authoritative');
    expect(provenanceForEvidence('Latest tool_audit row: 91')).toBe(
      'Execution telemetry',
    );
    expect(provenanceForEvidence('Policy engine configured')).toBe('Derived');
    expect(provenanceForEvidence('No invocation ID observed')).toBe('Unknown');
  });
});
