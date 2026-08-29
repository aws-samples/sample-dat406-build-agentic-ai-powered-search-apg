import React from 'react'
import {
  AlertCircle,
  Brain,
  Check,
  Database,
  GitBranch,
  LoaderCircle,
  MessageSquareQuote,
  ShieldCheck,
  Sparkles,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

import type { ConciergeInvestigationStep } from '../../services/operatorConcierge'

interface Props {
  steps: ConciergeInvestigationStep[]
}

function sourceIdentity(source: string): {
  Icon: LucideIcon
  tone:
    | 'database'
    | 'memory'
    | 'model'
    | 'control'
    | 'graph'
    | 'handoff'
    | 'neutral'
} {
  const value = source.toLowerCase()
  if (value.includes('postgres') || value.includes('aurora')) {
    return { Icon: Database, tone: 'database' }
  }
  if (value.includes('memory')) return { Icon: Brain, tone: 'memory' }
  if (value.includes('strands graph')) return { Icon: GitBranch, tone: 'graph' }
  if (value.includes('storefront handoff')) {
    return { Icon: MessageSquareQuote, tone: 'handoff' }
  }
  if (value.includes('bedrock')) return { Icon: Sparkles, tone: 'model' }
  if (value.includes('control') || value.includes('policy')) {
    return { Icon: ShieldCheck, tone: 'control' }
  }
  return { Icon: Database, tone: 'neutral' }
}

function statusIcon(step: ConciergeInvestigationStep): LucideIcon {
  if (step.status === 'running') return LoaderCircle
  if (step.status === 'failed' || step.status === 'unavailable') return AlertCircle
  return Check
}

function durationLabel(durationMs?: number | null): string {
  if (durationMs == null) return ''
  if (durationMs < 1000) return `${durationMs}ms`
  return `${(durationMs / 1000).toFixed(1)}s`
}

function statusLabel(status: ConciergeInvestigationStep['status']): string {
  if (status === 'running') return 'Running'
  if (status === 'failed') return 'Failed'
  if (status === 'unavailable') return 'Unavailable'
  return 'Completed'
}

const ConciergeStepList: React.FC<Props> = ({ steps }) => (
  <ol className="operator-concierge-steps">
    {steps.map((step, index) => {
      const { Icon: SourceIcon, tone } = sourceIdentity(step.source)
      const StatusIcon = statusIcon(step)
      const duration = durationLabel(step.durationMs)
      return (
        <li
          className="operator-concierge-step"
          key={`${step.kind}-${index}`}
          data-step-status={step.status}
          data-source-tone={tone}
        >
          <span className="operator-concierge-step-status" aria-hidden="true">
            <StatusIcon size={14} strokeWidth={1.8} />
          </span>
          <span className="sr-only">Status: {statusLabel(step.status)}</span>
          <span className="operator-concierge-step-copy">
            <span className="operator-concierge-step-label">{step.label}</span>
            {step.result ? (
              <span className="operator-concierge-step-result">{step.result}</span>
            ) : null}
          </span>
          <span className="operator-concierge-step-provenance">
            <span className="operator-concierge-step-source">
              <SourceIcon size={12} strokeWidth={1.8} aria-hidden="true" />
              {step.source}
            </span>
            {duration ? (
              <span className="operator-concierge-step-duration">{duration}</span>
            ) : null}
          </span>
        </li>
      )
    })}
  </ol>
)

export default ConciergeStepList
