import type { LabExercise, LabExerciseId } from './labCatalog';

export type ProofCardStatus =
  | 'complete'
  | 'needs_build'
  | 'needs_run'
  | 'needs_data'
  | 'needs_config'
  | 'pending'
  | 'available';

export type ProvenanceClass =
  | 'Authoritative'
  | 'Execution telemetry'
  | 'Derived'
  | 'Fixture'
  | 'Unknown';

export type EvidenceClassification =
  | 'ALLOW_EXECUTED'
  | 'DENY_NOT_EXECUTED'
  | 'ALLOW_WITHOUT_EXECUTION'
  | 'DENY_EXECUTED'
  | 'UNKNOWN_NO_EXECUTION'
  | 'IDENTITY_MISMATCH'
  | 'STATE_MISMATCH';

export interface ProofCard {
  id: string;
  title: string;
  status: ProofCardStatus;
  summary: string;
  evidenceSource?: string;
  lastUpdated?: string | null;
  evidence: string[];
}

export interface ManagedReceipt {
  present: boolean;
  traceId?: string | null;
  runtimeRequestId?: string | null;
  sessionId?: string | null;
  runId?: string | null;
  invocationId?: string | null;
  providerDecisionEventPresent?: boolean;
  invocationCorrelationVerified?: boolean;
  policyVersion?: string | null;
  policyHash?: string | null;
  gatewayAuditPresent?: boolean;
  gatewayAuditAbsenceVerified?: boolean;
  governedReceiptPresent?: boolean;
  governedDecision?: string;
  governedPrincipalId?: string;
  governedVerifiedSubject?: string;
  governedPolicyName?: string;
  writeOperationPresent?: boolean;
}

export interface ProofBoardPayload {
  status: 'ready' | 'attention' | 'not_ready';
  managedReceipt: ManagedReceipt;
  cards: ProofCard[];
}

export type LabStatusKey =
  | 'evidence_observed'
  | 'ready'
  | 'build_required'
  | 'run_required'
  | 'configuration_required'
  | 'evidence_missing'
  | 'unknown';

export interface LabStatus {
  key: LabStatusKey;
  label: string;
  source: string;
  provenance: ProvenanceClass;
  freshness: string;
}

export interface EvidenceDatum {
  id: string;
  label: string;
  value: string;
  source: string;
  provenance: ProvenanceClass;
  freshness: string;
}

export interface EvidenceClassificationInput {
  decision?: 'ALLOW' | 'DENY';
  decisionAuthoritative: boolean;
  invocationCorrelated: boolean;
  executionObserved: boolean;
  identityMatches?: boolean;
  stateMatches?: boolean;
}

export const CLASSIFICATION_COPY: Record<
  EvidenceClassification,
  { title: string; detail: string; contradiction: boolean }
> = {
  ALLOW_EXECUTED: {
    title: 'Allow and execution are correlated',
    detail:
      'An authoritative ALLOW and the execution outcome share the exact provider invocation identity.',
    contradiction: false,
  },
  DENY_NOT_EXECUTED: {
    title: 'Deny and zero execution are correlated',
    detail:
      'An authoritative DENY and a zero-execution result share the exact provider invocation identity.',
    contradiction: false,
  },
  ALLOW_WITHOUT_EXECUTION: {
    title: 'Contradiction: ALLOW without execution',
    detail:
      'The authoritative decision allowed the request, but no correlated execution outcome was observed.',
    contradiction: true,
  },
  DENY_EXECUTED: {
    title: 'Contradiction: DENY executed',
    detail:
      'The authoritative decision denied the request, but a correlated execution outcome was observed.',
    contradiction: true,
  },
  UNKNOWN_NO_EXECUTION: {
    title: 'Execution state is unknown',
    detail:
      'No authoritative decision and exact invocation correlation are available. Missing execution telemetry is not negative proof.',
    contradiction: false,
  },
  IDENTITY_MISMATCH: {
    title: 'Contradiction: identity mismatch',
    detail:
      'The authenticated principal and the governed resource identity do not match the expected ownership contract.',
    contradiction: true,
  },
  STATE_MISMATCH: {
    title: 'Contradiction: state mismatch',
    detail:
      'The policy, execution, or Aurora state does not match the expected outcome for the correlated invocation.',
    contradiction: true,
  },
};

const STATUS_PRIORITY: ProofCardStatus[] = [
  'needs_build',
  'needs_run',
  'needs_config',
  'needs_data',
  'pending',
  'available',
  'complete',
];

