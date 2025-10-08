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

  const [showCollectionsMenu, setShowCollectionsMenu] = useState(false)
  const [placeholderIndex, setPlaceholderIndex] = useState(0)
  const { theme } = useTheme()
  const searchRef = useRef<HTMLDivElement>(null)
  const collectionsRef = useRef<HTMLDivElement>(null)

  const placeholders = [
    'laptop under $800 for gaming',
    'wireless headphones with noise cancellation',
    'camera for travel photography',
    '4K monitor under $500',
    'ergonomic keyboard for programming'
  ]

  const categories = [
    { icon: '🔌', name: 'Cables & Chargers', query: 'cable charger' },
    { icon: '⌚', name: 'Watches', query: 'watch' },
    { icon: '📷', name: 'Cameras', query: 'camera' },
    { icon: '💻', name: 'Laptops', query: 'laptop' },
    { icon: '🎧', name: 'Headphones', query: 'headphones earbuds' },
    { icon: '🎮', name: 'Gaming', query: 'gaming' },
  ]

  useEffect(() => {
    const interval = setInterval(() => {
      setPlaceholderIndex((prev) => (prev + 1) % placeholders.length)
    }, 3000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (collectionsRef.current && !collectionsRef.current.contains(e.target as Node)) {
        setShowCollectionsMenu(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])



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
      <nav className="px-16 h-[72px] flex items-center justify-between relative z-10">
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
            className={`nav-link text-base font-normal transition-colors duration-300 cursor-pointer relative ${
              activeSection === 'shop' ? 'text-text-primary' : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            Shop
            {activeSection === 'shop' && (
              <span className="absolute -bottom-[26px] left-0 right-0 h-[1px] bg-accent-light opacity-60" />
            )}
          </a>
          <div 
            ref={collectionsRef} 
            className="relative"
            onMouseEnter={() => setShowCollectionsMenu(true)}
            onMouseLeave={() => setShowCollectionsMenu(false)}
          >
            <a
              onClick={() => handleNavClick('collections')}
              className={`nav-link text-base font-normal transition-colors duration-300 cursor-pointer relative ${
                activeSection === 'collections' ? 'text-text-primary' : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              Collections
              {activeSection === 'collections' && (
                <span className="absolute -bottom-[26px] left-0 right-0 h-[1px] bg-accent-light opacity-60" />
              )}
            </a>
            {showCollectionsMenu && (
              <div className="absolute top-full pt-6 left-0 w-64">
                <div className="glass-strong rounded-2xl shadow-2xl border border-purple-500/20 overflow-hidden animate-slideUp">
                  {categories.map((cat, i) => (
                    <div
                      key={i}
                      onClick={() => {
                        setShowCollectionsMenu(false)
                        if (onSearch) onSearch(cat.query)
                      }}
                      className="px-4 py-3 hover:bg-purple-500/10 cursor-pointer border-b border-purple-500/10 last:border-0 transition-all duration-200 flex items-center gap-3"
                    >
                      <span className="text-2xl">{cat.icon}</span>
                      <span className="text-sm text-text-primary">{cat.name}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
          <a
            onClick={() => handleNavClick('tech')}
            className={`nav-link text-base font-normal transition-colors duration-300 cursor-pointer relative ${
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
          <div className="flex items-center gap-2">
            <div className="relative w-[450px] group" ref={searchRef}>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={handleSearchKeyDown}
              placeholder={`Try: "${placeholders[placeholderIndex]}"`}
              className="w-full px-3 py-2 text-sm input-field rounded-lg"
            />
            {/* AI Badge */}
            {!searchQuery && (
              <div className="absolute right-3 top-1/2 transform -translate-y-1/2 flex items-center gap-1 px-2 py-0.5 rounded-full bg-purple-500/20 border border-purple-500/30">
                <span className="text-[10px] text-purple-300 font-medium">✨ AI-Powered</span>
              </div>
            )}
            {/* AI Hint Tooltip - Shows on hover */}
            {!searchQuery && (
              <div className="absolute -bottom-8 left-0 opacity-0 group-hover:opacity-100 transition-opacity duration-200 text-xs text-purple-400 whitespace-nowrap">
                💡 Semantic Search: Understands intent, not just keywords
              </div>
            )}
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-text-secondary hover:text-text-primary"
              >
                ✕
              </button>
            )}

            </div>
            <button
              onClick={() => searchQuery.trim() && onSearch?.(searchQuery)}
              disabled={!searchQuery.trim()}
              className="px-4 py-2 rounded-lg text-sm font-medium transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
              style={{
                background: searchQuery.trim() ? 'linear-gradient(135deg, #6a1b9a 0%, #ba68c8 100%)' : 'rgba(255, 255, 255, 0.1)',
                color: 'white'
              }}
            >
              Search
            </button>
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
        </div>
      </nav>

      {/* Animated Purple Data Flow Line - Full Width */}
      <div className="absolute bottom-0 left-0 w-full h-[1px] pointer-events-none z-50">
        <div
          className="absolute h-full w-[20%] top-0"
          style={{
            background: 'linear-gradient(90deg, transparent, rgba(186, 104, 200, 0.8), transparent)',
            boxShadow: '0 0 12px rgba(186, 104, 200, 0.9), 0 0 24px rgba(186, 104, 200, 0.5)',
            animation: 'dataFlowPurple 3s linear infinite'
          }}
        />
      </div>
    </header>
  )
}

export default Header