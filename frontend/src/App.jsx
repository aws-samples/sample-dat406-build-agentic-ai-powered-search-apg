import React, { useState, useEffect } from 'react'
import './App.css'

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
  { name: 'Sony A7R V', price: '$3,899', icon: '📷', desc: '61MP Full Frame' },
  { name: 'LG OLED C3 65"', price: '$1,896', icon: '📺', desc: 'Gaming Optimized' }
]

// Product database
const productDatabase = [
  // Headphones
  { id: 'B001', name: 'Sony WH-1000XM5 Headphones', category: 'Headphones', price: 399, icon: '🎧', keywords: ['sony', 'headphones', 'noise cancelling', 'wireless', 'premium', 'anc'] },
  { id: 'B002', name: 'Apple AirPods Pro 2', category: 'Headphones', price: 249, icon: '🎧', keywords: ['apple', 'airpods', 'earbuds', 'wireless', 'noise cancelling'] },
  { id: 'B003', name: 'Bose QuietComfort Ultra', category: 'Headphones', price: 429, icon: '🎧', keywords: ['bose', 'headphones', 'quietcomfort', 'noise cancelling', 'premium'] },
  { id: 'B004', name: 'Sennheiser Momentum 4', category: 'Headphones', price: 379, icon: '🎧', keywords: ['sennheiser', 'momentum', 'headphones', 'audiophile', 'wireless'] },
  { id: 'B005', name: 'B&O Beoplay H95', category: 'Headphones', price: 899, icon: '🎧', keywords: ['bang olufsen', 'luxury', 'headphones', 'premium', 'designer'] },
  { id: 'B006', name: 'Focal Bathys', category: 'Headphones', price: 799, icon: '🎧', keywords: ['focal', 'audiophile', 'headphones', 'high-end', 'wireless'] },
  { id: 'B007', name: 'AirPods Max', category: 'Headphones', price: 549, icon: '🎧', keywords: ['apple', 'airpods max', 'headphones', 'premium', 'spatial audio'] },
  { id: 'B008', name: 'Beats Studio Pro', category: 'Headphones', price: 349, icon: '🎧', keywords: ['beats', 'studio', 'headphones', 'bass', 'wireless'] },
  
  // Laptops
  { id: 'L001', name: 'MacBook Pro 16" M3 Max', category: 'Laptops', price: 3999, icon: '💻', keywords: ['macbook', 'laptop', 'apple', 'm3', 'pro', 'professional'] },
  { id: 'L002', name: 'MacBook Air 15" M2', category: 'Laptops', price: 1299, icon: '💻', keywords: ['macbook', 'air', 'laptop', 'apple', 'm2', 'ultrabook'] },
  { id: 'L003', name: 'Dell XPS 15 OLED', category: 'Laptops', price: 2499, icon: '💻', keywords: ['dell', 'xps', 'laptop', 'oled', 'windows', 'creator'] },
  { id: 'L004', name: 'ThinkPad X1 Carbon', category: 'Laptops', price: 1899, icon: '💻', keywords: ['lenovo', 'thinkpad', 'business', 'laptop', 'carbon'] },
  
  // Phones
  { id: 'P001', name: 'iPhone 15 Pro Max', category: 'Phones', price: 1199, icon: '📱', keywords: ['iphone', 'apple', 'phone', 'pro max', 'titanium', 'flagship'] },
  { id: 'P002', name: 'Samsung Galaxy S24 Ultra', category: 'Phones', price: 1299, icon: '📱', keywords: ['samsung', 'galaxy', 'android', 'phone', 's24', 'ultra'] },
  { id: 'P003', name: 'Google Pixel 8 Pro', category: 'Phones', price: 999, icon: '📱', keywords: ['google', 'pixel', 'android', 'phone', 'camera', 'ai'] },
  
  // Other categories...
  { id: 'W001', name: 'Apple Watch Ultra 2', category: 'Watches', price: 799, icon: '⌚', keywords: ['apple watch', 'ultra', 'smartwatch', 'fitness', 'adventure'] },
  { id: 'C001', name: 'Sony A7R V', category: 'Cameras', price: 3899, icon: '📷', keywords: ['sony', 'a7r', 'camera', 'mirrorless', 'professional', '61mp'] },
  { id: 'V001', name: 'Apple Vision Pro', category: 'AR/VR', price: 3499, icon: '🥽', keywords: ['apple', 'vision pro', 'ar', 'vr', 'spatial', 'mixed reality'] },
]