const STATUS_BY_CARD: Record<ProofCardStatus, Omit<LabStatus, 'source' | 'freshness'>> = {
  complete: {
    key: 'evidence_observed',
    label: 'Evidence observed',
    provenance: 'Derived',
  },
  available: {
    key: 'ready',
    label: 'Ready',
    provenance: 'Derived',
  },
  needs_build: {
    key: 'build_required',
    label: 'Build required',
    provenance: 'Derived',
  },
  needs_run: {
    key: 'run_required',
    label: 'Run required',
    provenance: 'Derived',
  },
  needs_config: {
    key: 'configuration_required',
    label: 'Configuration required',
    provenance: 'Derived',
  },
  needs_data: {
    key: 'evidence_missing',
    label: 'Evidence missing',
    provenance: 'Derived',
  },
  pending: {
    key: 'unknown',
    label: 'Unknown',
    provenance: 'Unknown',
  },
};

const MISSING_PATTERN =
  /\b(no |not |missing|unavailable|unknown|was not|false\b|still looks like)\b/i;
const AUTHORITATIVE_PATTERN =
  /\b(aurora|catalog rows?|warehouse|product_catalog|row count|quantity|transaction)\b/i;
const TELEMETRY_PATTERN =
  /\b(tool_audit|audit row|runtime receipt|runtime trace|gateway audit|execution|trace id|write operation)\b/i;
const DERIVED_PATTERN =
  /\b(configured|configuration|model|ready|endpoint|url|cognito|policy engine)\b/i;

function freshnessFor(card?: ProofCard): string {
  if (!card?.lastUpdated) return 'Source timestamp unavailable';
  const parsed = new Date(card.lastUpdated);
  if (Number.isNaN(parsed.getTime())) return card.lastUpdated;
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(parsed);
}

export function classifyEvidence(input: EvidenceClassificationInput): EvidenceClassification {
  if (input.identityMatches === false) return 'IDENTITY_MISMATCH';
  if (input.stateMatches === false) return 'STATE_MISMATCH';

  if (!input.decisionAuthoritative || !input.invocationCorrelated) {
    return input.executionObserved ? 'STATE_MISMATCH' : 'UNKNOWN_NO_EXECUTION';
  }

  if (input.decision === 'ALLOW') {
    return input.executionObserved ? 'ALLOW_EXECUTED' : 'ALLOW_WITHOUT_EXECUTION';
  }

  if (input.decision === 'DENY') {
    return input.executionObserved ? 'DENY_EXECUTED' : 'DENY_NOT_EXECUTED';
  }

  return input.executionObserved ? 'STATE_MISMATCH' : 'UNKNOWN_NO_EXECUTION';
}

export function classificationFromPayload(
  payload: ProofBoardPayload | null,
): EvidenceClassification {
  const receipt = payload?.managedReceipt;
  if (!receipt) return 'UNKNOWN_NO_EXECUTION';

  const decision = receipt.governedDecision?.toUpperCase();
  return classifyEvidence({
    decision: decision === 'ALLOW' || decision === 'DENY' ? decision : undefined,
    decisionAuthoritative: receipt.providerDecisionEventPresent === true,
    invocationCorrelated:
      Boolean(receipt.invocationId) &&
      receipt.invocationCorrelationVerified === true,
    executionObserved:
      receipt.gatewayAuditPresent === true ||
      receipt.writeOperationPresent === true,
  });
}

export function provenanceForEvidence(
  value: string,
  source = '',
): ProvenanceClass {
  const combined = `${value} ${source}`;
  if (/\bfixture|seeded demonstration|synthetic example\b/i.test(combined)) {
    return 'Fixture';
  }
  if (MISSING_PATTERN.test(value)) return 'Unknown';
  if (TELEMETRY_PATTERN.test(combined)) return 'Execution telemetry';
  if (AUTHORITATIVE_PATTERN.test(combined)) return 'Authoritative';
  if (DERIVED_PATTERN.test(combined)) return 'Derived';
  return 'Unknown';
}

export function sourceForEvidence(value: string, card?: ProofCard): string {
  if (/catalog rows?|product_catalog/i.test(value)) return 'pellier.product_catalog';
  if (/warehouse|quantity|transaction/i.test(value)) return 'Aurora PostgreSQL';
  if (/tool_audit|audit row/i.test(value)) return 'pellier.tool_audit';
  if (/runtime receipt|runtime trace|trace id/i.test(value)) {
    return 'AgentCore Runtime response';
  }
  if (/gateway audit|execution/i.test(value)) return 'Gateway execution telemetry';
  if (/model|configured|configuration|endpoint|cognito|policy engine/i.test(value)) {
    return 'Backend configuration';
  }
  return card?.evidenceSource ?? 'Proof-board response';
}

