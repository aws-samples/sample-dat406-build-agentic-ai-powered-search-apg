/**
 * Chat Service - Connects to FastAPI Backend
 * Handles product search and AI chat functionality
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  products?: ChatProduct[]
  suggestions?: string[]
}

export interface ChatProduct {
  id: string
  name: string
  price: number
  image: string
  category?: string
  rating?: number
  reviews?: number
}

export interface AgentExecution {
  agent_steps: Array<{agent: string, action: string, status: string, timestamp: number, duration_ms: number}>
  tool_calls: Array<{tool: string, params?: string, timestamp: number, duration_ms: number, status: string}>
  reasoning_steps: Array<{step: string, content: string, timestamp: number}>
  total_duration_ms: number
  success_rate: number
}

export interface ChatResponse {
  response: string
  products: ChatProduct[]
  suggestions?: string[]
  agent_execution?: AgentExecution
}

/**
 * Send a chat message with streaming support
 */
export async function sendChatMessageStreaming(
  query: string,
  conversationHistory: ChatMessage[] = [],
  onUpdate: (data: any) => void
): Promise<ChatResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: query,
        conversation_history: conversationHistory.map(msg => ({
          role: msg.role,
          content: msg.content
        }))
      }),
    })

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`)
    }

    const reader = response.body?.getReader()
    const decoder = new TextDecoder()
    let finalResponse: ChatResponse | null = null

    if (reader) {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              onUpdate(data)
              
              if (data.type === 'complete') {
                finalResponse = {
                  response: data.response.response,
                  products: data.response.products || [],
                  suggestions: data.response.suggestions || [],
                  agent_execution: data.response.agent_execution
                }
              }
            } catch (e) {
              console.error('Failed to parse SSE data:', e)
            }
          }
        }
      }
    }

    return finalResponse || {
      response: 'Response completed',
      products: [],
      suggestions: []
    }
  } catch (error) {
    console.error('Streaming chat error:', error)
    throw error
  }
}

/**
 * Send a chat message to the backend and get AI response with products
 */
export async function sendChatMessage(query: string, conversationHistory: ChatMessage[] = [], enableThinking: boolean = false): Promise<ChatResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/chat?enable_thinking=${enableThinking}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        message: query,
        conversation_history: conversationHistory.map(msg => ({
          role: msg.role,
          content: msg.content
        }))
      }),
    })

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`)
    }

    const data = await response.json()
    
    // Backend already returns formatted products
    const chatProducts: ChatProduct[] = (data.products || []).map((p: any) => ({
        id: p.id || p.productId || '',
        name: p.name || p.product_description || '',
        price: p.price || 0,
        image: p.image || p.imgurl || '📦',
        category: p.category || p.category_name,
        rating: p.stars || p.rating,
        reviews: p.reviews,
      }
    ))

    return {
      response: data.response || 'I found some products for you!',
      products: chatProducts,
      suggestions: data.suggestions || generateSmartSuggestions(query, chatProducts),
      agent_execution: data.agent_execution
    }
  } catch (error) {
    console.error('Chat API error:', error)
    throw error
  }
}

/**
 * Generate smart suggestions based on the search query and results
 */
function generateSmartSuggestions(query: string, products: ChatProduct[]): string[] {
  const lowerQuery = query.toLowerCase()
  
  // If we have products, offer relevant follow-ups
  if (products.length > 0) {
    return ['Show similar items', 'Different price range', 'Other brands']
  }
  
  // Default suggestions for different query types
  if (lowerQuery.includes('headphone') || lowerQuery.includes('audio') || lowerQuery.includes('earbud')) {
    return ['Show wireless options', 'What about noise cancelling?', 'Under $100']
  }
  
  if (lowerQuery.includes('laptop') || lowerQuery.includes('computer')) {
    return ['Show gaming laptops', 'Best for work', 'Under $1000']
  }
  
  if (lowerQuery.includes('phone')) {
    return ['Show latest models', 'Best camera phones', 'Budget smartphones']
  }
  
  // Default fallback
  return ['🎧 Wireless earbuds', '💻 Laptops', '📱 Smartphones', '🎮 Gaming gear']
}

/**
 * Health check for the backend
 */
export async function checkBackendHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/health`)
    return response.ok
  } catch {
    return false
  }
}