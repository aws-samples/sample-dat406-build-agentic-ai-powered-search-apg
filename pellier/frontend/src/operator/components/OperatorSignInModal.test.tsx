/**
 * OperatorSignInModal tests.
 *
 * The Operator desk deliberately uses Cognito's native email/password path:
 * it is an authorized-staff entry point, not the storefront's provider
 * chooser. These tests protect that boundary as well as the dialog behavior.
 */
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { OPERATOR_SIGNIN_MODAL } from '../../copy'
import { UIProvider, useUI } from '../../contexts/UIContext'
import { redirectToSignIn } from '../../utils/auth'
import OperatorSignInAction from './OperatorSignInAction'
import OperatorSignInModal from './OperatorSignInModal'

vi.mock('../../utils/auth', () => ({
  redirectToSignIn: vi.fn(),
}))

const mockedRedirectToSignIn = vi.mocked(redirectToSignIn)

function Probe() {
  const { activeModal, openModal } = useUI()
  return (
    <>
      <span data-testid="active-modal">{activeModal ?? 'none'}</span>
      <button type="button" onClick={() => openModal('operator-auth')}>
        Open sign-in
      </button>
    </>
  )
}

function renderModal() {
  return render(
    <UIProvider>
      <Probe />
      <OperatorSignInAction />
      <OperatorSignInModal />
    </UIProvider>,
  )
}

beforeEach(() => {
  window.history.pushState({}, '', '/operator/reviews/3?from=queue')
})

afterEach(() => {
  vi.clearAllMocks()
})

describe('OperatorSignInModal', () => {
  it('stays absent until an Operator sign-in action opens it', async () => {
    const user = userEvent.setup()
    renderModal()

    expect(screen.queryByTestId('operator-signin-modal')).toBeNull()

    await user.click(screen.getByTestId('operator-state-sign-in'))

    expect(screen.getByTestId('active-modal')).toHaveTextContent('operator-auth')
    expect(screen.getByTestId('operator-signin-modal')).toBeInTheDocument()
    expect(screen.getByText(OPERATOR_SIGNIN_MODAL.EYEBROW)).toBeInTheDocument()
    expect(screen.getByRole('heading')).toHaveTextContent(
      OPERATOR_SIGNIN_MODAL.TITLE,
    )
    expect(screen.getByText(OPERATOR_SIGNIN_MODAL.BODY)).toBeInTheDocument()
    expect(
      screen.getByTestId('operator-signin-modal-continue'),
    ).toHaveTextContent(OPERATOR_SIGNIN_MODAL.ACTION)

    expect(screen.queryByText(/Continue with Google/i)).toBeNull()
    expect(screen.queryByText(/Continue with Apple/i)).toBeNull()
  })

  it('uses the email sign-in path and returns the Operator to the current desk route', async () => {
    const user = userEvent.setup()
    renderModal()

    await user.click(screen.getByText('Open sign-in'))
    await user.click(screen.getByTestId('operator-signin-modal-continue'))

    expect(mockedRedirectToSignIn).toHaveBeenCalledOnce()
    expect(mockedRedirectToSignIn).toHaveBeenCalledWith('email', {
      returnTo: '/operator/reviews/3?from=queue',
    })
  })

  it('closes from the close control and returns focus to the opener', async () => {
    const user = userEvent.setup()
    renderModal()
    const opener = screen.getByTestId('operator-state-sign-in')

    await user.click(opener)
    await user.click(screen.getByTestId('operator-signin-modal-close'))

    expect(screen.queryByTestId('operator-signin-modal')).toBeNull()
    expect(screen.getByTestId('active-modal')).toHaveTextContent('none')
    await waitFor(() => expect(opener).toHaveFocus())
  })

  it('closes when the warm-paper dialog backdrop is clicked', async () => {
    const user = userEvent.setup()
    renderModal()

    await user.click(screen.getByText('Open sign-in'))
    await user.click(screen.getByTestId('operator-signin-modal-backdrop'))

    expect(screen.queryByTestId('operator-signin-modal')).toBeNull()
  })
})