export function statusForExercise(
  exercise: LabExercise,
  payload: ProofBoardPayload | null,
): LabStatus {
  if (exercise.id === 'governed-evidence-bundle') {
    return {
      key: 'unknown',
      label: 'Unknown',
      source: 'No scoped bundle endpoint',
      provenance: 'Unknown',
      freshness: 'Endpoint unavailable',
    };
  }

  if (!payload) {
    return {
      key: 'unknown',
      label: 'Unknown',
      source: 'Proof-board response unavailable',
      provenance: 'Unknown',
      freshness: 'Not observed',
    };
  }

  const cards = exercise.proofCardIds
    .map((id) => payload.cards.find((card) => card.id === id))
    .filter((card): card is ProofCard => Boolean(card));

  if (cards.length !== exercise.proofCardIds.length || cards.length === 0) {
    return {
      key: 'unknown',
      label: 'Unknown',
      source: 'Required proof card missing',
      provenance: 'Unknown',
      freshness: 'Not observed',
    };
  }

  const allComplete = cards.every((card) => card.status === 'complete');
  const selectedStatus = allComplete
    ? 'complete'
    : STATUS_PRIORITY.find((status) =>
        cards.some((card) => card.status === status),
      ) ?? 'pending';
  const mapping = STATUS_BY_CARD[selectedStatus];

  return {
    ...mapping,
    source: cards.map((card) => `proof-board:${card.id}`).join(', '),
    freshness:
      cards.map(freshnessFor).find((value) => value !== 'Source timestamp unavailable') ??
      'Source timestamp unavailable',
  };
}

export function evidenceForExercise(
  exercise: LabExercise,
  payload: ProofBoardPayload | null,
): EvidenceDatum[] {
  if (!payload || exercise.proofCardIds.length === 0) return [];

  return exercise.proofCardIds.flatMap((cardId) => {
    const card = payload.cards.find((candidate) => candidate.id === cardId);
    if (!card) return [];
    return card.evidence.map((value, index) => {
      const source = sourceForEvidence(value, card);
      return {
        id: `${card.id}-${index}`,
        label: card.title,
        value,
        source,
        provenance: provenanceForEvidence(value, source),
        freshness: freshnessFor(card),
      };
    });
  });
}

export function evidenceIdentity(
  payload: ProofBoardPayload | null,
): EvidenceDatum[] {
  const receipt = payload?.managedReceipt;
  const values: Array<{
    id: string;
    label: string;
    value?: string | null;
    source: string;
  }> = [
    {
      id: 'run',
      label: 'Run ID',
      value: receipt?.runId,
      source: 'Scoped verifier',
    },
    {
      id: 'session',
      label: 'Session ID',
      value: receipt?.sessionId,
      source: 'Runtime response',
    },
    {
      id: 'trace',
      label: 'Trace ID',
      value: receipt?.traceId,
      source: 'Runtime response',
    },
    {
      id: 'invocation',
      label: 'Invocation ID',
      value: receipt?.invocationId,
      source: 'Provider decision event',
    },
  ];

  return values.map(({ id, label, value, source }) => ({
    id,
    label,
    value: value || 'Unknown',
    source,
    provenance: value ? 'Execution telemetry' : 'Unknown',
    freshness: value ? 'Source timestamp unavailable' : 'Not observed',
  }));
}

export function policyEvidence(
  payload: ProofBoardPayload | null,
): EvidenceDatum[] {
  const receipt = payload?.managedReceipt;
  const values: Array<{
    id: string;
    label: string;
    value?: string | null;
    source: string;
  }> = [
    {
      id: 'policy',
      label: 'Policy ID',
      value: receipt?.governedPolicyName,
      source: 'Governed receipt',
    },
    {
      id: 'version',
      label: 'Policy version',
      value: receipt?.policyVersion,
      source: 'Provider decision event',
    },
    {
      id: 'hash',
      label: 'Policy hash',
      value: receipt?.policyHash,
      source: 'Provider decision event',
    },
  ];

  return values.map(({ id, label, value, source }) => ({
    id,
    label,
    value: value || 'Unknown',
    source,
    provenance: value ? 'Execution telemetry' : 'Unknown',
    freshness: value ? 'Source timestamp unavailable' : 'Not observed',
  }));
}

export function findProofCard(
  payload: ProofBoardPayload | null,
  cardId: string,
): ProofCard | undefined {
  return payload?.cards.find((card) => card.id === cardId);
}

export function isLabExerciseId(value: string): value is LabExerciseId {
  return [
    'grounded-inventory',
    'retrieval-acceptance',
    'exactly-once-return',
    'fail-closed-policy',
    'governed-evidence-bundle',
  ].includes(value);
}
