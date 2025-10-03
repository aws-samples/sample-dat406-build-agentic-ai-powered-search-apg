/**
 * Premium Header Component - Enhanced with Theme Toggle
 * ALWAYS DARK BACKGROUND - No transparency at top!
 */
import { useState, useEffect, useRef } from 'react'
import { useTheme } from '../App'
import { apiClient } from '../services/api'

interface HeaderProps {
  activeSection?: 'shop' | 'collections' | 'tech'
  onNavigate?: (section: 'shop' | 'collections' | 'tech') => void
  onSearch?: (query: string) => void
}

const Header = ({ activeSection = 'shop', onNavigate, onSearch }: HeaderProps) => {
  const [searchQuery, setSearchQuery] = useState('')
  const [suggestions, setSuggestions] = useState<Array<{text: string, category: string}>>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const { theme, toggleTheme } = useTheme()
  const searchRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setShowSuggestions(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  useEffect(() => {
    if (searchQuery.length >= 2) {
      const timer = setTimeout(async () => {
        try {
          const result = await apiClient.autocomplete(searchQuery)
          setSuggestions(result.suggestions)
          setShowSuggestions(true)
        } catch (error) {
          console.error('Autocomplete failed:', error)
        }
      }, 300)
      return () => clearTimeout(timer)
    } else {
      setSuggestions([])
      setShowSuggestions(false)
    }
  }, [searchQuery])

  const handleNavClick = (section: 'shop' | 'collections' | 'tech') => {
    if (onNavigate) {
      onNavigate(section)
    }
  }

  const handleSearchKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && searchQuery.trim() && onSearch) {
      onSearch(searchQuery)
    }
  }

  return (
    <header 
      className="fixed top-0 left-0 right-0 z-50 border-b relative"
      style={{
        background: theme === 'dark' 
          ? 'rgba(10, 10, 15, 0.95)' 
          : 'rgba(255, 255, 255, 0.95)',
        backdropFilter: 'blur(30px)',
        WebkitBackdropFilter: 'blur(30px)',
        borderColor: theme === 'dark' 
          ? 'rgba(106, 27, 154, 0.3)' 
          : 'rgba(0, 0, 0, 0.1)'
      }}
    >
      <nav className="max-w-[1400px] mx-auto px-10 h-[72px] flex items-center justify-between relative z-10">
        {/* Logo */}
        <div 
          className="logo gradient-text-chrome text-2xl font-light tracking-tight cursor-pointer"
          onClick={() => handleNavClick('shop')}
        >
          Blaize Bazaar
        </div>

        {/* Center Navigation */}
        <div className="absolute left-1/2 transform -translate-x-1/2 flex gap-10">
          <a
            onClick={() => handleNavClick('shop')}
            className={`nav-link text-sm font-normal transition-colors duration-300 cursor-pointer relative ${
              activeSection === 'shop' ? 'text-text-primary' : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            Shop
            {activeSection === 'shop' && (
              <span className="absolute -bottom-[26px] left-0 right-0 h-[1px] bg-accent-light opacity-60" />
            )}
          </a>
          <a
            onClick={() => handleNavClick('collections')}
            className={`nav-link text-sm font-normal transition-colors duration-300 cursor-pointer relative ${
              activeSection === 'collections' ? 'text-text-primary' : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            Collections
            {activeSection === 'collections' && (
              <span className="absolute -bottom-[26px] left-0 right-0 h-[1px] bg-accent-light opacity-60" />
            )}
          </a>
          <a
            onClick={() => handleNavClick('tech')}
            className={`nav-link text-sm font-normal transition-colors duration-300 cursor-pointer relative ${
              activeSection === 'tech' ? 'text-text-primary' : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            Architecture
            {activeSection === 'tech' && (
              <span className="absolute -bottom-[26px] left-0 right-0 h-[1px] bg-accent-light opacity-60" />
            )}
          </a>
        </div>

        {/* Right Side - Search & Theme Toggle */}
        <div className="flex items-center gap-4">
          <div className="relative w-60" ref={searchRef}>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={handleSearchKeyDown}
              placeholder="Search products..."
              className="w-full px-3 py-2 text-sm input-field rounded-lg"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-text-secondary hover:text-text-primary"
              >
                ✕
              </button>
            )}
            {showSuggestions && suggestions.length > 0 && (
              <div className="absolute top-full mt-2 w-full bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 overflow-hidden z-50">
                {suggestions.map((s, i) => (
                  <div
                    key={i}
                    onClick={() => {
                      setSearchQuery(s.text)
                      setShowSuggestions(false)
                      if (onSearch) onSearch(s.text)
                    }}
                    className="px-4 py-2 hover:bg-purple-50 dark:hover:bg-purple-900/20 cursor-pointer border-b border-gray-100 dark:border-gray-700 last:border-0"
                  >
                    <div className="text-sm text-gray-900 dark:text-white">{s.text}</div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">{s.category}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* GitHub Link */}
          <a
            href="https://github.com/aws-samples/sample-dat406-build-agentic-ai-powered-search-apg"
            target="_blank"
            rel="noopener noreferrer"
            className="p-2 rounded-lg hover:bg-white/10 dark:hover:bg-white/10 transition-all duration-300 group"
            aria-label="View on GitHub"
            title="View source code on GitHub"
          >
            <svg 
              className="w-5 h-5 text-text-secondary group-hover:text-text-primary transition-colors" 
              fill="currentColor" 
              viewBox="0 0 24 24"
            >
              <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
            </svg>
          </a>

          {/* Theme Toggle Button */}
          <button
            onClick={toggleTheme}
            className="p-2 rounded-lg hover:bg-white/10 dark:hover:bg-white/10 transition-all duration-300 group"
            aria-label="Toggle theme"
            title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          >
            {theme === 'dark' ? (
              <svg 
                className="w-5 h-5 text-yellow-400 group-hover:text-yellow-300 transition-colors" 
                fill="currentColor" 
                viewBox="0 0 20 20"
              >
                <path 
                  fillRule="evenodd" 
                  d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" 
                  clipRule="evenodd" 
                />
              </svg>
            ) : (
              <svg 
                className="w-5 h-5 text-purple-600 group-hover:text-purple-500 transition-colors" 
                fill="currentColor" 
                viewBox="0 0 20 20"
              >
                <path 
                  d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" 
                />
              </svg>
            )}
          </button>
        </div>
      </nav>

      {/* Animated Purple Data Flow Line - Full Width - Only in Dark Mode */}
      {theme === 'dark' && (
        <div className="absolute bottom-0 left-0 w-full h-[2px] pointer-events-none z-50">
          <div
            className="absolute h-full w-[40%] top-0"
            style={{
              background: 'rgba(186, 104, 200, 0.2)',
              boxShadow: '0 0 4px rgba(186, 104, 200, 0.6)',
              animation: 'dataFlowPurple 3s linear infinite'
            }}
          />
        </div>
      )}
    </header>
  )
}

export default Header