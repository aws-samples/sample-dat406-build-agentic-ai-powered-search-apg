/**
 * Chat Service - Connects to FastAPI Backend
 * Handles product search and AI chat functionality
 */

const API_BASE_URL =
  import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || ''

const SESSION_ID_KEY = 'pellier-session-id'
const SESSION_TOKEN_KEY = 'pellier-session-token'
const SESSION_TOKEN_SESSION_KEY = 'pellier-session-token-session'

function randomHex(bytes: number): string {
  const values = new Uint8Array(bytes)
  globalThis.crypto.getRandomValues(values)
  return Array.from(values, value => value.toString(16).padStart(2, '0')).join('')
}

/**
 * Get or create session ID for conversation persistence
 */
function getSessionId(): string {
  let sessionId = localStorage.getItem(SESSION_ID_KEY)
  if (!sessionId) {
    const id = globalThis.crypto.randomUUID?.() ?? randomHex(16)
    sessionId = `session-${id}`
    localStorage.setItem(SESSION_ID_KEY, sessionId)
  }
  return sessionId
}

function getSessionToken(sessionId: string): string {
  const tokenSession = localStorage.getItem(SESSION_TOKEN_SESSION_KEY)
  let token = localStorage.getItem(SESSION_TOKEN_KEY)
  if (!token || tokenSession !== sessionId) {
    token = randomHex(32)
    localStorage.setItem(SESSION_TOKEN_KEY, token)
    localStorage.setItem(SESSION_TOKEN_SESSION_KEY, sessionId)
  }
  return token
}

export function getSessionOwnershipHeaders(
  sessionId: string = getSessionId(),
): Record<string, string> {
  return { 'X-Pellier-Session-Token': getSessionToken(sessionId) }
}

function getAuthHeaders(sessionId: string): Record<string, string> {
  return {
    'Content-Type': 'application/json',
    ...getSessionOwnershipHeaders(sessionId),
  }
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  products?: ChatProduct[]
  suggestions?: string[]
}

export interface ChatProduct {
  id: number
  name: string
  price: number
  image: string
  category?: string
  rating?: number
  reviews?: number
  url?: string
  similarityScore?: number
  quantity?: number
  inStock?: boolean
  originalPrice?: number
  discountPercent?: number
}

export interface AgentExecution {
  agent_steps: Array<{agent: string, action: string, status: string, timestamp: number, duration_ms: number}>
  tool_calls: Array<{tool: string, params?: string, timestamp: number, duration_ms: number, status: string}>
  reasoning_steps: Array<{step: string, content: string, timestamp: number}>
  total_duration_ms: number
  success_rate: number
  /** False when Strands' TracerProvider isn't SDK-backed. UI renders a
   * banner and disables the waterfall instead of synthesizing spans. */
  otel_enabled?: boolean
  /** Actionable failure string from the backend when otel_enabled is
   * false. Rendered verbatim. */
  reason?: string
}

export interface ChatResponse {
  response: string
  products: ChatProduct[]
  suggestions?: string[]
  agent_execution?: AgentExecution
  orchestrator_enabled?: boolean
  token_count?: number
  estimated_cost_usd?: number
}

export type ResponseMode = 'balanced' | 'editorial' | 'fast'

/**
 * Send a chat message with streaming support
 */
