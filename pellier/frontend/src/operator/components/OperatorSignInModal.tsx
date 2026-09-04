/**
 * The Operator desk has a distinct sign-in moment from the shopper storefront.
 *
 * It deliberately offers one account path: Cognito's native email/password
 * flow, where the seeded Operator account belongs. That keeps the desk's
 * authorization boundary clear without exposing implementation details or
 * presenting providers that cannot grant Operator access.
 */
import { useEffect, useRef } from 'react'
import { ArrowRight, ShieldCheck, X } from 'lucide-react'
import { OPERATOR_SIGNIN_MODAL } from '../../copy'
import { useUI } from '../../contexts/UIContext'
import { redirectToSignIn } from '../../utils/auth'

export default function OperatorSignInModal() {
  const { activeModal, closeModal } = useUI()
  const isOpen = activeModal === 'operator-auth'
  const primaryActionRef = useRef<HTMLButtonElement>(null)
  const openerRef = useRef<HTMLElement | null>(null)

  useEffect(() => {
    if (!isOpen || typeof document === 'undefined') return

    openerRef.current =
      document.activeElement instanceof HTMLElement ? document.activeElement : null
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    window.requestAnimationFrame(() => primaryActionRef.current?.focus())

    return () => {
      document.body.style.overflow = previousOverflow
      openerRef.current?.focus()
      openerRef.current = null
    }
  }, [isOpen])

  if (!isOpen) return null

  const returnTo =
    typeof window === 'undefined'
      ? '/operator'
      : `${window.location.pathname}${window.location.search}`

  return (
    <div
      className="operator-signin-overlay"
      data-testid="operator-signin-modal-backdrop"
      role="presentation"
      onClick={() => closeModal({ restoreDrawer: false })}
    >
      <section
        className="operator-signin-dialog"
        data-testid="operator-signin-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="operator-signin-modal-title"
        aria-describedby="operator-signin-modal-description"
        onClick={(event) => event.stopPropagation()}
      >
        <button
          className="operator-signin-close"
          type="button"
          onClick={() => closeModal({ restoreDrawer: false })}
          aria-label="Close Operator sign-in"
          data-testid="operator-signin-modal-close"
        >
          <X aria-hidden />
        </button>

        <div className="operator-signin-mark" aria-hidden>
          <ShieldCheck />
        </div>
        <p className="operator-signin-eyebrow">
          {OPERATOR_SIGNIN_MODAL.EYEBROW}
        </p>
        <h2 id="operator-signin-modal-title">
          {OPERATOR_SIGNIN_MODAL.TITLE}
        </h2>
        <p
          id="operator-signin-modal-description"
          className="operator-signin-description"
        >
          {OPERATOR_SIGNIN_MODAL.BODY}
        </p>

        <button
          ref={primaryActionRef}
          type="button"
          className="operator-signin-primary-action"
          onClick={() => redirectToSignIn('email', { returnTo })}
          data-testid="operator-signin-modal-continue"
        >
          <span>{OPERATOR_SIGNIN_MODAL.ACTION}</span>
          <ArrowRight aria-hidden />
        </button>

        <p className="operator-signin-footer">
          {OPERATOR_SIGNIN_MODAL.FOOTER}
        </p>
      </section>
    </div>
  )
}
