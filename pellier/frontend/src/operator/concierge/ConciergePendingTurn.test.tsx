/**
 * The live trace opens while the work runs and closes itself when it lands.
 */

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import ConciergePendingTurn from './ConciergePendingTurn'
import type {
  ConciergeInvestigationStep,
  ConciergeStreamAnswer,
} from '../../services/operatorConcierge'

const STEPS: ConciergeInvestigationStep[] = [
  {
    kind: 'read',
    label: 'Read the client record',
    source: 'Local PostgreSQL',
    status: 'complete',
    durationMs: 40,
  },
  {
    kind: 'recall',
    label: 'Recall prior context',
    source: 'AgentCore Memory',
    status: 'running',
    durationMs: null,
  },
]

const ANSWER: ConciergeStreamAnswer = {
  sessionId: 'session-1',
  turnId: 'turn-1',
  status: 'complete',
  replayed: false,
  summary: 'Done.',
}

function head() {
  return screen.getByTestId('operator-concierge-live-activity').querySelector('button')!
}

describe('ConciergePendingTurn', () => {
  it('shows the trace while the work is still running', () => {
    render(<ConciergePendingTurn request="Investigate" steps={STEPS} answer={null} />)
    expect(head()).toHaveAttribute('aria-expanded', 'true')
    // A completed step, which appears only in the expanded list. The running
    // step's label is also echoed in the status line above it.
    expect(screen.getByText('Read the client record')).toBeInTheDocument()
  })

  it('collapses itself once the answer lands, and stays one click away', async () => {
    const user = userEvent.setup()
    const { rerender } = render(
      <ConciergePendingTurn request="Investigate" steps={STEPS} answer={null} />,
    )
    expect(head()).toHaveAttribute('aria-expanded', 'true')

    rerender(<ConciergePendingTurn request="Investigate" steps={STEPS} answer={ANSWER} />)
    expect(head()).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByText('Read the client record')).not.toBeInTheDocument()

    await user.click(head())
    expect(head()).toHaveAttribute('aria-expanded', 'true')
  })

  it('leaves a hand-closed trace closed when the answer lands', async () => {
    const user = userEvent.setup()
    const { rerender } = render(
      <ConciergePendingTurn request="Investigate" steps={STEPS} answer={null} />,
    )
    await user.click(head())
    expect(head()).toHaveAttribute('aria-expanded', 'false')

    // The operator has said what they want; completion must not reopen it.
    rerender(<ConciergePendingTurn request="Investigate" steps={STEPS} answer={ANSWER} />)
    expect(head()).toHaveAttribute('aria-expanded', 'false')
  })
})
