/**
 * Observable system activity. Never a reasoning trace.
 *
 * The distinction is the point: these rows are operations that happened and the
 * system that performed them. No model interiors, no "let me think through this",
 * no hidden prompt state — the backend refuses to persist those keys, and this
 * component has nowhere to render them.
 *
 * A source row appears only when that system actually participated. Listing every
 * service in the architecture would be decoration.
 */

import React, { useState } from 'react'
import { ChevronDown } from 'lucide-react'

import type {
  ConciergeInvestigationStep,
  ConciergeOrchestration,
} from '../../services/operatorConcierge'
import ConciergeStepList from './ConciergeStepList'

interface Props {
  steps: ConciergeInvestigationStep[]
  durationMs?: number | null
  orchestration?: ConciergeOrchestration
}

function nodeLabel(nodeId: string): string {
  return nodeId
    .replace(/-/g, ' ')
    .replace(/\b\w/g, (character) => character.toUpperCase())
}

const ConciergeInvestigation: React.FC<Props> = ({
  steps,
  durationMs,
  orchestration,
}) => {
  const [open, setOpen] = useState(false)
  if (!steps.length) return null

  const measured = durationMs ?? steps.reduce((sum, s) => sum + (s.durationMs ?? 0), 0)
  const sources = new Set(steps.map((step) => step.source)).size

  return (
    <section className="operator-concierge-investigation"
             data-testid="operator-concierge-investigation">
      <button
        type="button"
        className="operator-concierge-investigation-head"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <span className="operator-concierge-eyebrow">How this answer was built</span>
        <span className="operator-concierge-investigation-meta">
          {steps.length} {steps.length === 1 ? 'step' : 'steps'}
          {` · ${sources} ${sources === 1 ? 'source' : 'sources'}`}
          {/* Only a measured duration. Never an invented one. */}
          {measured > 0 ? ` · ${(measured / 1000).toFixed(1)}s` : ''}
        </span>
        <ChevronDown
          className="operator-concierge-disclosure-icon"
          size={15}
          strokeWidth={1.8}
          aria-hidden="true"
        />
      </button>
      {open ? (
        <>
          {orchestration?.executedNodes?.length ? (
            <div
              className="operator-concierge-graph"
              data-testid="operator-concierge-graph"
            >
              <div className="operator-concierge-graph-meta">
                <span>{orchestration.pattern ?? 'strands-graph'}</span>
                <span>{orchestration.execution ?? 'application-orchestrated'}</span>
                {orchestration.deploymentTarget ? (
                  <span>Target: {orchestration.deploymentTarget}</span>
                ) : null}
              </div>
              <ol className="operator-concierge-graph-nodes">
                {orchestration.executedNodes.map((node) => (
                  <li key={node.nodeId} data-node-status={node.status}>
                    <span>{nodeLabel(node.nodeId)}</span>
                    {node.durationMs != null ? (
                      <small>{node.durationMs}ms</small>
                    ) : null}
                  </li>
                ))}
              </ol>
              {orchestration.checkpoint?.state ? (
                <p className="operator-concierge-checkpoint">
                  Checkpoint: {orchestration.checkpoint.state.replace(/_/g, ' ')}
                  {orchestration.checkpoint.reviewId
                    ? ` · review ${orchestration.checkpoint.reviewId}`
                    : ''}
                </p>
              ) : null}
            </div>
          ) : null}
          <ConciergeStepList steps={steps} />
        </>
      ) : null}
    </section>
  )
}

export default ConciergeInvestigation
