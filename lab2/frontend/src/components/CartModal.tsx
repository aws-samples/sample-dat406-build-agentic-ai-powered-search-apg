/**
 * Cart Modal - View and manage cart items
 */
import { X, Trash2, Plus, Minus } from 'lucide-react'
import { ChatProduct } from '../services/chat'

interface CartModalProps {
  isOpen: boolean
  onClose: () => void
  cart: ChatProduct[]
  onUpdateQuantity: (productId: string, delta: number) => void
  onRemove: (productId: string) => void
  onCheckout: () => void
}

const CartModal = ({ isOpen, onClose, cart, onUpdateQuantity, onRemove, onCheckout }: CartModalProps) => {
  if (!isOpen) return null

  const quantities = cart.reduce((acc, item) => {
    acc[item.id] = (acc[item.id] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  const uniqueItems = Array.from(new Set(cart.map(item => item.id)))
    .map(id => cart.find(item => item.id === id)!)

  const total = cart.reduce((sum, item) => sum + item.price, 0)

  return (
    <div className="fixed inset-0 z-[1000] flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="w-[500px] max-h-[80vh] glass-strong rounded-[20px] flex flex-col shadow-2xl">
        {/* Header */}
        <div className="px-6 py-4 border-b border-accent-light/20 flex justify-between items-center">
          <h2 className="text-xl font-semibold text-text-primary">Your Cart ({cart.length})</h2>
          <button onClick={onClose} className="hover:text-accent-light transition-colors">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Cart Items */}
        <div className="flex-1 overflow-y-auto px-6 py-4 custom-scrollbar">
          {uniqueItems.length === 0 ? (
            <div className="text-center py-12 text-text-secondary">
              Your cart is empty
            </div>
          ) : (
            <div className="space-y-3">
              {uniqueItems.map(item => (
                <div key={item.id} className="flex items-center gap-3 p-3 rounded-xl" style={{ background: 'rgba(30, 30, 40, 0.4)' }}>
                  <img src={item.image} alt={item.name} className="w-16 h-16 object-cover rounded-lg" />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-text-primary line-clamp-1">{item.name}</div>
                    <div className="text-accent-light font-bold">${item.price}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button onClick={() => onUpdateQuantity(item.id, -1)} className="p-1 hover:bg-accent-light/20 rounded">
                      <Minus className="h-4 w-4" />
                    </button>
                    <span className="w-8 text-center font-semibold">{quantities[item.id]}</span>
                    <button onClick={() => onUpdateQuantity(item.id, 1)} className="p-1 hover:bg-accent-light/20 rounded">
                      <Plus className="h-4 w-4" />
                    </button>
                  </div>
                  <button onClick={() => onRemove(item.id)} className="p-2 hover:text-red-500 transition-colors">
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        {cart.length > 0 && (
          <div className="px-6 py-4 border-t border-accent-light/20">
            <div className="flex justify-between items-center mb-4">
              <span className="text-lg font-semibold text-text-primary">Total:</span>
              <span className="text-2xl font-bold text-accent-light">${total.toFixed(2)}</span>
            </div>
            <button
              onClick={onCheckout}
              className="w-full py-3 rounded-xl font-semibold transition-all duration-300 hover:scale-105"
              style={{ background: 'linear-gradient(135deg, #6a1b9a 0%, #ba68c8 100%)', color: 'white' }}
            >
              Proceed to Checkout
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default CartModal
