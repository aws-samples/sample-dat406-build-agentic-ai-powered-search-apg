/**
 * Prior resolutions: the surface for Aurora episodic recall.
 *
 * The assertions that matter are negative. This card must not turn a derived memory
 * into a claim: no similarity score, no distance, no vector, no "3 matches found"
 * confidence framing, and no implication that a recall which fell back to recency was
 * measured by meaning.
 */

import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import ConciergePriorResolutions from './ConciergePriorResolutions'
import type { ConciergeEpisode } from '../../services/operatorConcierge'

function episode(over: Partial<ConciergeEpisode> = {}): ConciergeEpisode {
  return {
    episodeId: 37,
    customerId: 'CUST-THEO',
    episodeType: 'return_resolution',
    situation: 'CUST-THEO asked for a damaged return on product 37.',
    resolution: 'Return 37 was created through the governed path.',
    humanOutcome: 'confirmed',
    policyOutcome: 'allow',
    auroraOutcome: 'applied',
    reviewId: 40,
    executionTurnId: 'turn-' + 'a'.repeat(32),
    sourceTurnId: 'turn-' + 'b'.repeat(32),
    createdAt: '2026-08-27T15:20:00Z',
    similarity: 0.87,
    evidenceSummary: {},
    actionSummary: {},
    ...over,
  }
}

function renderCard(
  episodes: ConciergeEpisode[],
  retrieval?: { mode: 'semantic' | 'recent'; matched: number },
) {
  return render(
    <MemoryRouter>
      <ConciergePriorResolutions prior={{ episodes, retrieval }} />
    </MemoryRouter>,
  )
}

describe('ConciergePriorResolutions', () => {
  it('names the kind of situation in words an operator would use', () => {
    renderCard([episode()])
    expect(screen.getByText('Damaged-item return')).toBeTruthy()
  })

  it('states all three governance outcomes, not one verdict', () => {
    renderCard([episode()])
    const row = screen.getByTestId('operator-concierge-prior-37')
    expect(row.textContent).toContain('Human confirmed')
    expect(row.textContent).toContain('Policy allowed')
    expect(row.textContent).toContain('Aurora applied')
  })

  it('keeps a policy allow beside a database refusal', () => {
    // Amara's shape. Flattening it into "failed" would destroy the only row that shows
    // authorization and data access answering differently.
    renderCard([
      episode({ episodeId: 38, policyOutcome: 'allow', auroraOutcome: 'refused' }),
    ])
    const row = screen.getByTestId('operator-concierge-prior-38')
    expect(row.textContent).toContain('Policy allowed')
    expect(row.textContent).toContain('Aurora refused')
    expect(row).toHaveAttribute('data-outcome', 'refused')
  })

  it('shows a policy denial without implying the database was involved', () => {
    renderCard([
      episode({ episodeId: 36, policyOutcome: 'deny', auroraOutcome: 'not_attempted' }),
    ])
    const row = screen.getByTestId('operator-concierge-prior-36')
    expect(row.textContent).toContain('Policy denied')
    expect(row.textContent).toContain('Aurora not reached')
  })

  it('never shows a similarity score, a distance, or a vector', () => {
    const { container } = renderCard([episode()], { mode: 'semantic', matched: 1 })
    const text = container.textContent ?? ''
    expect(text).not.toContain('0.87')
    for (const jargon of ['similarity', 'distance', 'cosine', 'vector', 'HNSW', 'pgvector', 'embedding']) {
      expect(text.toLowerCase()).not.toContain(jargon.toLowerCase())
    }
  })

  it('says whether similarity was measured or merely assumed', () => {
    const semantic = renderCard([episode()], { mode: 'semantic', matched: 1 })
    expect(
      screen.getByTestId('operator-concierge-prior-retrieval').textContent,
    ).toContain('Matched by meaning')
    semantic.unmount()

    renderCard([episode()], { mode: 'recent', matched: 1 })
    const note = screen.getByTestId('operator-concierge-prior-retrieval').textContent
    expect(note).toContain('Semantic matching was unavailable')
    expect(note).toContain('ordered by date')
  })

  it('offers the evidence rather than asserting it', () => {
    renderCard([episode()])
    const link = screen.getByTestId('operator-concierge-prior-evidence-37')
    expect(link.getAttribute('href')).toBe('/operator/reviews/40')
  })

  it('omits the evidence link when there is no review to inspect', () => {
    renderCard([episode({ reviewId: null })])
    expect(screen.queryByTestId('operator-concierge-prior-evidence-37')).toBeNull()
  })

  it('reports an empty recall as an answer', () => {
    // A client with no prior governed resolutions has none. A silent gap would read as
    // a failed search, and a fabricated row would be the whole failure this substrate
    // is written to avoid.
    renderCard([])
    const card = screen.getByTestId('operator-concierge-prior')
    expect(card).toHaveAttribute('data-empty', 'true')
    expect(card.textContent).toContain('No prior governed resolutions are on record')
  })

  it('numbers the rows rather than carding them', () => {
    renderCard([episode({ episodeId: 1 }), episode({ episodeId: 2 })])
    expect(screen.getByTestId('operator-concierge-prior').querySelector('ol')).toBeTruthy()
  })
})
