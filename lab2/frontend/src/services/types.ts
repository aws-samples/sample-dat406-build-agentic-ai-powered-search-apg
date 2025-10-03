/**
 * Type definitions for DAT406 Workshop Frontend
 */

// Product Types
export interface Product {
  productId: string
  product_description: string
  imgurl?: string
  producturl?: string
  stars?: number
  reviews?: number
  price?: number
  category_id?: number
  isbestseller?: boolean
  boughtinlastmonth?: number
  category_name?: string
  quantity?: number
}

export interface ProductSearchResult extends Product {
  similarity_score: number
}

// Search Types
export interface SearchFilters {
  category?: string
  min_price?: number
  max_price?: number
  min_rating?: number
  in_stock?: boolean
}

export interface SearchQuery {
  query: string
  limit?: number
  filters?: SearchFilters
}

export interface SearchResponse {
  query: string
  total_results: number
  results: ProductSearchResult[]
  search_method: string
  execution_time_ms?: number
}

// Inventory Types
export interface InventoryAnalysis {
  total_products: number
  low_stock_count: number
  out_of_stock_count: number
  average_quantity: number
  low_stock_products: Product[]
  out_of_stock_products: Product[]
}

// Recommendation Types
export interface RecommendationRequest {
  product_id: string
  limit?: number
}

export interface RecommendationResponse {
  source_product: Product
  recommendations: ProductSearchResult[]
}

// Health Check Types
export interface HealthCheck {
  status: string
  database: boolean
  embeddings: boolean
  bedrock: boolean
  timestamp: string
}

// API Error Type
export interface ApiError {
  error: string
  status_code: number
}