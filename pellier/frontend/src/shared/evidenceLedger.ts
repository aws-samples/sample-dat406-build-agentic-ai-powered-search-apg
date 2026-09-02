export type EvidenceLedgerEventKind =
  | 'route'
  | 'plan'
  | 'memory'
  | 'retrieval'
  | 'rerank'
  | 'model'
  | 'tool'
  | 'policy'
  | 'aurora'
  | 'write'
  | 'response'

export type EvidenceLedgerPhase =
  | 'routing'
  | 'context'
  | 'evidence'
  | 'reasoning'
  | 'governance'
  | 'execution'
  | 'terminal'

export type EvidenceLedgerStatus =
  | 'planned'
  | 'running'
  | 'succeeded'
  | 'failed'
  | 'denied'
  | 'not_reached'
  | 'not_enforced'
  | 'unavailable'

export type EvidenceLedgerProvenance =
  | 'live-emitted-event'
  | 'aurora-receipt'
  | 'cloudwatch-span'
  | 'agentcore-service-telemetry'
  | 'presentation-only'

export interface EvidenceReference {
  kind: string
  id: string
}

export interface EvidenceLedgerEvent {
  sequence: number
  eventKind: EvidenceLedgerEventKind
  phase: EvidenceLedgerPhase
  status: EvidenceLedgerStatus
  provenance: EvidenceLedgerProvenance
  occurredAt?: string | null
  durationMs?: number | null
  turnId: string
  sessionId?: string | null
  principalSub?: string | null
  rail?: string | null
  traceId?: string | null
  evidenceRef: EvidenceReference
  title: string
  summary: string
  details?: Record<string, unknown>
  sql?: string | null
  rows?: Record<string, unknown>[]
}

export type EvidenceSufficiencyStatus =
  | 'satisfied'
  | 'missing'
  | 'unavailable'
  | 'not_applicable'
  | 'not_reached'
  | 'not_enforced'

export interface EvidenceSufficiencyCheck {
  id: string
  label: string
  status: EvidenceSufficiencyStatus
  detail: string
}

export interface EvidenceLedger {
  version: string
  authority: 'canonical-receipt-projection'
  principalScoped: boolean
  turnId?: string
  turnIds?: string[]
  sessionId?: string | null
  events: EvidenceLedgerEvent[]
  evidenceSufficiency: EvidenceSufficiencyCheck[]
}
