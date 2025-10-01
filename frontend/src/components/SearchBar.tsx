/**
 * Search bar component with input and search button
 */
import { useState, FormEvent } from 'react'
import { Search, X } from 'lucide-react'

interface SearchBarProps {
  onSearch: (query: string) => void
  loading?: boolean
  placeholder?: string
}

const SearchBar = ({ 
  onSearch, 
  loading = false,
  placeholder = "Search for products... (e.g., 'wireless headphones', 'laptop stand')"
}: SearchBarProps) => {
  const [query, setQuery] = useState('')

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (query.trim()) {
      onSearch(query.trim())
    }
  }

  const handleClear = () => {
    setQuery('')
  }

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="relative">
        {/* Search Icon */}
        <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
          <Search className="h-5 w-5 text-gray-400" />
        </div>

        {/* Input Field */}
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={placeholder}
          disabled={loading}
          className="w-full pl-12 pr-24 py-4 text-lg border-2 border-gray-300 rounded-xl 
                   focus:ring-2 focus:ring-primary-500 focus:border-transparent
                   disabled:bg-gray-100 disabled:cursor-not-allowed
                   transition-all duration-200"
        />

        {/* Clear Button */}
        {query && !loading && (
          <button
            type="button"
            onClick={handleClear}
            className="absolute inset-y-0 right-24 flex items-center pr-3 text-gray-400 
                     hover:text-gray-600 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        )}

        {/* Search Button */}
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="absolute inset-y-0 right-0 flex items-center px-6 m-1 
                   bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg
                   disabled:bg-gray-300 disabled:cursor-not-allowed
                   transition-colors duration-200"
        >
          {loading ? (
            <div className="flex items-center space-x-2">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
              <span>Searching...</span>
            </div>
          ) : (
            'Search'
          )}
        </button>
      </div>

      {/* Search Tips */}
      <div className="mt-2 text-xs text-gray-500">
        Try: "noise cancelling headphones", "ergonomic mouse", or "4K monitor"
      </div>
    </form>
  )
}

export default SearchBar