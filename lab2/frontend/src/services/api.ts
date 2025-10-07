/**
 * API client for DAT406 Workshop Backend
 */
import axios, { AxiosInstance } from 'axios'
import {
  SearchQuery,
  SearchResponse,
  Product,
  InventoryAnalysis,
  RecommendationRequest,
  RecommendationResponse,
  HealthCheck,
} from './types'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Add request interceptor for logging
    this.client.interceptors.request.use(
      (config) => {
        console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`)
        return config
      },
      (error) => {
        console.error('[API] Request error:', error)
        return Promise.reject(error)
      }
    )

    // Add response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response) {
          console.error('[API] Response error:', error.response.status, error.response.data)
        } else if (error.request) {
          console.error('[API] No response received:', error.request)
        } else {
          console.error('[API] Error:', error.message)
        }
        return Promise.reject(error)
      }
    )
  }

  // Health Check
  async healthCheck(): Promise<HealthCheck> {
    const response = await this.client.get<HealthCheck>('/health')
    return response.data
  }

  // Lab 1: Search
  async search(query: SearchQuery): Promise<SearchResponse> {
    const response = await this.client.post<SearchResponse>('/api/search', query)
    return response.data
  }

  async autocomplete(query: string): Promise<{suggestions: Array<{text: string, category: string}>}> {
    if (!query || query.trim().length < 2) {
      return { suggestions: [] }
    }
    const response = await this.client.get(`/api/autocomplete?q=${encodeURIComponent(query)}`)
    return response.data
  }

  async getProduct(productId: string): Promise<Product> {
    const response = await this.client.get<Product>(`/api/products/${productId}`)
    return response.data
  }

  async listProducts(params?: {
    limit?: number
    category?: string
    min_price?: number
    max_price?: number
  }): Promise<Product[]> {
    const response = await this.client.get<Product[]>('/api/products', { params })
    return response.data
  }

  // Lab 2: Inventory
  async analyzeInventory(lowStockThreshold?: number): Promise<InventoryAnalysis> {
    const response = await this.client.get<InventoryAnalysis>('/api/inventory/analyze', {
      params: { low_stock_threshold: lowStockThreshold },
    })
    return response.data
  }

  async getLowStockProducts(threshold?: number): Promise<Product[]> {
    const response = await this.client.get<Product[]>('/api/inventory/low-stock', {
      params: { threshold },
    })
    return response.data
  }

  async getOutOfStockProducts(): Promise<Product[]> {
    const response = await this.client.get<Product[]>('/api/inventory/out-of-stock')
    return response.data
  }

  // Lab 2: Recommendations
  async getRecommendations(request: RecommendationRequest): Promise<RecommendationResponse> {
    const response = await this.client.post<RecommendationResponse>(
      '/api/recommendations',
      request
    )
    return response.data
  }

  // Chat
  async chat(message: string, conversationHistory: Array<{role: string, content: string}> = []): Promise<{
    response: string
    tool_calls: any[]
    model: string
    success: boolean
  }> {
    const response = await this.client.post('/api/chat', {
      message,
      conversation_history: conversationHistory
    })
    return response.data
  }
}

// Export singleton instance
export const apiClient = new ApiClient()