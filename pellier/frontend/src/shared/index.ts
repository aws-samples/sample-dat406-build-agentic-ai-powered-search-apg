/**
 * Shared atoms used by BOTH the Pellier storefront and the Observatory
 * observatory. Importing from `../../shared` (or `../shared`) keeps
 * the two surfaces visually and semantically aligned.
 */
export { TraceChip } from './TraceChip'
export type { TraceChipProps } from './TraceChip'

export { SurfaceCrossLink } from './SurfaceCrossLink'
export type { SurfaceCrossLinkProps, CrossLinkDirection } from './SurfaceCrossLink'

export { PresencePill } from './PresencePill'
export type { PresencePillProps, PresenceSurface, PresenceMode } from './PresencePill'

export {
  AGENT_VOCABULARY,
  lookupVocab,
} from './agentVocabulary'
export type { AgentToolName } from './agentVocabulary'

export { GovernedSeal } from './GovernedSeal'
export type { GovernedSealProps } from './GovernedSeal'

export { PolicyDecisionBadge } from './PolicyDecisionBadge'
export type { PolicyDecisionBadgeProps } from './PolicyDecisionBadge'

export {
  PROVENANCE_DETAIL,
  PROVENANCE_LABEL,
  RAIL_STATE_DETAIL,
  RAIL_STATE_LABEL,
  resolveRailState,
} from './governedTypes'
export type {
  EvidenceProvenance,
  ExecutionRail,
  GovernedRailState,
  PolicyDecision,
  RailDecision,
  RailDegradation,
} from './governedTypes'

export {
  TURN_QUERY_KEY,
  pellierRoute,
  inspectorHref,
  inspectorRoute,
  receiptHref,
  receiptRoute,
  turnIdFromSearch,
} from './governedReceipt'
export type { ReceiptTarget } from './governedReceipt'

