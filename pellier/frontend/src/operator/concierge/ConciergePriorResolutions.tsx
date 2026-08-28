/**
 * Prior resolutions: how comparable situations actually ended.
 *
 * The one question the client record cannot answer. Orders, tickets and returns say
 * what the state IS; `pellier.operator_episodes` says how a situation like this went,
 * and each row carries the three governance answers separately because they regularly
 * disagree — a policy ALLOW beside an Aurora refusal is the most instructive thing an
 * operator can be shown before deciding.
 *
 * What is deliberately absent: a similarity score on the card, a distance, a vector, a
 * confidence percentage, and the word HNSW. An operator is deciding what to do about a
 * client, not tuning a retriever. The retrieval mechanics belong in the expanded
 * technical evidence and in the Observatory, and `source_turn_id` is there for anyone
 * who wants to walk the lineage.
 *
 * These rows are DERIVED memories. The authoritative artifacts are the approval, the
 * execution receipt, `tool_audit`, `write_operations` and the domain rows, which is why
 * the footer offers the evidence rather than asserting it here.
 */

import React from 'react'
import { Link } from 'react-router-dom'

import type { ConciergePriorResolutions as PriorResolutions } from '../../services/operatorConcierge'

/** Episode kind to a phrase an operator would use. */
const KIND_LABELS: Record<string, string> = {
  return_resolution: 'Damaged-item return',
  replacement_offered: 'Replacement offered',
  credit_issued: 'Goodwill credit',
  escalation: 'Escalated to a person',
  inventory_correction: 'Inventory correction',
}

/** The three axes, in the same words the Action Assurance component uses. */
const HUMAN: Record<string, string> = {
  confirmed: 'Human confirmed',
  declined: 'Human declined',
  pending: 'Awaiting a person',
  not_required: 'No confirmation required',
}

const POLICY: Record<string, string> = {
  allow: 'Policy allowed',
  deny: 'Policy denied',
  would_deny: 'Policy would have denied',
  not_evaluated: 'Policy not evaluated',
}

const AURORA: Record<string, string> = {
  applied: 'Aurora applied',
  refused: 'Aurora refused',
  rolled_back: 'Aurora rolled back',
  not_attempted: 'Aurora not reached',
}

function kindLabel(kind: string): string {
  return KIND_LABELS[kind] ?? kind.replace(/_/g, ' ')
}

/** A date an operator can place, without a time nobody needs. */
function when(iso: string | null): string {
  if (!iso) return ''
  const parsed = new Date(iso)
  if (Number.isNaN(parsed.getTime())) return ''
  return parsed.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

interface Props {
  prior: PriorResolutions
}

const ConciergePriorResolutions: React.FC<Props> = ({ prior }) => {
  const episodes = prior.episodes ?? []

  // An empty recall is an answer. A client with no prior governed resolutions has
  // none, and saying so is better than a silent gap that reads as a failed search.
  if (!episodes.length) {
    return (
      <section
        className="operator-concierge-prior"
        data-testid="operator-concierge-prior"
        data-empty="true"
      >
        <span className="operator-concierge-eyebrow">Prior resolutions</span>
        <p className="operator-concierge-prior-empty">
          No prior governed resolutions are on record for this client.
        </p>
      </section>
    )
  }

  return (
    <section
      className="operator-concierge-prior"
      data-testid="operator-concierge-prior"
    >
      <span className="operator-concierge-eyebrow">
        Prior {episodes.length === 1 ? 'resolution' : 'resolutions'}
      </span>
      <ol className="operator-concierge-prior-list">
        {episodes.map((episode) => (
          <li
            className="operator-concierge-prior-item"
            key={episode.episodeId ?? `${episode.executionTurnId}-${episode.episodeType}`}
            data-outcome={episode.auroraOutcome}
            data-testid={`operator-concierge-prior-${episode.episodeId ?? 'row'}`}
          >
            <p className="operator-concierge-prior-kind">
              {kindLabel(episode.episodeType)}
            </p>
            <p className="operator-concierge-prior-axes">
              {/* Three answers, not one verdict. Read as a sentence rather than a
                  badge row so an ALLOW-then-refused reads as the story it is. */}
              {[
                HUMAN[episode.humanOutcome] ?? episode.humanOutcome,
                POLICY[episode.policyOutcome] ?? episode.policyOutcome,
                AURORA[episode.auroraOutcome] ?? episode.auroraOutcome,
              ].join(' · ')}
            </p>
            {episode.resolution ? (
              <p className="operator-concierge-prior-resolution">
                {episode.resolution}
              </p>
            ) : null}
            <p className="operator-concierge-prior-meta">
              <span>Aurora</span>
              {when(episode.createdAt) ? (
                <span>{when(episode.createdAt)}</span>
              ) : null}
              {episode.reviewId ? (
                <Link
                  to={`/operator/reviews/${episode.reviewId}`}
                  data-testid={`operator-concierge-prior-evidence-${episode.episodeId ?? 'row'}`}
                >
                  Inspect evidence <span aria-hidden="true">&rarr;</span>
                </Link>
              ) : null}
            </p>
          </li>
        ))}
      </ol>
      {/* How the match was made, stated plainly and once. An operator told "3 similar"
          deserves to know whether similarity was measured or merely assumed. */}
      {prior.retrieval ? (
        <p
          className="operator-concierge-prior-retrieval"
          data-testid="operator-concierge-prior-retrieval"
        >
          {prior.retrieval.mode === 'semantic'
            ? 'Matched by meaning against this client’s recorded outcomes.'
            : 'Most recent outcomes for this client. Semantic matching was unavailable, so these are ordered by date rather than by similarity.'}
        </p>
      ) : null}
    </section>
  )
}

export default ConciergePriorResolutions