// Collections data
const collections = [
  { icon: '🎧', title: 'Premium Audio', count: '247 products • Updated daily' },
  { icon: '💻', title: 'Pro Workstations', count: '183 products • Curated by AI' },
  { icon: '📱', title: 'Flagship Phones', count: '94 products • Trending now' },
  { icon: '⌚', title: 'Smart Wearables', count: '156 products • Health focused' },
  { icon: '📷', title: 'Creator Gear', count: '312 products • Professional grade' },
  { icon: '🎮', title: 'Gaming Elite', count: '428 products • Performance optimized' },
]

function App() {
  const [activeSection, setActiveSection] = useState('shop')
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [showSearch, setShowSearch] = useState(false)
  const [currentProduct, setCurrentProduct] = useState(0)
  const [showProductModal, setShowProductModal] = useState(false)
  const [selectedProduct, setSelectedProduct] = useState(null)
  const [quantity, setQuantity] = useState(1)
  const [cart, setCart] = useState([])
  const [showCart, setShowCart] = useState(false)
  const [showChat, setShowChat] = useState(false)
  const [chatMessages, setChatMessages] = useState([
    {
      type: 'assistant',
      text: '👋 Welcome to Aurora AI! I\'m your premium shopping assistant powered by Amazon Aurora PostgreSQL with pgvector and Amazon Bedrock. I can help you find products, compare options, and provide personalized recommendations using advanced semantic search.'
    }
  ])
  const [chatInput, setChatInput] = useState('')

  // Rotate showcase products
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentProduct((prev) => (prev + 1) % premiumProducts.length)
    }, 3500)
    return () => clearInterval(interval)
  }, [])

  // Calculate similarity score
  const calculateSimilarity = (query, product) => {
    const searchTerms = query.toLowerCase().split(' ').filter(term => term.length > 2)
    let matches = 0
    let totalTerms = searchTerms.length
    
    searchTerms.forEach(term => {
      if (product.name.toLowerCase().includes(term)) {
        matches += 2
      }
      product.keywords?.forEach(keyword => {
        if (keyword.includes(term)) {
          matches += 1
        }
      })
    })
    
    let similarity = totalTerms > 0 ? (matches / (totalTerms * 2)) : 0
    similarity = Math.min(0.99, similarity + (Math.random() * 0.15))
    
    if (searchTerms.includes(product.category.toLowerCase())) {
      similarity = Math.min(0.99, similarity + 0.2)
    }
    
    return Math.max(0.15, similarity)
  }

  // Handle search
  const handleSearch = (e) => {
    const query = e.target.value
    setSearchQuery(query)
    
    if (query.length > 0) {
      const results = productDatabase
        .map(product => ({
          ...product,
          similarity: calculateSimilarity(query, product)
        }))
        .sort((a, b) => b.similarity - a.similarity)
        .slice(0, 12)
      
      setSearchResults(results)
      setShowSearch(true)
    } else {
      setShowSearch(false)
    }
  }

  // Open product modal
  const openProductModal = (productId) => {
    const product = productDatabase.find(p => p.id === productId)
    if (product) {
      setSelectedProduct(product)
      setQuantity(1)
      setShowProductModal(true)
    }
  }

  // Add to cart
  const addToCart = () => {
    if (selectedProduct) {
      setCart([...cart, { ...selectedProduct, quantity }])
      setShowCart(true)
      setShowProductModal(false)
      setTimeout(() => setShowCart(false), 3000)
    }
  }

  // Buy now
  const buyNow = () => {
    if (selectedProduct) {
      alert(`🎉 Checkout Successful!\n\nOrder Summary:\n• ${quantity} x ${selectedProduct.name}\n• Total: $${(selectedProduct.price * quantity).toLocaleString()}\n\nThank you for shopping with Blaize Bazaar!\nYour order will be delivered by our AI-optimized logistics network.`)
      setShowProductModal(false)
    }
  }

  // Send chat message
  const sendChatMessage = () => {
    if (chatInput.trim()) {
      setChatMessages([...chatMessages, { type: 'user', text: chatInput }])
      setChatInput('')
      
      // Simulate AI response
      setTimeout(() => {
        const responses = [
          'I\'ve analyzed your query using Aurora PostgreSQL with pgvector. Based on semantic similarity, I found 3 perfect matches for you.',
          'Using our RAG pipeline powered by Amazon Bedrock, I can see that the Sony WH-1000XM5 matches your requirements with 97% confidence.',
          'Our multi-agent system has coordinated inventory, pricing, and recommendation agents to find the best deal for you.',
          'The MCP protocol integration allows me to access real-time inventory across all warehouses. The product you\'re interested in is available with same-day delivery.'
        ]
        setChatMessages(prev => [...prev, { 
          type: 'assistant', 
          text: responses[Math.floor(Math.random() * responses.length)] 
        }])
      }, 1500)
    }
  }

  // Get cart totals
  const cartTotal = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0)
  const cartItems = cart.reduce((sum, item) => sum + item.quantity, 0)

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <nav className="nav">
          <div className="logo">Blaize Bazaar</div>
          
          <div className="nav-center">
            <a 
              className={`nav-link ${activeSection === 'shop' ? 'active' : ''}`}
              onClick={() => setActiveSection('shop')}
            >
              Shop
            </a>
            <a 
              className={`nav-link ${activeSection === 'collections' ? 'active' : ''}`}
              onClick={() => setActiveSection('collections')}
            >
              Collections
            </a>
            <a 
              className={`nav-link ${activeSection === 'about' ? 'active' : ''}`}
              onClick={() => setActiveSection('about')}
            >
              About
            </a>
          </div>

          <div className="nav-right">
            <div className="search-bar">
              <input 
                type="text" 
                className="search-input" 
                placeholder="Search products..."
                value={searchQuery}
                onChange={handleSearch}
              />
            </div>
          </div>
        </nav>
      </header>

      {/* Search Results Overlay */}
      {showSearch && (
        <div className="search-overlay active">
          <div className="search-header">
            <div className="search-query">
              Searching for: <span>{searchQuery}</span>
            </div>
            <div className="search-metrics">
              <div>⚡ {(8 + Math.random() * 8).toFixed(1)}ms</div>
              <div>🔍 {searchResults.length} results</div>
              <div>🧠 pgvector similarity</div>
            </div>
          </div>
          <div className="search-results">
            {searchResults.map(product => (
              <div 
                key={product.id} 
                className="search-result-card"
                onClick={() => openProductModal(product.id)}
              >
                <div className="similarity-badge">{(product.similarity * 100).toFixed(0)}%</div>
                <div className="result-header">
                  <div className="result-icon">{product.icon}</div>
                  <div className="result-info">
                    <div className="result-name">{product.name}</div>
                    <div className="result-category">{product.category}</div>
                  </div>
                </div>
                <div className="result-footer">
                  <div className="result-price">${product.price.toLocaleString()}</div>
                  <div className="result-meta">
                    <span>⭐ 4.{Math.floor(5 + Math.random() * 4)}</span>
                    <span>{Math.floor(100 + Math.random() * 900)} reviews</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Product Modal */}
      {showProductModal && selectedProduct && (
        <div className="product-modal active">
          <div className="modal-content">
            <div className="modal-close" onClick={() => setShowProductModal(false)}>✕</div>
            
            <div className="product-detail">
              <div className="product-gallery">
                <div className="main-image">
                  <span style={{ fontSize: '120px' }}>{selectedProduct.icon}</span>
                </div>
                <div className="image-thumbnails">
                  <div className="thumbnail">📐</div>
                  <div className="thumbnail">📏</div>
                  <div className="thumbnail">📦</div>
                  <div className="thumbnail">🎁</div>
                </div>
              </div>
              
              <div className="product-details">
                <h2 className="product-title">{selectedProduct.name}</h2>
                
                <div className="product-rating">
                  <span className="stars">⭐⭐⭐⭐⭐</span>
                  <span className="rating-text">4.8 out of 5 (2,451 reviews)</span>
                </div>
                
                <div className="product-price-section">
                  <span className="current-price">${selectedProduct.price}</span>
                  <span className="original-price">${Math.floor(selectedProduct.price * 1.25)}</span>
                  <span className="discount-badge">20% OFF</span>
                </div>
                
                <div className="product-options">
                  <div className="quantity-selector">
                    <span style={{ color: 'var(--text-secondary)' }}>Quantity:</span>
                    <div className="quantity-btn" onClick={() => setQuantity(Math.max(1, quantity - 1))}>−</div>
                    <span className="quantity-display">{quantity}</span>
                    <div className="quantity-btn" onClick={() => setQuantity(quantity + 1)}>+</div>
                  </div>
                </div>
                
                <div className="action-buttons">
                  <button className="btn-add-cart" onClick={addToCart}>🛒 Add to Cart</button>
                  <button className="btn-buy-now" onClick={buyNow}>⚡ Buy Now</button>
                </div>
                
                <div className="product-features">
                  <h3 style={{ fontSize: '16px', marginBottom: '12px' }}>Key Features</h3>
                  <div className="features-list">
                    <div className="feature-item">
                      <span className="feature-icon">✓</span>
                      <span>Premium materials and build quality</span>
                    </div>
                    <div className="feature-item">
                      <span className="feature-icon">✓</span>
                      <span>AI-powered recommendations</span>
                    </div>
                    <div className="feature-item">
                      <span className="feature-icon">✓</span>
                      <span>Free shipping & returns</span>
                    </div>
                    <div className="feature-item">
                      <span className="feature-icon">✓</span>
                      <span>2-year warranty included</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            {/* Recommendations */}
            <div className="recommendations-section">
              <div className="recommendations-header">
                <h3 className="recommendations-title">Items You May Like</h3>
                <div className="ai-powered-badge">
                  🤖 Powered by Aurora AI & pgvector
                </div>
              </div>
              <div className="recommendations-grid">
                {productDatabase
                  .filter(p => p.id !== selectedProduct.id && p.category === selectedProduct.category)
                  .slice(0, 6)
                  .map(product => (
                    <div 
                      key={product.id} 
                      className="recommendation-card"
                      onClick={() => openProductModal(product.id)}
                    >
                      <span className="match-score">{(75 + Math.random() * 20).toFixed(0)}% match</span>
                      <div className="rec-product-icon">{product.icon}</div>
                      <div className="rec-product-name">{product.name}</div>
                      <div className="rec-product-price">${product.price.toLocaleString()}</div>
                    </div>
                  ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Cart Summary */}
      {showCart && (
        <div className="cart-summary active">
          <div className="cart-info">
            <span className="cart-count">{cartItems} items in cart</span>
            <span className="cart-total">${cartTotal.toLocaleString()}</span>
          </div>
          <button className="btn-checkout">Checkout</button>
        </div>
      )}

      {/* AI Chat Window */}
      {showChat && (
        <div className="ai-chat-window active">
          <div className="chat-header">
            <div className="chat-header-info">
              <div className="aurora-ai-avatar">🤖</div>
              <div>
                <div style={{ fontWeight: 500, fontSize: '16px' }}>Aurora AI Assistant</div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Powered by Aurora PostgreSQL + Bedrock</div>
              </div>
            </div>
            <div style={{ cursor: 'pointer', fontSize: '20px' }} onClick={() => setShowChat(false)}>✕</div>
          </div>
          <div className="chat-messages">
            {chatMessages.map((msg, idx) => (
              <div key={idx} className={`chat-message ${msg.type}`}>
                {msg.text}
              </div>
            ))}
          </div>
          <div className="chat-input-container">
            <input 
              type="text" 
              className="chat-input" 
              placeholder="Ask me anything about our products..."
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && sendChatMessage()}
            />
            <button className="chat-send-btn" onClick={sendChatMessage}>Send</button>
          </div>
        </div>
      )}

      {/* AI Assistant Bubble */}
      <div className="ai-assistant-bubble" onClick={() => setShowChat(!showChat)}>
        <div className="ai-assistant-icon">🤖</div>
        <div className="aurora-ai-badge">Aurora AI</div>
      </div>

      {/* Main Content */}
      <main>
        {/* Shop Section */}
        {activeSection === 'shop' && (
          <section className="hero">
            <div className="hero-content">
              <div className="hero-text">
                <h1>
                  Welcome to<br/>
                  <span className="gradient-text">Blaize Bazaar</span>
                </h1>
                <div className="subtitle">Shop Smart with AI-Powered Search</div>
                <p>
                  Experience intelligent product discovery powered by Aurora PostgreSQL with pgvector, 
                  Amazon Bedrock, and AWS Strands SDK. Real-time semantic search meets premium shopping.
                </p>
                <div className="hero-buttons">
                  <button className="btn-primary" onClick={() => setShowChat(true)}>Chat with Aurora AI</button>
                  <button className="btn-secondary" onClick={() => setActiveSection('collections')}>Browse Collections</button>
                </div>
              </div>
              <div className="hero-image">
                <div className="product-showcase">
                  <div className="showcase-content">
                    <div className="product-img">{premiumProducts[currentProduct].icon}</div>
                    <h3>{premiumProducts[currentProduct].name}</h3>
                    <div className="product-price">{premiumProducts[currentProduct].price}</div>
                    <p>{premiumProducts[currentProduct].desc}</p>
                  </div>
                </div>
              </div>
            </div>
          </section>
        )}

        {/* Collections Section */}
        {activeSection === 'collections' && (
          <section className="collections-section active">
            <div style={{ textAlign: 'center', marginBottom: '48px' }}>
              <h2 style={{ fontSize: '48px', fontWeight: 300, marginBottom: '16px' }}>Curated Collections</h2>
              <p style={{ color: 'var(--text-secondary)', fontSize: '18px' }}>AI-powered collections tailored to your preferences</p>
            </div>
            <div className="collections-grid">
              {collections.map((collection, idx) => (
                <div key={idx} className="collection-card">
                  <div className="collection-icon">{collection.icon}</div>
                  <div className="collection-title">{collection.title}</div>
                  <div className="collection-count">{collection.count}</div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* About Section */}
        {activeSection === 'about' && (
          <section className="about-section active">
            <div className="about-content">
              <h2 className="about-title">About Blaize Bazaar</h2>
              <p className="about-text">
                Blaize Bazaar exemplifies production-grade vector search architecture and autonomous agent orchestration 
                deployed at enterprise scale. The platform implements semantic search using cosine similarity 
                calculations on high-dimensional embeddings, retrieval-augmented generation (RAG) patterns with Amazon Bedrock, 
                and multi-agent coordination through the AWS Strands SDK.
              </p>
              <p className="about-text">
                The architecture leverages pgvector's HNSW indexing for approximate nearest neighbor search across 
                millions of product embeddings, while RAG pipelines enhance query responses with contextual data retrieval. 
                Agent communication follows the Model Context Protocol (MCP) specification for standardized tool use 
                and inter-agent messaging. This implementation showcases practical patterns for building 
                production-grade AI applications on managed database infrastructure.
              </p>
              <div className="team-info">
                <div className="team-logo">🚀</div>
                <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid rgba(255, 255, 255, 0.1)', fontSize: '13px', color: 'var(--text-secondary)' }}>
                  © 2025 Shayon Sanyal. All rights reserved.<br/>
                  DAT406 | Build agentic AI-powered search with Amazon Aurora and Amazon RDS | AWS re:Invent 2025
                </div>
              </div>
            </div>
          </section>
        )}
      </main>
    </div>
  )
}

export default App