/**
 * Product Card Component - Shopping Cart Style
 * Displays product with Add to Cart functionality
 */
import { ShoppingCart, Star } from 'lucide-react'

interface ProductCardProps {
  product: {
    id: string
    name: string
    price: number
    image: string
    category?: string
    rating?: number
    reviews?: number
  }
  onAddToCart?: (product: any) => void
  highlighted?: boolean
  aiRecommended?: boolean
}

const ProductCard = ({ product, onAddToCart, aiRecommended = true }: ProductCardProps) => {
  const isImageUrl = product.image.startsWith('http')
  const productUrl = `https://amazon.com/dp/${product.id}`
  
  return (
    <div
      className="rounded-xl p-3 flex items-center gap-3 animate-slideUp transition-all duration-300 hover:scale-[1.02] group relative"
      style={{
        background: 'rgba(30, 30, 40, 0.4)',
        border: '1px solid rgba(106, 27, 154, 0.2)',
        transition: 'all 0.3s ease'
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = 'linear-gradient(135deg, rgba(186, 104, 200, 0.15) 0%, rgba(106, 27, 154, 0.1) 100%)'
        e.currentTarget.style.borderColor = 'rgba(186, 104, 200, 0.5)'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = 'rgba(30, 30, 40, 0.4)'
        e.currentTarget.style.borderColor = 'rgba(106, 27, 154, 0.2)'
      }}
    >
      {/* AI Badge */}
      {aiRecommended && (
        <div className="absolute top-1 right-1 px-2 py-0.5 rounded-full bg-purple-500/20 border border-purple-500/30 backdrop-blur-sm z-10">
          <span className="text-[9px] text-purple-300 font-medium">✨ AI Pick</span>
        </div>
      )}
      
      {/* Product Image - Clickable */}
      <a
        href={productUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="w-14 h-14 rounded-lg flex items-center justify-center flex-shrink-0 overflow-hidden hover:opacity-80 transition-opacity"
        style={{ background: 'rgba(0, 0, 0, 0.3)' }}
        onClick={(e) => e.stopPropagation()}
      >
        {isImageUrl ? (
          <img src={product.image} alt={product.name} className="w-full h-full object-cover" />
        ) : (
          <span className="text-2xl">{product.image}</span>
        )}
      </a>

      {/* Product Info - Clickable */}
      <a
        href={productUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="flex-1 min-w-0 hover:opacity-80 transition-opacity"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="font-medium text-xs mb-1 text-text-primary line-clamp-2">
          {product.name}
        </div>
        
        {/* Rating & Price Row */}
        <div className="flex items-center gap-2 mb-1">
          {product.rating && (
            <div className="flex items-center gap-1">
              <Star className="h-3 w-3 text-yellow-400 fill-current" />
              <span className="text-xs text-text-secondary">
                {product.rating}
              </span>
            </div>
          )}
          <div className="text-accent-light font-bold text-sm">
            ${product.price}
          </div>
        </div>
        
        {/* Category */}
        {product.category && (
          <div className="text-xs text-text-secondary">
            {product.category}
          </div>
        )}
      </a>

      {/* Add to Cart Button */}
      <button
        onClick={() => onAddToCart?.(product)}
        className="px-3 py-2 rounded-lg font-semibold text-xs transition-all duration-300 hover:scale-105 flex items-center gap-1 flex-shrink-0"
        style={{
          background: 'linear-gradient(135deg, #6a1b9a 0%, #ba68c8 100%)',
          color: 'white'
        }}
      >
        <ShoppingCart className="h-3 w-3" />
        Add
      </button>
    </div>
  )
}

export default ProductCard