/**
 * The Operator desk has a distinct sign-in moment from the shopper storefront.
 *
 * It deliberately offers one account path: Cognito's native email/password
 * flow, where the seeded Operator account belongs. That keeps the desk's
 * authorization boundary clear without exposing implementation details or
 * presenting providers that cannot grant Operator access.
 */
import { useCallback, useEffect, useRef } from 'react'
import { X } from 'lucide-react'
import ResponsiveImage from '../../components/ResponsiveImage'
import { OPERATOR_SIGNIN_MODAL } from '../../copy'
import { useUI } from '../../contexts/UIContext'
import { SectionEyebrow } from '../../shared'
import { useFocusTrap } from '../../shared/useFocusTrap'
import { redirectToSignIn } from '../../utils/auth'

export default function OperatorSignInModal() {
  const { activeModal, closeModal } = useUI()
  const isOpen = activeModal === 'operator-auth'
  const primaryActionRef = useRef<HTMLButtonElement>(null)
  const openerRef = useRef<HTMLElement | null>(null)
  const dialogRef = useRef<HTMLElement | null>(null)
  const close = useCallback(
    () => closeModal({ restoreDrawer: false }),
    [closeModal],
  )

  // Escape closes and Tab stays inside. Focus placement stays with the effect
  // below: this desk opens on its one action, not on the dialog frame.
  useFocusTrap({
    containerRef: dialogRef,
    active: isOpen,
    onClose: close,
    manageFocus: false,
  })

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
      onClick={close}
    >
      {/*
       * The house plate behind the dialog. `hero-fresh-2` is already the
       * desk's atmosphere image, so signing in reads as arriving at the same
       * room rather than at a separate login product; its wide empty plaster
       * at the right is what makes room for the sheet.
       *
       * Through ResponsiveImage, never a CSS `url()`: the AVIF and WebP
       * derivatives are used and every URL passes the Workshop Studio base
       * path. The scrim lives on the overlay's ::after, and no cream text sits
       * on the photograph — the dialog stays opaque raised paper, so form
       * contrast is untouched.
       */}
      <ResponsiveImage
        src="/products/hero-fresh-2.png"
        widths={[960, 1600]}
        sizes="100vw"
        pictureClassName="operator-signin-plate"
        className="operator-signin-plate-image"
        alt=""
        aria-hidden="true"
        decoding="async"
      />
      <section
        ref={dialogRef}
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
          onClick={close}
          aria-label="Close Operator sign-in"
          data-testid="operator-signin-modal-close"
        >
          <X aria-hidden />
        </button>

        {/* The wrapper carries the block layout and the spacing. SectionEyebrow
            sets `display: inline-flex` inline, and an inline style beats a
            class rule, so styling the primitive itself would have needed an
            `!important` to put it on its own line. */}
        <div className="operator-signin-eyebrow">
          <SectionEyebrow tone="brand">
            {OPERATOR_SIGNIN_MODAL.EYEBROW}
          </SectionEyebrow>
        </div>
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
        </button>

        <p className="operator-signin-footer">
          {OPERATOR_SIGNIN_MODAL.FOOTER}
        </p>
      </section>
    </div>
  )
}
