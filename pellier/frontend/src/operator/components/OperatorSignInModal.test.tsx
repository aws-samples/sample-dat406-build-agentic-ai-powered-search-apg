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

  it('closes on Escape and returns focus to the opener', async () => {
    const user = userEvent.setup()
    renderModal()
    const opener = screen.getByTestId('operator-state-sign-in')

    await user.click(opener)
    expect(screen.getByTestId('operator-signin-modal')).toBeInTheDocument()
    await user.keyboard('{Escape}')

    expect(screen.queryByTestId('operator-signin-modal')).toBeNull()
    await waitFor(() => expect(opener).toHaveFocus())
  })

  it('keeps Tab and Shift+Tab inside the dialog', async () => {
    const user = userEvent.setup()
    renderModal()

    await user.click(screen.getByText('Open sign-in'))
    const close = screen.getByTestId('operator-signin-modal-close')
    const primary = screen.getByTestId('operator-signin-modal-continue')
    await waitFor(() => expect(primary).toHaveFocus())

    await user.keyboard('{Tab}')
    expect(close).toHaveFocus()

    await user.keyboard('{Shift>}{Tab}{/Shift}')
    expect(primary).toHaveFocus()
  })

  it('sets the sheet on the house plate, loaded through the asset helpers', async () => {
    // The owner asked for a background here, and the one rule that matters is
    // that it never becomes a CSS url(): a bare root-relative path 404s behind
    // the Workshop Studio /ports/8000/ proxy, and a sign-in screen with a
    // missing background is the first thing anyone sees of this desk.
    const user = userEvent.setup()
    const { container } = renderModal()
    await user.click(screen.getByText('Open sign-in'))

    const plate = container.querySelector('.operator-signin-plate')
    expect(plate).not.toBeNull()
    const img = plate?.querySelector('img')
    expect(img?.getAttribute('src')).toContain('/products/hero-fresh-2-960.webp')
    expect(
      plate?.querySelector('source[type="image/avif"]')?.getAttribute('srcSet'),
    ).toContain('/products/hero-fresh-2-1600.avif')

    // Decorative. The dialog's own words carry the moment.
    expect(img).toHaveAttribute('alt', '')
    expect(img).toHaveAttribute('aria-hidden', 'true')

    // Still exactly one heading: the eyebrow is a label, not a second title.
    expect(screen.getAllByRole('heading')).toHaveLength(1)
  })

  it('closes when the warm-paper dialog backdrop is clicked', async () => {
    const user = userEvent.setup()
    renderModal()

    await user.click(screen.getByText('Open sign-in'))
    await user.click(screen.getByTestId('operator-signin-modal-backdrop'))

    expect(screen.queryByTestId('operator-signin-modal')).toBeNull()
  })
})
