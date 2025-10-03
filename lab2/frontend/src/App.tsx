/**
 * Main App Component - Enhanced with Light/Dark Mode
 * Hero section, Collections, About pages with theme toggle
 */
import { useState, useEffect, createContext, useContext } from 'react'
import Header from './components/Header'
import AIAssistant from './components/AIAssistant'
import SearchOverlay from './components/SearchOverlay'
import ProductModal from './components/ProductModal'
import { Product } from './services/types'
import './styles/premium-heading-styles.css'

// Theme Context
type Theme = 'light' | 'dark'
interface ThemeContextType {
  theme: Theme
  toggleTheme: () => void
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

export const useTheme = () => {
  const context = useContext(ThemeContext)
  if (!context) throw new Error('useTheme must be used within ThemeProvider')
  return context
}

// Premium products for showcase rotation
const premiumProducts = [
  { name: 'Apple AirPods Pro 2', price: '$249', icon: '🎧', desc: 'Active Noise Cancellation' },
  { name: 'Sony WH-1000XM5', price: '$399', icon: '🎧', desc: 'Industry Leading ANC' },
  { name: 'MacBook Pro 16" M3 Max', price: '$3,999', icon: '💻', desc: '48GB Unified Memory' },
  { name: 'iPhone 15 Pro Max', price: '$1,199', icon: '📱', desc: 'Titanium Design' },
  { name: 'Apple Vision Pro', price: '$3,499', icon: '🥽', desc: 'Spatial Computing' },
  { name: 'Bose QuietComfort Ultra', price: '$429', icon: '🎧', desc: 'Immersive Audio' },
  { name: 'iPad Pro 12.9" M2', price: '$1,299', icon: '📱', desc: 'Liquid Retina XDR' },
  { name: 'Samsung Galaxy S24 Ultra', price: '$1,299', icon: '📱', desc: '200MP Camera System' },
  { name: 'Dell XPS 15 OLED', price: '$2,499', icon: '💻', desc: '4K OLED Touch Display' },
  { name: 'Apple Watch Ultra 2', price: '$799', icon: '⌚', desc: 'Precision GPS' },
]

type Section = 'shop' | 'collections' | 'tech'

function App() {
  const [theme, setTheme] = useState<Theme>(() => {
    const saved = localStorage.getItem('theme')
    return (saved as Theme) || 'dark'
  })
  const [activeSection, setActiveSection] = useState<Section>('shop')
  const [currentProductIndex, setCurrentProductIndex] = useState(0)
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null)
  const [showcaseKey, setShowcaseKey] = useState(0)
  const [searchOverlayVisible, setSearchOverlayVisible] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')

