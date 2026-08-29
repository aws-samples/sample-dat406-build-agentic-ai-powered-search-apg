/**
 * A research input, not a consumer chat box.
 *
 * When orchestration is absent the field is read-only and says why. A submit box
 * that visibly accepts a question and can never answer it is worse than no box, and
 * a spinner that never resolves would be a lie told with animation.
 *
 * No attachments, voice, model picker, temperature, agent selector, or sparkle
 * button: none of those capabilities exist, so offering them would be theatre.
 */

import React, { useCallback, useState } from 'react'
import { ArrowUp, LoaderCircle } from 'lucide-react'

interface Props {
  /** Server truth has not arrived yet. Distinct from `enabled: false`. */
  loading?: boolean
  enabled: boolean
  submitting: boolean
  note: string
  error: string | null
  onSubmit: (message: string) => Promise<void>
}

const ConciergeComposer: React.FC<Props> = ({
  loading = false,
  enabled,
  submitting,
  note,
  error,
  onSubmit,
}) => {
  const [value, setValue] = useState('')

  const send = useCallback(async () => {
    const text = value.trim()
    if (!text || submitting || !enabled) return
    setValue('')
    await onSubmit(text)
  }, [enabled, onSubmit, submitting, value])

  const onKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
      // Enter submits, Shift+Enter is a newline.
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault()
        void send()
      }
    },
    [send],
  )

  return (
    <div
      className="operator-concierge-composer"
      data-enabled={enabled}
      data-testid="operator-concierge-composer"
    >
      <label className="operator-concierge-composer-label" htmlFor="concierge-input">
        Ask the Concierge
      </label>
      <textarea
        id="concierge-input"
        className="operator-concierge-input"
        rows={2}
        value={value}
        readOnly={!enabled}
        disabled={submitting}
        placeholder={
          // Three states, not two. Claiming "not yet available" while the config read
          // is still in flight is the same unverified-vs-closed conflation this
          // surface exists to avoid — and it flipped to enabled a second later.
          loading
            ? 'Reading client context…'
            : enabled
              ? 'Ask about this client, an order, or a resolution…'
              : 'Investigation is not yet available on this surface.'
        }
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={onKeyDown}
        aria-describedby="concierge-composer-note"
        data-testid="operator-concierge-input"
      />
      <div className="operator-concierge-composer-foot">
        <p className="operator-concierge-composer-note" id="concierge-composer-note">
          {error
            ? 'The investigation did not complete. The request may already be saved; reopen this client before retrying.'
            : submitting
              ? 'Working on the request…'
              : note}
        </p>
        {enabled ? (
          <button
            type="button"
            className="operator-concierge-ask"
            onClick={() => void send()}
            disabled={submitting || !value.trim()}
            aria-label={submitting ? 'Concierge is working' : 'Ask the Concierge'}
            title={submitting ? 'Concierge is working' : 'Ask the Concierge'}
            data-submitting={submitting}
            data-testid="operator-concierge-ask"
          >
            {submitting ? (
              <LoaderCircle size={15} strokeWidth={2} aria-hidden="true" />
            ) : (
              <ArrowUp size={16} strokeWidth={2} aria-hidden="true" />
            )}
          </button>
        ) : null}
      </div>
    </div>
  )
}

export default ConciergeComposer
