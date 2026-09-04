/**
 * TurnReceipt: the copyable turn reference plus two badges that mean
 * different things.
 *
 *   Response complete   the stream finished (a transport fact)
 *   Evidence recorded   the durable ledger for this turn_id reports every
 *                       required sufficiency check satisfied (a data fact)
 *
 * The second badge is fetched from the principal-scoped ledger endpoint and
 * never inferred from the first. While the fetch is in flight, or when the
 * caller has no verified session to read a ledger with, the receipt says
 * nothing about evidence.
 */
import { useEffect, useState } from 'react'
import { Check, Copy, FileCheck2 } from 'lucide-react'
import { useOptionalAuth } from '../contexts/AuthContext'
import { CHAT_TRUST } from '../copy'
import {
  fetchTurnEvidenceLedger,
  requiredEvidenceSatisfied,
} from '../services/evidenceLedger'
import '../styles/turn-receipt.css'

interface TurnReceiptProps {
  /** The reference shown and copied: a trace id, or the turn id as fallback. */
  reference: string
  /** Stable per-turn id used to read the evidence ledger. */
  turnId?: string | null
  /** True once the stream has finished for this turn. */
  complete?: boolean
  surface?: 'pellier' | 'observatory'
}

function shortReference(reference: string): string {
  if (reference.length <= 20) return reference
  return `${reference.slice(0, 10)}...${reference.slice(-6)}`
}

/**
 * Whether the evidence ledger for `turnId` is fully recorded.
 *
 * Resolves to `null` while unknown: before the fetch settles, when there is
 * no turn id, and when the caller cannot read a principal-scoped ledger.
 */
function useEvidenceRecorded(
  turnId: string | null | undefined,
  enabled: boolean,
): boolean | null {
  const isAuthenticated = useOptionalAuth()?.isAuthenticated ?? false
  const [recorded, setRecorded] = useState<boolean | null>(null)

  useEffect(() => {
    setRecorded(null)
    if (!enabled || !turnId || !isAuthenticated) return
    const controller = new AbortController()
    fetchTurnEvidenceLedger(turnId, controller.signal)
      .then((ledger) => {
        if (controller.signal.aborted) return
        setRecorded(
          ledger ? requiredEvidenceSatisfied(ledger.evidenceSufficiency) : null,
        )
      })
      .catch(() => {
        if (!controller.signal.aborted) setRecorded(null)
      })
    return () => controller.abort()
  }, [enabled, turnId, isAuthenticated])

  return recorded
}

export default function TurnReceipt({
  reference,
  turnId,
  complete = true,
  surface = 'pellier',
}: TurnReceiptProps) {
  const [copied, setCopied] = useState(false)
  const evidenceRecorded = useEvidenceRecorded(turnId, complete)

  useEffect(() => {
    if (!copied) return
    const timeout = window.setTimeout(() => setCopied(false), 1800)
    return () => window.clearTimeout(timeout)
  }, [copied])

  const copyReference = async () => {
    try {
      await navigator.clipboard.writeText(reference)
    } catch {
      const textarea = document.createElement('textarea')
      textarea.value = reference
      textarea.style.position = 'fixed'
      textarea.style.opacity = '0'
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      textarea.remove()
    }
    setCopied(true)
  }

  return (
    <div
      className={`turn-receipt turn-receipt--${surface}`}
      data-testid="turn-receipt"
      data-complete={complete ? 'true' : 'false'}
      data-evidence={evidenceRecorded === true ? 'recorded' : 'unknown'}
    >
      <span className="turn-receipt__badges">
        {complete ? (
          <span className="turn-receipt__status" data-testid="turn-response-complete">
            <Check size={13} aria-hidden="true" />
            {CHAT_TRUST.RESPONSE_COMPLETE}
          </span>
        ) : null}
        {evidenceRecorded === true ? (
          <span
            className="turn-receipt__status turn-receipt__status--evidence"
            data-testid="turn-evidence-recorded"
          >
            <FileCheck2 size={13} aria-hidden="true" />
            {CHAT_TRUST.EVIDENCE_RECORDED}
          </span>
        ) : null}
      </span>
      <code title={reference}>{shortReference(reference)}</code>
      <button
        type="button"
        className="turn-receipt__copy"
        onClick={() => void copyReference()}
        aria-label={
          copied ? CHAT_TRUST.COPIED_REFERENCE : CHAT_TRUST.COPY_REFERENCE
        }
        title={
          copied ? CHAT_TRUST.COPIED_REFERENCE : CHAT_TRUST.COPY_REFERENCE
        }
      >
        {copied ? <Check size={14} /> : <Copy size={14} />}
      </button>
    </div>
  )
}
