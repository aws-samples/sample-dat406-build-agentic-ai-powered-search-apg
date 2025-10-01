/**
 * Custom hook for product search functionality
 */
import { useState } from 'react'
import { apiClient } from '../services/api'
import { ProductSearchResult, SearchFilters } from '../services/types'

export interface UseSearchResult {
  results: ProductSearchResult[]
  loading: boolean
  error: string | null
  searchProducts: (query: string, filters?: SearchFilters) => Promise<void>
  clearResults: () => void
}

export const useSearch = (): UseSearchResult => {
  const [results, setResults] = useState<ProductSearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const searchProducts = async (query: string, filters?: SearchFilters) => {
    if (!query.trim()) {
      setError('Please enter a search query')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await apiClient.search({
        query,
        limit: 20,
        filters,
      })

      setResults(response.results)
      
      if (response.results.length === 0) {
        setError('No products found. Try a different search term.')
      }
    } catch (err) {
      console.error('Search error:', err)
      setError('Failed to search products. Please try again.')
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  const clearResults = () => {
    setResults([])
    setError(null)
  }

  return {
    results,
    loading,
    error,
    searchProducts,
    clearResults,
  }
}