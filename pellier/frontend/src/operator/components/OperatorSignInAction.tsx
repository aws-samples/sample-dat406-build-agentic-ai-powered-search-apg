import React from 'react'
import { User } from 'lucide-react'
import { useUI } from '../../contexts/UIContext'

/** A consistent recovery action for a Cognito-protected operator surface. */
const OperatorSignInAction: React.FC = () => {
  const { openModal } = useUI()

  return (
    <button
      type="button"
      className="pellier-account-pill operator-auth-signin operator-state-signin"
      onClick={() => openModal('operator-auth')}
      data-testid="operator-state-sign-in"
    >
      <User className="operator-topbar-icon" aria-hidden />
      <span>Sign in</span>
    </button>
  )
}

export default OperatorSignInAction
