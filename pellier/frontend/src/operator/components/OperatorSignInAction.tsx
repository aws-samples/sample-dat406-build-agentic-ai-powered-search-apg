import React from 'react'
import { User } from 'lucide-react'
import { redirectToSignIn } from '../../utils/auth'

/** A consistent recovery action for a Cognito-protected operator surface. */
const OperatorSignInAction: React.FC = () => (
  <button
    type="button"
    className="pellier-account-pill operator-auth-signin operator-state-signin"
    onClick={() => redirectToSignIn('email')}
    data-testid="operator-state-sign-in"
  >
    <User className="operator-topbar-icon" aria-hidden />
    <span>Sign in</span>
  </button>
)

export default OperatorSignInAction