export async function sendChatMessageStreaming(
  query: string,
  conversationHistory: ChatMessage[] = [],
  onUpdate: (data: any) => void,
  workshopMode?: string,
  guardrailsEnabled?: boolean,
  customerId?: string | null,
  pattern?: 'dispatcher' | 'agents_as_tools' | 'graph' | null,
  responseMode: ResponseMode = 'balanced',
): Promise<ChatResponse> {
  try {
    const sessionId = getSessionId()
    const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
      method: 'POST',
      credentials: 'include',
      headers: getAuthHeaders(sessionId),
      body: JSON.stringify({
        message: query,
        conversation_history: conversationHistory.map(msg => ({
          role: msg.role,
          content: msg.content
        })),
        session_id: sessionId,
        workshop_mode: workshopMode || null,
        guardrails_enabled: guardrailsEnabled || false,
        customer_id: customerId ?? null,
        pattern: pattern ?? null,
        response_mode: responseMode,
      }),
    })

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`)
    }

    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('The response did not include a stream.')
    }

    const decoder = new TextDecoder()
    let finalResponse: ChatResponse | null = null
    let lastContent = ''
    let streamError: Error | null = null

    const processLine = (line: string) => {
      if (!line.startsWith('data:')) return

      let data: Record<string, any>
      try {
        data = JSON.parse(line.slice(5).trimStart())
      } catch {
        return
      }

      onUpdate(data)
      if (data.type === 'error') {
        streamError = new Error(
          data.error || data.message || 'The live agent response failed.',
        )
        return
      }
      if (data.type === 'content') {
        lastContent = data.content
      } else if (data.type === 'content_delta') {
        lastContent += data.delta
      } else if (data.type === 'complete') {
        finalResponse = {
          response: data.response?.response,
          products: data.response?.products || [],
          suggestions: data.response?.suggestions || [],
          agent_execution: data.response?.agent_execution,
          orchestrator_enabled: data.response?.orchestrator_enabled,
          token_count: data.response?.token_count,
          estimated_cost_usd: data.response?.estimated_cost_usd
        }
      }
    }

    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      lines.forEach(processLine)
      if (streamError) {
        await reader.cancel()
        throw streamError
      }
    }

    buffer += decoder.decode()
    if (buffer.trim()) processLine(buffer)
    if (streamError) throw streamError
    if (!finalResponse) {
      throw new Error(
        lastContent
          ? 'The response stream ended before the agent completed.'
          : 'The response stream ended without a result.',
      )
    }

    return finalResponse
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
    const sessionId = getSessionId()
    const response = await fetch(`${API_BASE_URL}/api/chat?enable_thinking=${enableThinking}`, {
      method: 'POST',
      credentials: 'include',
      headers: getAuthHeaders(sessionId),
      body: JSON.stringify({ 
        message: query,
        conversation_history: conversationHistory.map(msg => ({
          role: msg.role,
          content: msg.content
        })),
        session_id: sessionId
      }),
    })

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`)
    }

    const data = await response.json()
    
    // Backend already returns formatted products
    const chatProducts: ChatProduct[] = (data.products || []).map((p: any) => ({
        id: p.id ?? p.productId ?? 0,
        name: p.name || p.product_description || '',
        price: p.price || 0,
        image: p.image || p.imgUrl || p.imgurl || '',
        category: p.category || p.category_name,
        rating: p.stars || p.rating,
        reviews: p.reviews,
        url: p.url || p.producturl,
        similarityScore:
          p.similarityScore ??
          p.similarity_score ??
          p.similarity ??
          p.relevance_score ??
          undefined,
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
  
  // Use actual product data to generate relevant suggestions
  if (products.length > 0) {
    const avgPrice = products.reduce((sum, p) => sum + p.price, 0) / products.length
    const categories = [...new Set(products.map(p => p.category).filter(Boolean))]
    const suggestions: string[] = []

    // Price-based follow-up
    if (avgPrice > 100) {
      suggestions.push(`Budget options under $${Math.round(avgPrice / 2)}`)
    } else {
      suggestions.push(`Premium options up to $${Math.round(avgPrice * 3)}`)
    }

    // Category-based follow-up
    if (categories.length > 0) {
      suggestions.push(`More in ${categories[0]}`)
    }

    // Action-based follow-up
    if (products.length >= 2) {
      suggestions.push('Compare the top picks')
    } else {
      suggestions.push("What's trending right now?")
    }

    return suggestions.slice(0, 3)
  }
  
  // Query-type based fallbacks (no products returned)
  if (lowerQuery.includes('watch') || lowerQuery.includes('rolex') || lowerQuery.includes('time')) {
    return ['Luxury watches under $500', 'Best everyday watches', 'Show all watches']
  }
  
  if (lowerQuery.includes('shirt') || lowerQuery.includes('linen') || lowerQuery.includes('apparel')) {
    return ['Linen for warm weather', 'Travel-ready layers', 'Show all apparel']
  }
  
  if (lowerQuery.includes('home') || lowerQuery.includes('ceramic') || lowerQuery.includes('decor')) {
    return ['Gifts for a new home', 'Handmade ceramics', 'Show all home decor']
  }

  if (lowerQuery.includes('shoe') || lowerQuery.includes('footwear') || lowerQuery.includes('espadrille')) {
    return ['Travel footwear under $150', 'Best rated footwear', 'Show all footwear']
  }
  
  return ["What's trending?", 'Best rated under $50', 'Show me something surprising']
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
