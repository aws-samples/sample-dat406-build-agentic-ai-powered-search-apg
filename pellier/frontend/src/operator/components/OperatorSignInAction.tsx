import React from 'react'
import { useUI } from '../../contexts/UIContext'

interface Props {
  /**
   * What signing in gives the operator, phrased as the outcome.
   *
   * The gated surface already says sign-in is required, in a heading and again
   * in a sentence, and the topbar carries a persistent account control. A
   * fourth control reading "Sign in" made one screen state the same
   * instruction three times over, so this one names the destination instead.
   */
  unlocks?: string
}

/**
 * The recovery action on a Cognito-protected operator surface.
 *
 * Deliberately not the account pill. It used to render
 * `pellier-account-pill operator-auth-signin` with a person icon and the word
 * "Sign in", which is exactly the topbar control, so a signed-out desk showed
 * two identical pills a few hundred pixels apart and it was not obvious they
 * were the same door. This is the page's primary action and looks like one;
 * the topbar keeps the global control.
 */
const OperatorSignInAction: React.FC<Props> = ({ unlocks }) => {
  const { openModal } = useUI()

  return (
    <button
      type="button"
      className="operator-state-signin"
      onClick={() => openModal('operator-auth')}
      data-testid="operator-state-sign-in"
    >
      {unlocks ? `Sign in to ${unlocks}` : 'Sign in'}
    </button>
  )
}

export default OperatorSignInAction
