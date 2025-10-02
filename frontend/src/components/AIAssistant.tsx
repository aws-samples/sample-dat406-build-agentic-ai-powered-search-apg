/**
 * Premium AI Assistant Component - Apple-inspired Design
 * Floating bubble with glassmorphic chat window
 * DARK MODE READY
 */
import { useState, useRef, useEffect } from 'react'
import { Send, Sparkles, X, Bot } from 'lucide-react'

interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

const AIAssistant = () => {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: '👋 Welcome to Aurora AI! I\'m your premium shopping assistant powered by Amazon Aurora PostgreSQL with pgvector and Amazon Bedrock. I can help you find products, compare options, and provide personalized recommendations using advanced semantic search.',
      timestamp: new Date()
    }
  ])
  const [inputValue, setInputValue] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = () => {
    if (!inputValue.trim()) return

    const userMessage: Message = {
      role: 'user',
      content: inputValue,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setIsTyping(true)

    // Simulate AI response with typing indicator
    setTimeout(() => {
      const responses = [
        'I\'ve analyzed your query using Aurora PostgreSQL with pgvector. Based on semantic similarity, I found 3 perfect matches for you with 95%+ confidence scores.',
        'Using our RAG pipeline powered by Amazon Bedrock, I can see that the Sony WH-1000XM5 matches your requirements with 97% confidence. Would you like to see alternatives?',
        'Our multi-agent system has coordinated inventory, pricing, and recommendation agents to find the best deal for you. The item is in stock with same-day delivery available.',
        'The MCP protocol integration allows me to access real-time inventory across all warehouses. I found 15 matching products sorted by relevance and customer ratings.'
      ]

      const assistantMessage: Message = {
        role: 'assistant',
        content: responses[Math.floor(Math.random() * responses.length)],
        timestamp: new Date()
      }

      setMessages(prev => [...prev, assistantMessage])
      setIsTyping(false)
    }, 1500)
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <>
      {/* Chat Window */}
      {isOpen && (
        <div 
          className="fixed bottom-32 right-8 w-[440px] h-[640px] z-[999]
                     rounded-[28px] overflow-hidden
                     bg-white/95 dark:bg-gray-900/95 backdrop-blur-2xl
                     shadow-2xl border border-white/20 dark:border-gray-700/50
                     animate-in slide-in-from-bottom-8 fade-in duration-500"
          style={{
            boxShadow: '0 24px 60px rgba(0, 0, 0, 0.15), 0 0 0 1px rgba(0, 0, 0, 0.05)'
          }}
        >
          {/* Header */}
          <div className="px-6 py-5 border-b border-gray-100/80 dark:border-gray-700/80
                         bg-gradient-to-r from-purple-50/80 via-white/80 to-blue-50/80
                         dark:from-purple-900/20 dark:via-gray-800/80 dark:to-blue-900/20">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="relative">
                  <div className="w-11 h-11 rounded-full flex items-center justify-center
                                bg-gradient-to-br from-purple-500 to-blue-500
                                shadow-lg">
                    <Bot className="h-5 w-5 text-white" strokeWidth={2} />
                  </div>
                  {/* Online indicator */}
                  <div className="absolute bottom-0 right-0 w-3 h-3 
                                rounded-full bg-emerald-500 border-2 border-white dark:border-gray-900
                                shadow-sm" />
                </div>
                <div>
                  <div className="font-semibold text-gray-900 dark:text-white">Aurora AI</div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 font-medium">
                    Powered by pgvector + Bedrock
                  </div>
                </div>
              </div>
              
              <button 
                onClick={() => setIsOpen(false)}
                className="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700
                         transition-all duration-300 group"
              >
                <X className="h-5 w-5 text-gray-500 dark:text-gray-400 
                             group-hover:text-gray-900 dark:group-hover:text-white" strokeWidth={2} />
              </button>
            </div>
          </div>

          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto px-6 py-6 space-y-4 custom-scrollbar"
               style={{ height: 'calc(100% - 180px)' }}>
            {messages.map((message, index) => (
              <div
                key={index}
                className={`flex ${message.role === 'assistant' ? 'justify-start' : 'justify-end'}`}
              >
                <div
                  className={`max-w-[85%] px-4 py-3 rounded-2xl text-sm leading-relaxed
                             animate-in slide-in-from-bottom-2 fade-in duration-300
                             ${message.role === 'assistant' 
                               ? 'bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-700 text-gray-900 dark:text-white rounded-tl-md' 
                               : 'bg-gradient-to-br from-purple-600 to-blue-600 text-white rounded-tr-md'
                             }`}
                  style={{
                    boxShadow: message.role === 'assistant' 
                      ? '0 2px 8px rgba(0, 0, 0, 0.04)' 
                      : '0 4px 12px rgba(139, 92, 246, 0.3)'
                  }}
                >
                  {message.content}
                </div>
              </div>
            ))}

            {/* Typing Indicator */}
            {isTyping && (
              <div className="flex justify-start">
                <div className="px-4 py-3 rounded-2xl rounded-tl-md
                              bg-gradient-to-br from-gray-50 to-gray-100
                              dark:from-gray-800 dark:to-gray-700
                              shadow-sm">
                  <div className="flex gap-1.5">
                    <div className="w-2 h-2 rounded-full bg-gray-400 dark:bg-gray-500 animate-bounce" 
                         style={{ animationDelay: '0ms' }} />
                    <div className="w-2 h-2 rounded-full bg-gray-400 dark:bg-gray-500 animate-bounce" 
                         style={{ animationDelay: '150ms' }} />
                    <div className="w-2 h-2 rounded-full bg-gray-400 dark:bg-gray-500 animate-bounce" 
                         style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="px-6 py-5 border-t border-gray-100/80 dark:border-gray-700/80
                         bg-white/90 dark:bg-gray-800/90 backdrop-blur-xl">
            <div className="flex gap-3">
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask me anything..."
                className="flex-1 px-4 py-3 rounded-2xl text-sm
                         bg-gray-50 dark:bg-gray-700 
                         border border-gray-200 dark:border-gray-600
                         text-gray-900 dark:text-white
                         placeholder:text-gray-400 dark:placeholder:text-gray-500
                         focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-transparent
                         transition-all duration-300"
              />
              <button
                onClick={handleSend}
                disabled={!inputValue.trim()}
                className="px-5 py-3 rounded-2xl font-semibold text-sm
                         bg-gradient-to-br from-purple-600 to-blue-600
                         hover:from-purple-700 hover:to-blue-700
                         text-white shadow-lg hover:shadow-xl
                         disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-lg
                         transform transition-all duration-300 hover:scale-105
                         flex items-center gap-2"
              >
                <Send className="h-4 w-4" strokeWidth={2} />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Floating Bubble */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="floating-bubble w-[72px] h-[72px] rounded-full z-[1000]
                   bg-gradient-to-br from-blue-600 via-purple-600 to-teal-600
                   hover:from-blue-700 hover:via-purple-700 hover:to-teal-700
                   shadow-2xl hover:shadow-3xl
                   transform transition-all duration-500
                   hover:scale-110 active:scale-95
                   group relative"
        style={{
          boxShadow: '0 12px 40px rgba(59, 130, 246, 0.4), 0 0 0 1px rgba(255, 255, 255, 0.1)'
        }}
      >
        {/* Animated Ring */}
        <div className="absolute inset-0 rounded-full 
                       bg-gradient-to-br from-blue-400 via-purple-400 to-teal-400
                       animate-ping opacity-20" />
        
        {/* Aurora Database Icon */}
        <div className="relative w-full h-full flex items-center justify-center">
          <svg className="h-8 w-8 text-white" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.94-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
          </svg>
        </div>

        {/* Aurora AI Badge */}
        <div 
          className="absolute -top-3 -right-4 px-2 py-1 rounded-full text-xs font-bold
                     bg-gradient-to-r from-blue-500 via-purple-500 to-teal-500
                     text-white shadow-lg
                     transform group-hover:scale-110 transition-transform duration-300"
          style={{
            boxShadow: '0 4px 12px rgba(59, 130, 246, 0.4)'
          }}
        >
          Aurora AI
        </div>

        {/* Notification Dot */}
        <div className="absolute top-1 right-1 w-3 h-3 rounded-full 
                       bg-emerald-400 border-2 border-white dark:border-gray-900
                       shadow-sm animate-pulse" />
      </button>

      <style>{`
        @keyframes float {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-10px); }
        }

        .custom-scrollbar::-webkit-scrollbar {
          width: 6px;
        }

        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }

        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: linear-gradient(180deg, #a855f7 0%, #3b82f6 100%);
          border-radius: 3px;
        }

        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: linear-gradient(180deg, #9333ea 0%, #2563eb 100%);
        }
      `}</style>
    </>
  )
}

export default AIAssistant