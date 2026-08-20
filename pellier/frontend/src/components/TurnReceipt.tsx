import { useEffect, useState } from 'react'
import { Check, Copy } from 'lucide-react'
import { CHAT_TRUST } from '../copy'
import '../styles/chat-outcomes.css'

interface TurnReceiptProps {
  reference: string
  surface?: 'pellier' | 'observatory'
}

function shortReference(reference: string): string {
  if (reference.length <= 20) return reference
  return `${reference.slice(0, 10)}...${reference.slice(-6)}`
}

export default function TurnReceipt({
  reference,
  surface = 'pellier',
}: TurnReceiptProps) {
  const [copied, setCopied] = useState(false)

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
    >
      <span className="turn-receipt__status">
        <Check size={13} aria-hidden="true" />
        {CHAT_TRUST.VERIFIED}
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
