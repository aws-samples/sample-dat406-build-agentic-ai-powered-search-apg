/**
 * Premium Search Overlay Component - Apple-inspired Design
 * Glassmorphism, smooth animations, and refined spacing
 * DARK MODE READY - SYNTAX FIXED
 */
import { useEffect, useState } from 'react'
import { Search, X, Sparkles, Zap, Database } from 'lucide-react'
import { apiClient } from '../services/api'

interface SearchResult {
  id: string
  name: string
  category: string
  price: number
  icon: string
  similarity: number
  stars: number
  reviews: number
  productUrl?: string
}

interface SearchOverlayProps {
  isVisible: boolean
  onClose: () => void
  searchTerm: string
}

const SearchOverlay = ({ 
  isVisible, 
  onClose, 
  searchTerm
}: SearchOverlayProps) => {
  const [results, setResults] = useState<SearchResult[]>([])
  const [allResults, setAllResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [latency, setLatency] = useState('0ms')
  const [minPrice, setMinPrice] = useState<number>(0)
  const [maxPrice, setMaxPrice] = useState<number>(10000)
  const [minStars, setMinStars] = useState<number>(0)
  const [isSemanticSearch, setIsSemanticSearch] = useState(false)

  useEffect(() => {
    if (isVisible && searchTerm) {
      performSearch()
    }
  }, [isVisible, searchTerm])

  const performSearch = async () => {
    setLoading(true)
    const startTime = performance.now()
    
    try {
      // Use fast category endpoint for known categories
      const categoryTerms = ['security cameras', 'vacuum cleaners', 'gaming consoles', 'shaving grooming', 'kids watches', 'kids play tractors']
      const isCategorySearch = categoryTerms.some(term => searchTerm.toLowerCase().includes(term))
      
      let response
      if (isCategorySearch) {
        // Fast category browse without embeddings
        const res = await fetch(`http://localhost:8000/api/products/category/${encodeURIComponent(searchTerm)}?limit=10`)
        response = await res.json()
        setIsSemanticSearch(false)
      } else {
        // Semantic search with embeddings
        response = await apiClient.search({
          query: searchTerm,
          limit: 10,
          min_similarity: 0.0
        })
        setIsSemanticSearch(true)
      }
      
      const endTime = performance.now()
      setLatency(`${Math.round(endTime - startTime)}ms`)
      
      console.log('Search response:', response)
      
      // Transform API response to SearchResult format
      const transformedResults: SearchResult[] = response.results.map(r => ({
        id: r.product.productId,
        name: r.product.product_description,
        category: r.product.category_name || 'General',
        price: r.product.price || 0,
        icon: r.product.imgurl || '', // Use actual image URL
        similarity: r.product.similarity_score,
        stars: r.product.stars || 0,
        reviews: r.product.reviews || 0,
        productUrl: r.product.producturl || '' // Add Amazon URL
      }))
      
      console.log('Transformed results:', transformedResults)
      setAllResults(transformedResults)
      setResults(transformedResults)
    } catch (error) {
      console.error('Search failed:', error)
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const filtered = allResults.filter(r => 
      r.price >= minPrice && 
      r.price <= maxPrice && 
      r.stars >= minStars
    )
    setResults(filtered)
  }, [minPrice, maxPrice, minStars, allResults])

  if (!isVisible) return null

  const displayResults = results

  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 
                   animate-in fade-in duration-300"
        onClick={onClose}
      />

      {/* Overlay Content */}
      <div 
        className="fixed top-20 left-1/2 -translate-x-1/2 w-full max-w-6xl z-50
                   animate-in slide-in-from-top-4 fade-in duration-500"
        style={{ maxHeight: 'calc(100vh - 120px)' }}
      >
        <div className="mx-4 rounded-[24px] overflow-hidden
                       bg-white/95 dark:bg-gray-900/95 backdrop-blur-2xl
                       shadow-2xl border border-white/20 dark:border-gray-700/50">
          
          {/* Header */}
          <div className="px-8 py-6 border-b border-gray-100/50 dark:border-gray-700/50
                         bg-gradient-to-r from-purple-50/50 via-white to-blue-50/50
                         dark:from-purple-900/20 dark:via-gray-800 dark:to-blue-900/20">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-full bg-gradient-to-br from-purple-500 to-blue-500">
                  <Search className="h-4 w-4 text-white" strokeWidth={2} />
                </div>
                <div>
                  <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    Searching for
                  </div>
                  <div className="text-xl font-semibold bg-gradient-to-r from-purple-600 to-blue-600 
                                dark:from-purple-400 dark:to-blue-400
                                bg-clip-text text-transparent">
                    "{searchTerm}"
                  </div>
                </div>
              </div>

              <button
                onClick={onClose}
                className="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700
                         transition-all duration-300 group"
              >
                <X className="h-5 w-5 text-gray-500 dark:text-gray-400 
                             group-hover:text-gray-900 dark:group-hover:text-white" strokeWidth={2} />
              </button>
            </div>

            {/* Stats Bar */}
            <div className="flex items-center gap-6 text-sm">
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full 
                            bg-white/80 dark:bg-gray-800/80 shadow-sm
                            border border-gray-100 dark:border-gray-700">
                <Zap className="h-3.5 w-3.5 text-amber-500 dark:text-amber-400" strokeWidth={2} />
                <span className="font-semibold text-gray-900 dark:text-white">{latency}</span>
                <span className="text-gray-500 dark:text-gray-400">response</span>
              </div>
              
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full 
                            bg-white/80 dark:bg-gray-800/80 shadow-sm
                            border border-gray-100 dark:border-gray-700">
                <Sparkles className="h-3.5 w-3.5 text-purple-500 dark:text-purple-400" strokeWidth={2} />
                <span className="font-semibold text-gray-900 dark:text-white">{displayResults.length}</span>
                <span className="text-gray-500 dark:text-gray-400">results</span>
              </div>

              {isSemanticSearch && (
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-full 
                              bg-white/80 dark:bg-gray-800/80 shadow-sm
                              border border-gray-100 dark:border-gray-700">
                  <Database className="h-3.5 w-3.5 text-blue-500 dark:text-blue-400" strokeWidth={2} />
                  <span className="text-gray-500 dark:text-gray-400 font-medium">pgvector similarity</span>
                </div>
              )}
            </div>
          </div>

          {/* Filters */}
          <div className="px-8 py-4 border-b border-gray-100/50 dark:border-gray-700/50
                         bg-white/50 dark:bg-gray-800/50">
            <div className="flex items-center gap-6">
              {/* Price Range */}
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Price:</span>
                <input
                  type="number"
                  value={minPrice}
                  onChange={(e) => setMinPrice(Number(e.target.value))}
                  placeholder="Min"
                  className="w-20 px-2 py-1 text-sm rounded-lg bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 text-gray-900 dark:text-white"
                />
                <span className="text-gray-400">-</span>
                <input
                  type="number"
                  value={maxPrice}
                  onChange={(e) => setMaxPrice(Number(e.target.value))}
                  placeholder="Max"
                  className="w-20 px-2 py-1 text-sm rounded-lg bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 text-gray-900 dark:text-white"
                />
              </div>

              {/* Star Rating */}
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Min Rating:</span>
                <div className="flex gap-1">
                  {[0, 3, 4, 4.5, 5].map(rating => (
                    <button
                      key={rating}
                      onClick={() => setMinStars(rating)}
                      className={`px-3 py-1 text-xs rounded-full transition-all ${
                        minStars === rating
                          ? 'bg-gradient-to-r from-purple-500 to-blue-500 text-white shadow-lg'
                          : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                      }`}
                    >
                      {rating === 0 ? 'All' : `${rating}★`}
                    </button>
                  ))}
                </div>
              </div>

              {/* Reset */}
              <button
                onClick={() => {
                  setMinPrice(0)
                  setMaxPrice(10000)
                  setMinStars(0)
                }}
                className="ml-auto text-sm text-purple-600 dark:text-purple-400 hover:underline"
              >
                Reset Filters
              </button>
            </div>
          </div>

          {/* Results Grid */}
          <div className="p-6 overflow-y-auto custom-scrollbar" 
               style={{ maxHeight: 'calc(100vh - 280px)' }}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {displayResults.map((result, index) => (
                <a
                  key={result.id}
                  href={result.productUrl || '#'}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="group relative p-5 rounded-2xl cursor-pointer block
                           bg-white dark:bg-gray-800 
                           hover:bg-gradient-to-br hover:from-purple-50/50 hover:to-blue-50/50
                           dark:hover:from-purple-900/20 dark:hover:to-blue-900/20
                           border border-gray-100 dark:border-gray-700 
                           hover:border-purple-200 dark:hover:border-purple-700
                           shadow-sm hover:shadow-xl
                           transition-all duration-500 ease-out
                           transform hover:scale-[1.02]"
                  style={{
                    animationDelay: `${index * 50}ms`,
                    animation: 'slideIn 0.5s ease-out forwards'
                  }}
                >
                  {/* Similarity Score Badge - Only for semantic search */}
                  {isSemanticSearch && (
                    <div className="absolute top-4 right-4 flex items-center gap-1.5
                                  px-3 py-1.5 rounded-full
                                  bg-gradient-to-r from-purple-500 to-blue-500
                                  shadow-lg group-hover:shadow-xl
                                  transition-all duration-300">
                      <Sparkles className="h-3 w-3 text-white" strokeWidth={2} />
                      <span className="text-xs font-bold text-white">
                        {Math.round(result.similarity * 100)}%
                      </span>
                    </div>
                  )}

                  {/* Product Info */}
                  <div className="flex items-start gap-4">
                    {/* Product Image */}
                    <div className="flex-shrink-0 w-16 h-16 rounded-2xl overflow-hidden
                                  bg-gradient-to-br from-gray-50 to-gray-100
                                  dark:from-gray-700 dark:to-gray-600
                                  flex items-center justify-center
                                  group-hover:scale-110 transition-transform duration-300">
                      {result.icon ? (
                        <img 
                          src={result.icon} 
                          alt={result.name}
                          className="w-full h-full object-cover"
                          onError={(e) => {
                            e.currentTarget.style.display = 'none'
                            const parent = e.currentTarget.parentElement
                            if (parent) parent.innerHTML = '📦'
                          }}
                        />
                      ) : (
                        <span className="text-3xl">📦</span>
                      )}
                    </div>

                    {/* Details */}
                    <div className="flex-1 min-w-0 pt-1">
                      <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-1.5
                                   group-hover:text-purple-600 dark:group-hover:text-purple-400 
                                   transition-colors duration-300
                                   line-clamp-2">
                        {result.name}
                      </h3>
                      
                      <div className="inline-block px-2.5 py-1 rounded-full
                                    bg-gray-100 dark:bg-gray-700 
                                    group-hover:bg-purple-100 dark:group-hover:bg-purple-900/40
                                    transition-colors duration-300">
                        <span className="text-xs font-medium text-gray-600 dark:text-gray-300
                                       group-hover:text-purple-600 dark:group-hover:text-purple-400">
                          {result.category}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Price and Rating Footer */}
                  <div className="mt-4 pt-4 border-t border-gray-100 dark:border-gray-700
                                flex items-center justify-between">
                    <div className="text-2xl font-bold 
                                  bg-gradient-to-r from-purple-600 to-blue-600 
                                  dark:from-purple-400 dark:to-blue-400
                                  bg-clip-text text-transparent">
                      ${result.price}
                    </div>

                    <div className="flex items-center gap-3 text-sm">
                      <div className="flex items-center gap-1">
                        <span className="text-amber-400">★</span>
                        <span className="font-semibold text-gray-900 dark:text-white">
                          {result.stars}
                        </span>
                      </div>
                      <span className="text-gray-400 dark:text-gray-600">·</span>
                      <span className="text-gray-500 dark:text-gray-400 font-medium">
                        {result.reviews.toLocaleString()} reviews
                      </span>
                    </div>
                  </div>
                </a>
              ))}
            </div>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .custom-scrollbar::-webkit-scrollbar {
          width: 8px;
        }

        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }

        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: linear-gradient(180deg, #a855f7 0%, #3b82f6 100%);
          border-radius: 4px;
        }

        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: linear-gradient(180deg, #9333ea 0%, #2563eb 100%);
        }
      `}</style>
    </>
  )
}

export default SearchOverlay