  // Apply theme to document
  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
    document.documentElement.classList.toggle('light', theme === 'light')
    localStorage.setItem('theme', theme)
  }, [theme])

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark')
  }

  // Rotate products in hero showcase
  useEffect(() => {
    const interval = setInterval(() => {
      setShowcaseKey(prev => prev + 1)
      setCurrentProductIndex((prev) => (prev + 1) % premiumProducts.length)
    }, 3500)

    return () => clearInterval(interval)
  }, [])

  const currentProduct = premiumProducts[currentProductIndex]

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      <div className="min-h-screen bg-bg-primary relative transition-colors duration-300">
        {/* Header */}
        <Header
          activeSection={activeSection}
          onNavigate={setActiveSection}
          onSearch={(query) => {
            setSearchQuery(query)
            setSearchOverlayVisible(true)
          }}
        />

        {/* Search Overlay */}
        <SearchOverlay
          isVisible={searchOverlayVisible}
          onClose={() => setSearchOverlayVisible(false)}
          searchTerm={searchQuery}
        />

        {/* Main Content */}
        <main className="mt-[72px] relative z-10">
          {/* Shop Section (Hero) */}
          {activeSection === 'shop' && (
            <section className="h-[calc(100vh-72px)] flex items-center px-10 bg-gradient-radial">
              <div className="max-w-[1400px] mx-auto w-full grid grid-cols-2 gap-20 items-center">
                {/* Left: Text */}
                <div>
                    <h1 className="text-hero mb-6 text-gray-900 dark:text-white">
                      Welcome to<br />
                      <span className="gradient-text-chrome" style={{ 
                        fontSize: 'inherit',
                        fontFamily: '"SF Pro Display", -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif',
                        fontWeight: '100',
                        letterSpacing: '0.03em'
                      }}>
                        Blaize Bazaar
                      </span>
                    </h1>
                  <div className="text-subtitle text-white dark:text-white mb-8 font-light">
                    Shop Smart with AI-Powered Search
                  </div>
                  <p className="text-lg text-gray-700 dark:text-white mb-12 leading-relaxed" style={{ fontWeight: '300', letterSpacing: '0.01em' }}>
                    Experience intelligent product discovery powered by Aurora PostgreSQL with pgvector,
                    Amazon Bedrock, and AWS Strands SDK. Real-time semantic search meets premium shopping.
                  </p>
                  <div className="flex gap-4">
                    <button 
                      className="btn-primary"
                      onClick={() => {
                        const bubble = document.querySelector('.floating-bubble') as HTMLElement
                        if (bubble) bubble.click()
                      }}
                    >
                      Chat with Aurora AI
                    </button>
                    <button 
                      className="btn-secondary"
                      onClick={() => setActiveSection('collections')}
                    >
                      Browse Collections
                    </button>
                  </div>
                </div>

                {/* Right: Product Showcase - FIXED FOR DARK MODE */}
                <div className="h-[500px] flex items-center justify-center">
                  <div className="w-full h-full card flex items-center justify-center relative overflow-hidden">
                    <div 
                      key={showcaseKey}
                      className="text-center relative z-10 opacity-0 animate-fadeIn"
                    >
                      <div className="text-[180px] mb-6">{currentProduct.icon}</div>
                      {/* FIXED: Added dark:text-white for dark mode visibility */}
                      <h3 className="text-2xl font-normal mb-3 text-gray-900 dark:text-white">
                        {currentProduct.name}
                      </h3>
                      <div className="text-[28px] text-accent-light mb-2">{currentProduct.price}</div>
                      {/* FIXED: Changed from text-text-secondary to explicit dark mode classes */}
                      <p className="text-gray-600 dark:text-gray-400 text-sm">{currentProduct.desc}</p>
                    </div>
                  </div>
                </div>
              </div>
            </section>
          )}

          {/* Collections Section */}
          {activeSection === 'collections' && (
            <section className="max-w-[1400px] mx-auto px-10 py-24">
              <div className="text-center mb-12">
                <h2 className="text-5xl font-light mb-4 text-gray-900 dark:text-white">Curated Collections</h2>
                <p className="text-text-secondary text-lg">AI-powered collections tailored to your preferences</p>
              </div>
              <div className="grid grid-cols-3 gap-8">
                {[
                  { icon: '📷', title: 'Security Cameras', count: '200 products • 1.9M reviews', query: 'security cameras' },
                  { icon: '💻', title: 'Vacuum Cleaners', count: '100 products • Perfect 5★ rating', query: 'vacuum cleaners' },
                  { icon: '🎮', title: 'Gaming Consoles', count: '260 products • Trending now', query: 'gaming consoles' },
                  { icon: '🎧', title: 'Shaving & Grooming', count: '193 products • 481K reviews', query: 'shaving grooming' },
                  { icon: '⌚', title: 'Kids Watches', count: '117 products • 4.4★ average', query: 'kids watches' },
                  { icon: '🚜', title: 'Kids Play Tractors', count: '106 products • 4.8★ rating', query: 'kids play tractors' },
                ].map((collection, index) => (
                  <div 
                    key={index} 
                    className="card cursor-pointer"
                    onClick={() => {
                      setSearchQuery(collection.query)
                      setSearchOverlayVisible(true)
                    }}
                  >
                    <div className="text-5xl mb-4">{collection.icon}</div>
                    <div className="text-2xl font-normal mb-3 text-gray-900 dark:text-white">{collection.title}</div>
                    <div className="text-text-secondary text-sm">{collection.count}</div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Architecture Section */}
          {activeSection === 'tech' && (
            <section className="max-w-[1400px] mx-auto px-10 py-24">
              <div className="text-center mb-12">
                <h2 className="text-5xl font-light mb-4 text-gray-900 dark:text-white">Architecture</h2>
                <p className="text-text-secondary text-lg">Production-grade AI search powered by AWS</p>
              </div>
              
              {/* Architecture Diagram */}
              <div className="mb-16 card p-8">
                <img 
                  src="/architecture.png" 
                  alt="Architecture Diagram" 
                  className="w-full h-auto rounded-2xl"
                  style={{ maxHeight: '600px', objectFit: 'contain' }}
                />
              </div>

              {/* Technology Stack - Smaller Tiles */}
              <div className="text-center mb-8">
                <h3 className="text-3xl font-light text-gray-900 dark:text-white mb-2">Technology Stack</h3>
                <p className="text-text-secondary text-sm">Powered by AWS's most advanced AI and database services</p>
              </div>
              <div className="grid grid-cols-4 gap-6 mb-12">
                {[
                  { title: 'Aurora PostgreSQL', icon: '🗄️' },
                  { title: 'Amazon Bedrock', icon: '🤖' },
                  { title: 'pgvector', icon: '🔍' },
                  { title: 'AWS Strands SDK', icon: '🔗' },
                ].map((tech, index) => (
                  <div key={index} className="card p-6 text-center">
                    <div className="text-4xl mb-3">{tech.icon}</div>
                    <h4 className="text-lg font-normal text-gray-900 dark:text-white">{tech.title}</h4>
                  </div>
                ))}
              </div>
              <div className="text-center">
                <p className="text-xs text-text-secondary">
                  © 2025 Shayon Sanyal | DAT406: Build agentic AI-powered search with Amazon Aurora | AWS re:Invent 2025
                </p>
              </div>
            </section>
          )}
        </main>

        {/* AI Assistant */}
        <AIAssistant />

        {/* Product Modal */}
        {selectedProduct && (
          <ProductModal
            product={selectedProduct}
            onClose={() => setSelectedProduct(null)}
          />
        )}
      </div>
    </ThemeContext.Provider>
  )
}

export default App