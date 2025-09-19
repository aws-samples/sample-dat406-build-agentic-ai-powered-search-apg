import React, { useState, useEffect } from 'react'
import { Search, Database, Bot, Layers, Zap, ChevronRight, Sparkles, Server, Star, AlertCircle, Loader } from 'lucide-react'

const API_URL = '/api'

function App() {
  const [searchQuery, setSearchQuery] = useState('')
  const [activeTab, setActiveTab] = useState('vector')
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(false)
  const [searchResults, setSearchResults] = useState(null)
  const [stats, setStats] = useState(null)
  const [categories, setCategories] = useState([])
  const [selectedCategory, setSelectedCategory] = useState('')
  const [queryTime, setQueryTime] = useState(0)
  const [ragResponse, setRagResponse] = useState(null)
  const [showRagModal, setShowRagModal] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchStats()
    fetchCategories()
  }, [])

  const fetchStats = async () => {
    try {
      const response = await fetch(`${API_URL}/stats`)
      if (response.ok) {
        const data = await response.json()
        setStats(data)
      }
    } catch (error) {
      console.error('Failed to fetch stats:', error)
    }
  }

  const fetchCategories = async () => {
    try {
      const response = await fetch(`${API_URL}/products/categories`)
      if (response.ok) {
        const data = await response.json()
        setCategories(data)
      }
    } catch (error) {
      console.error('Failed to fetch categories:', error)
    }
  }

  const handleSearch = async () => {
    if (!searchQuery.trim()) return
    
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`${API_URL}/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: searchQuery,
          limit: 20,
          category: selectedCategory || undefined,
        }),
      })
      
      if (!response.ok) {
        throw new Error('Search failed')
      }
      
      const data = await response.json()
      setSearchResults(data)
      setProducts(data.products)
      setQueryTime(data.query_time_ms)
    } catch (error) {
      console.error('Search failed:', error)
      setError('Search service is currently unavailable. Please try again.')
      setProducts([])
    } finally {
      setLoading(false)
    }
  }

  const formatPrice = (price) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(price || 0)
  }

  const renderStars = (rating) => {
    const stars = []
    const fullStars = Math.floor(rating || 0)
    const hasHalfStar = (rating || 0) % 1 >= 0.5
    
    for (let i = 0; i < fullStars; i++) {
      stars.push(<Star key={i} className="w-4 h-4 fill-yellow-400 text-yellow-400" />)
    }
    if (hasHalfStar && fullStars < 5) {
      stars.push(<Star key="half" className="w-4 h-4 fill-yellow-400/50 text-yellow-400" />)
    }
    const emptyStars = 5 - Math.ceil(rating || 0)
    for (let i = 0; i < emptyStars; i++) {
      stars.push(<Star key={`empty-${i}`} className="w-4 h-4 text-gray-600" />)
    }
    
    return <div className="flex items-center gap-0.5">{stars}</div>
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 via-purple-950 to-gray-900">
      <header className="border-b border-purple-800/30 backdrop-blur-sm bg-gray-900/50 sticky top-0 z-50">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Sparkles className="w-8 h-8 text-purple-500" />
              <h1 className="text-2xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
                Blaize Bazaar
              </h1>
            </div>
            <div className="flex items-center gap-4 text-sm">
              <span className="text-gray-400">
                {stats ? `${stats.total_products?.toLocaleString() || '0'} Products` : 'Aurora PostgreSQL'}
              </span>
              <span className="px-3 py-1 bg-green-500/20 text-green-400 rounded-full text-xs font-semibold">
                LIVE
              </span>
            </div>
          </div>
        </div>
      </header>

      <section className="container mx-auto px-6 py-16">
        <div className="text-center mb-12">
          <h2 className="text-5xl font-bold text-white mb-4">
            AI-Powered E-Commerce with
            <span className="bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent"> Aurora PostgreSQL</span>
          </h2>
          <p className="text-xl text-gray-300 max-w-3xl mx-auto">
            {stats?.total_products > 0 
              ? `Search through ${stats.total_products.toLocaleString()} real Amazon products using semantic search powered by pgvector`
              : 'Experience the power of vector search, RAG, and multi-agent AI systems'
            }
          </p>
        </div>

        <div className="text-center">
          <p className="text-gray-500">Full interactive version coming soon...</p>
        </div>
      </section>
    </div>
  )
}

export default App
