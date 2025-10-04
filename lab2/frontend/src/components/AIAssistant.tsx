/**
 * Connects to FastAPI backend for actual product search
 */
import { useState, useRef, useEffect } from 'react'
import { Send, ShoppingCart, X, AlertCircle } from 'lucide-react'
import ProductCard from './ProductCard'
import CartModal from './CartModal'
import CheckoutModal from './CheckoutModal'
import { sendChatMessage, ChatProduct, checkBackendHealth } from '../services/chat'

interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  products?: ChatProduct[]
  suggestions?: string[]
}

const AIAssistant = () => {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: '✨ I\'m Aurora AI. I can help you find products, compare options, and get recommendations. What are you looking for?',
      timestamp: new Date(),
      suggestions: ['🎧 Premium headphones', '💻 Laptops', '📱 Smartphones']
    }
  ])
  const [inputValue, setInputValue] = useState('')
  const [cart, setCart] = useState<ChatProduct[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [backendOnline, setBackendOnline] = useState(true)
  const [showCart, setShowCart] = useState(false)
  const [showCheckout, setShowCheckout] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Check backend health on mount
  useEffect(() => {
    checkBackendHealth().then(setBackendOnline)
  }, [])

  const addToCart = (product: ChatProduct) => {
    setCart(prev => [...prev, product])
    
    // Add confirmation message
    const confirmMessage: Message = {
      role: 'assistant',
      content: `✅ Added to cart! You now have ${cart.length + 1} item(s). Ready to checkout?`,
      timestamp: new Date()
    }
    setMessages(prev => [...prev, confirmMessage])
  }

  const updateQuantity = (productId: string, delta: number) => {
    if (delta > 0) {
      const product = cart.find(p => p.id === productId)
      if (product) setCart(prev => [...prev, product])
    } else {
      const index = cart.findIndex(p => p.id === productId)
      if (index !== -1) setCart(prev => prev.filter((_, i) => i !== index))
    }
  }

  const removeFromCart = (productId: string) => {
    setCart(prev => prev.filter(p => p.id !== productId))
  }

  const handleCheckoutComplete = () => {
    setCart([])
    const successMessage: Message = {
      role: 'assistant',
      content: '🎉 Order placed successfully! Your items will arrive in 2-3 business days. Can I help you find anything else?',
      timestamp: new Date(),
      suggestions: ['Track my order', 'Browse more products', 'Contact support']
    }
    setMessages(prev => [...prev, successMessage])
  }

  const handleSend = async (customMessage?: string) => {
    const messageText = customMessage || inputValue
    if (!messageText.trim() || isLoading) return

    // Add user message
    const userMessage: Message = {
      role: 'user',
      content: messageText,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setIsLoading(true)

    // Add loading message
    const loadingMessage: Message = {
      role: 'assistant',
      content: '✨ Finding the perfect products for you...',
      timestamp: new Date()
    }
    setMessages(prev => [...prev, loadingMessage])

    try {
      // Call real backend API with conversation history
      const response = await sendChatMessage(messageText, messages.slice(0, -1))

      // Remove loading message
      setMessages(prev => prev.slice(0, -1))

      // Add AI response (products already formatted by chat service)
      const aiMessage: Message = {
        role: 'assistant',
        content: response.response,
        timestamp: new Date(),
        products: response.products,
        suggestions: response.suggestions,
      }

      setMessages(prev => [...prev, aiMessage])
      setBackendOnline(true)

    } catch (error) {
      console.error('Chat error:', error)
      
      // Remove loading message
      setMessages(prev => prev.slice(0, -1))
      
      // Add error message
      const errorMessage: Message = {
        role: 'assistant',
        content: '❌ Unable to connect. Please check that the backend service is running.',
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
      setBackendOnline(false)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSuggestionClick = (suggestion: string) => {
    handleSend(suggestion)
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey && !isLoading) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <>
      {/* Chat Window */}
      {isOpen && (
        <div className="fixed bottom-32 right-8 w-[420px] max-w-[calc(100vw-4rem)] h-[680px] max-h-[calc(100vh-10rem)] glass-strong rounded-[20px] flex flex-col z-[999] animate-slideUp shadow-2xl">
          {/* Header */}
          <div className="px-6 py-6 rounded-t-[20px] border-b border-accent-light/20 flex justify-between items-center"
               style={{
                 background: 'linear-gradient(135deg, rgba(106, 27, 154, 0.1) 0%, rgba(186, 104, 200, 0.1) 100%)'
               }}>
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-full flex items-center justify-center overflow-hidden">
                <img src="/chat-icon.jpeg" alt="Aurora AI" className="w-full h-full object-cover" />
              </div>
              <div>
                <div className="font-medium text-lg text-text-primary">Aurora AI</div>
                <div className="text-xs text-text-secondary flex items-center gap-1">
                  {isLoading ? (
                    <>🔄 Searching...</>
                  ) : !backendOnline ? (
                    <>
                      <AlertCircle className="h-3 w-3" />
                      Backend Offline
                    </>
                  ) : (
                    <><span className="text-green-500">🟢</span> Online</>
                  )}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {cart.length > 0 && (
                <div className="relative cursor-pointer" onClick={() => setShowCart(true)}>
                  <ShoppingCart className="h-5 w-5 text-accent-light hover:scale-110 transition-transform" />
                  <span className="absolute -top-2 -right-2 bg-accent-light text-white text-xs rounded-full w-5 h-5 flex items-center justify-center font-bold">
                    {cart.length}
                  </span>
                </div>
              )}
              <button 
                onClick={() => setIsOpen(false)}
                className="text-text-primary hover:text-accent-light transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-6 py-6 flex flex-col gap-4 custom-scrollbar">
            {messages.map((message, index) => (
              <div key={index} className="flex flex-col gap-3">
                {/* Message Bubble */}
                <div
                  className={`max-w-[85%] px-[18px] py-[14px] rounded-2xl text-base leading-relaxed animate-slideUp ${
                    message.role === 'assistant'
                      ? 'self-start text-text-primary'
                      : 'self-end'
                  }`}
                  style={{
                    background: message.role === 'assistant'
                      ? 'linear-gradient(135deg, rgba(106, 27, 154, 0.1) 0%, rgba(186, 104, 200, 0.05) 100%)'
                      : 'linear-gradient(135deg, #6a1b9a 0%, #ba68c8 100%)',
                    border: message.role === 'assistant' ? '1px solid rgba(186, 104, 200, 0.2)' : 'none',
                    color: message.role === 'user' ? 'white' : undefined,
                    whiteSpace: 'pre-wrap'
                  }}
                >
                  {message.content}
                </div>

                {/* Product Cards */}
                {message.products && message.products.length > 0 && (
                  <div className="flex flex-col gap-2 ml-0">
                    {message.products.map((product, idx) => (
                      <ProductCard
                        key={product.id}
                        product={product}
                        onAddToCart={addToCart}
                        highlighted={idx === 0} // Highlight first product
                      />
                    ))}
                  </div>
                )}

                {/* Suggestions */}
                {message.suggestions && message.suggestions.length > 0 && (
                  <div className="flex flex-wrap gap-2 ml-0">
                    {message.suggestions.map((suggestion, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleSuggestionClick(suggestion)}
                        disabled={isLoading}
                        className="px-4 py-2 rounded-full text-sm font-medium transition-all duration-300 hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed"
                        style={{
                          background: 'rgba(106, 27, 154, 0.2)',
                          border: '1px solid rgba(186, 104, 200, 0.3)',
                          color: '#ba68c8'
                        }}
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                )}

                {/* Cart Actions */}
                {message.products && cart.length > 0 && (
                  <div className="flex gap-2 ml-0 mt-2">
                    <button
                      onClick={() => setShowCart(true)}
                      className="flex-1 px-4 py-3 rounded-xl font-semibold text-sm transition-all duration-300 hover:scale-105"
                      style={{
                        background: 'rgba(106, 27, 154, 0.2)',
                        border: '1px solid rgba(186, 104, 200, 0.3)',
                        color: '#ba68c8'
                      }}
                    >
                      View cart ({cart.length})
                    </button>
                    <button
                      onClick={() => setShowCheckout(true)}
                      className="flex-1 px-4 py-3 rounded-xl font-semibold text-sm transition-all duration-300 hover:scale-105"
                      style={{
                        background: 'linear-gradient(135deg, #6a1b9a 0%, #ba68c8 100%)',
                        color: 'white'
                      }}
                    >
                      Checkout now
                    </button>
                  </div>
                )}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="px-6 py-6 border-t border-accent-light/20 flex gap-3">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={isLoading ? 'Searching...' : 'Ask for products...'}
              disabled={isLoading}
              className="flex-1 px-[14px] py-[14px] input-field rounded-xl text-sm disabled:opacity-50"
            />
            <button
              onClick={() => handleSend()}
              disabled={!inputValue.trim() || isLoading}
              className="px-6 py-[14px] rounded-xl font-semibold transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              style={{
                background: 'linear-gradient(135deg, #6a1b9a 0%, #ba68c8 100%)'
              }}
            >
              {isLoading ? <span className="animate-spin">⏳</span> : <Send className="h-4 w-4 text-white" />}
            </button>
          </div>
        </div>
      )}

      {/* Floating Bubble */}
      <div className="fixed bottom-8 right-8 z-[1000]">
        {/* Tooltip Bubble */}
        {!isOpen && (
          <div className="absolute bottom-20 right-0 animate-slideIn">
            <div 
              className="px-4 py-2 rounded-2xl text-base font-medium text-white whitespace-nowrap relative"
              style={{
                background: 'rgba(10, 10, 15, 0.95)',
                boxShadow: '0 4px 16px rgba(0, 0, 0, 0.3)',
                border: '1px solid rgba(186, 104, 200, 0.2)'
              }}
            >
              How may I assist?
              {/* Chat bubble tail */}
              <div 
                className="absolute -bottom-2 right-6 w-4 h-4 rotate-45"
                style={{
                  background: 'rgba(10, 10, 15, 0.95)',
                  borderRight: '1px solid rgba(186, 104, 200, 0.2)',
                  borderBottom: '1px solid rgba(186, 104, 200, 0.2)'
                }}
              />
            </div>
          </div>
        )}
        
        {/* Chat Icon */}
        <div
          onClick={() => setIsOpen(!isOpen)}
          className="w-[80px] h-[80px] rounded-full flex items-center justify-center cursor-pointer transition-all duration-300 hover:scale-110 animate-float relative overflow-hidden"
          style={{
            boxShadow: '0 8px 32px rgba(106, 27, 154, 0.5)'
          }}
        >
          <img src="/chat-icon.jpeg" alt="Chat" className="w-full h-full object-cover" />

          {cart.length > 0 && (
            <div className="absolute -top-2 -left-2 bg-green-500 text-white text-xs rounded-full w-6 h-6 flex items-center justify-center font-bold animate-pulse">
              {cart.length}
            </div>
          )}
        </div>
      </div>

      {/* Cart Modal */}
      <CartModal
        isOpen={showCart}
        onClose={() => setShowCart(false)}
        cart={cart}
        onUpdateQuantity={updateQuantity}
        onRemove={removeFromCart}
        onCheckout={() => {
          setShowCart(false)
          setShowCheckout(true)
        }}
      />

      {/* Checkout Modal */}
      <CheckoutModal
        isOpen={showCheckout}
        onClose={() => setShowCheckout(false)}
        cart={cart}
        onComplete={handleCheckoutComplete}
      />
    </>
  )
}

export default AIAssistant