/**
 * Premium Header Component - Enhanced with Theme Toggle
 */
import { useState } from 'react'
import { useTheme } from '../App'

interface HeaderProps {
  activeSection?: 'shop' | 'collections' | 'about'
  onNavigate?: (section: 'shop' | 'collections' | 'about') => void
  onSearch?: (query: string) => void
}

const Header = ({ activeSection = 'shop', onNavigate, onSearch }: HeaderProps) => {
  const [searchQuery, setSearchQuery] = useState('')
  const { theme, toggleTheme } = useTheme()

  const handleNavClick = (section: 'shop' | 'collections' | 'about') => {
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
    <header className="fixed top-0 left-0 right-0 z-50 glass">
      <nav className="max-w-[1400px] mx-auto px-10 h-[72px] flex items-center justify-between">
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
            onClick={() => handleNavClick('about')}
            className={`nav-link text-sm font-normal transition-colors duration-300 cursor-pointer relative ${
              activeSection === 'about' ? 'text-text-primary' : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            About
            {activeSection === 'about' && (
              <span className="absolute -bottom-[26px] left-0 right-0 h-[1px] bg-accent-light opacity-60" />
            )}
          </a>
        </div>

        {/* Right Side - Search & Theme Toggle */}
        <div className="flex items-center gap-4">
          <div className="relative w-60">
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
          </div>

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
    </header>
  )
}

export default Header