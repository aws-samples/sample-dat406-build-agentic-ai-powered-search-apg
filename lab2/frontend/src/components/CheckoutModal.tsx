/**
 * Checkout Modal - Mockup payment flow with AI agent
 */
import { useState } from 'react'
import { X, CreditCard, CheckCircle } from 'lucide-react'
import { ChatProduct } from '../services/chat'

interface CheckoutModalProps {
  isOpen: boolean
  onClose: () => void
  cart: ChatProduct[]
  onComplete: () => void
}

const CheckoutModal = ({ isOpen, onClose, cart, onComplete }: CheckoutModalProps) => {
  const [step, setStep] = useState<'payment' | 'processing' | 'success'>('payment')
  const [cardNumber, setCardNumber] = useState('')

  if (!isOpen) return null

  const total = cart.reduce((sum, item) => sum + item.price, 0)

  const handlePayment = () => {
    setStep('processing')
    setTimeout(() => {
      setStep('success')
      setTimeout(() => {
        onComplete()
        onClose()
        setStep('payment')
        setCardNumber('')
      }, 2000)
    }, 1500)
  }

  return (
    <div className="fixed inset-0 z-[1001] flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="w-[450px] glass-strong rounded-[20px] flex flex-col shadow-2xl">
        {/* Header */}
        <div className="px-6 py-4 border-b border-accent-light/20 flex justify-between items-center">
          <h2 className="text-xl font-semibold text-text-primary">
            {step === 'payment' && 'Checkout'}
            {step === 'processing' && 'Processing...'}
            {step === 'success' && 'Order Complete!'}
          </h2>
          {step === 'payment' && (
            <button onClick={onClose} className="hover:text-accent-light transition-colors">
              <X className="h-5 w-5" />
            </button>
          )}
        </div>

        {/* Content */}
        <div className="px-6 py-6">
          {step === 'payment' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">Card Number</label>
                <input
                  type="text"
                  value={cardNumber}
                  onChange={(e) => setCardNumber(e.target.value.replace(/\D/g, '').slice(0, 16))}
                  placeholder="4242 4242 4242 4242"
                  className="w-full px-4 py-3 rounded-lg input-field"
                />
              </div>
              <div className="flex gap-4">
                <div className="flex-1">
                  <label className="block text-sm font-medium text-text-primary mb-2">Expiry</label>
                  <input type="text" placeholder="MM/YY" className="w-full px-4 py-3 rounded-lg input-field" />
                </div>
                <div className="flex-1">
                  <label className="block text-sm font-medium text-text-primary mb-2">CVV</label>
                  <input type="text" placeholder="123" maxLength={3} className="w-full px-4 py-3 rounded-lg input-field" />
                </div>
              </div>
              <div className="pt-4 border-t border-accent-light/20">
                <div className="flex justify-between items-center mb-4">
                  <span className="text-text-secondary">Total Amount:</span>
                  <span className="text-2xl font-bold text-accent-light">${total.toFixed(2)}</span>
                </div>
                <button
                  onClick={handlePayment}
                  disabled={cardNumber.length < 16}
                  className="w-full py-3 rounded-xl font-semibold transition-all duration-300 hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                  style={{ background: 'linear-gradient(135deg, #6a1b9a 0%, #ba68c8 100%)', color: 'white' }}
                >
                  <CreditCard className="h-5 w-5" />
                  Pay ${total.toFixed(2)}
                </button>
              </div>
            </div>
          )}

          {step === 'processing' && (
            <div className="text-center py-12">
              <div className="animate-spin text-6xl mb-4">⏳</div>
              <p className="text-text-primary font-medium">Processing your payment...</p>
              <p className="text-text-secondary text-sm mt-2">AI Agent validating inventory & payment</p>
            </div>
          )}

          {step === 'success' && (
            <div className="text-center py-12">
              <CheckCircle className="h-16 w-16 text-green-500 mx-auto mb-4" />
              <p className="text-text-primary font-semibold text-lg">Payment Successful!</p>
              <p className="text-text-secondary text-sm mt-2">Your order has been placed</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default CheckoutModal
