/**
 * Premium Product Card Component - Apple-inspired Design
 * Enhanced with smooth animations, gradients, and refined spacing
 * DARK MODE READY
 */
import { Star, ShoppingCart, TrendingUp, Sparkles } from 'lucide-react'
import { ProductSearchResult } from '../services/types'

interface ProductCardProps {
  product: ProductSearchResult
  onClick?: () => void
}

const ProductCard = ({ product, onClick }: ProductCardProps) => {
  const {
    product_description,
    imgurl,
    stars,
    reviews,
    price,
    isbestseller,
    boughtinlastmonth,
    quantity,
    similarity_score,
  } = product

  const formattedPrice = price ? `$${price.toFixed(2)}` : 'N/A'
  const matchPercentage = similarity_score
    ? `${(similarity_score * 100).toFixed(0)}%`
    : ''

  const stockStatus =
    quantity === undefined || quantity === null
      ? 'Unknown'
      : quantity === 0
      ? 'Out of Stock'
      : quantity < 10
      ? `Only ${quantity} left`
      : 'In Stock'

  const stockColor =
    quantity === 0
      ? 'text-red-500 dark:text-red-400'
      : quantity !== undefined && quantity < 10
      ? 'text-amber-500 dark:text-amber-400'
      : 'text-emerald-500 dark:text-emerald-400'

  return (
    <div
      onClick={onClick}
      className="group relative bg-white dark:bg-gray-800 rounded-[20px] overflow-hidden cursor-pointer 
                 transition-all duration-500 ease-out
                 hover:scale-[1.02] hover:shadow-2xl
                 border border-gray-100/50 dark:border-gray-700/50"
      style={{
        boxShadow: '0 4px 24px rgba(0, 0, 0, 0.06)',
      }}
    >
      {/* Hover Gradient Overlay */}
      <div className="absolute inset-0 bg-gradient-to-br from-purple-500/0 via-purple-500/0 to-blue-500/0
                      group-hover:from-purple-500/5 group-hover:via-purple-500/3 group-hover:to-blue-500/5
                      dark:group-hover:from-purple-500/10 dark:group-hover:via-purple-500/5 dark:group-hover:to-blue-500/10
                      transition-all duration-700 pointer-events-none" />

      {/* Product Image Container */}
      <div className="relative aspect-square overflow-hidden 
                    bg-gradient-to-br from-gray-50 to-gray-100 
                    dark:from-gray-700 dark:to-gray-600">
        {imgurl ? (
          <img
            src={imgurl}
            alt={product_description}
            className="w-full h-full object-cover transform transition-transform duration-700 
                       group-hover:scale-110"
            onError={(e) => {
              e.currentTarget.src = 'https://via.placeholder.com/400x400?text=No+Image'
            }}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <ShoppingCart className="h-20 w-20 text-gray-300 dark:text-gray-600" strokeWidth={1.5} />
          </div>
        )}

        {/* Top Badges */}
        <div className="absolute top-4 left-4 right-4 flex items-start justify-between">
          {/* Match Score */}
          {similarity_score && (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full
                          bg-white/95 dark:bg-gray-800/95 backdrop-blur-xl shadow-lg
                          border border-purple-100/50 dark:border-purple-900/50">
              <Sparkles className="h-3.5 w-3.5 text-purple-600 dark:text-purple-400" strokeWidth={2} />
              <span className="text-xs font-semibold text-purple-600 dark:text-purple-400">
                {matchPercentage} match
              </span>
            </div>
          )}

          {/* Bestseller Badge */}
          {isbestseller && (
            <div className="px-3 py-1.5 rounded-full
                          bg-gradient-to-r from-amber-400 to-orange-500
                          shadow-lg">
              <span className="text-xs font-bold text-white tracking-wide">
                BESTSELLER
              </span>
            </div>
          )}
        </div>

        {/* Stock Badge - Bottom */}
        <div className="absolute bottom-4 right-4">
          <div className={`px-3 py-1.5 rounded-full backdrop-blur-xl
                         bg-white/95 dark:bg-gray-800/95 shadow-lg 
                         border border-gray-100/50 dark:border-gray-700/50
                         ${stockColor} text-xs font-semibold`}>
            {stockStatus}
          </div>
        </div>
      </div>

      {/* Product Details */}
      <div className="p-5 space-y-3">
        {/* Title */}
        <h3 className="text-sm font-medium text-gray-900 dark:text-white line-clamp-2 leading-relaxed
                       transition-colors duration-300 
                       group-hover:text-purple-600 dark:group-hover:text-purple-400"
            style={{ minHeight: '2.5rem' }}>
          {product_description}
        </h3>

        {/* Rating */}
        {stars !== undefined && stars !== null && (
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1">
              {[...Array(5)].map((_, i) => (
                <Star
                  key={i}
                  className={`h-3.5 w-3.5 transition-all duration-300 ${
                    i < Math.floor(stars)
                      ? 'text-amber-400 fill-amber-400'
                      : 'text-gray-200 dark:text-gray-600 fill-gray-200 dark:fill-gray-600'
                  }`}
                  strokeWidth={0}
                />
              ))}
            </div>
            <span className="text-sm font-semibold text-gray-900 dark:text-white">
              {stars.toFixed(1)}
            </span>
            {reviews && (
              <span className="text-xs text-gray-500 dark:text-gray-400 font-medium">
                ({reviews.toLocaleString()})
              </span>
            )}
          </div>
        )}

        {/* Price and Popularity */}
        <div className="flex items-end justify-between pt-2 border-t border-gray-100 dark:border-gray-700">
          <div className="space-y-0.5">
            <div className="text-2xl font-bold bg-gradient-to-r from-purple-600 to-blue-600 
                           dark:from-purple-400 dark:to-blue-400
                           bg-clip-text text-transparent">
              {formattedPrice}
            </div>
            {boughtinlastmonth && boughtinlastmonth > 0 && (
              <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
                <TrendingUp className="h-3 w-3" strokeWidth={2} />
                <span className="font-medium">
                  {boughtinlastmonth > 1000 
                    ? `${(boughtinlastmonth / 1000).toFixed(1)}K` 
                    : boughtinlastmonth} sold
                </span>
              </div>
            )}
          </div>

          {/* Add to Cart Button */}
          <button 
            className="p-2.5 rounded-full bg-gradient-to-br from-purple-600 to-blue-600
                       hover:from-purple-700 hover:to-blue-700
                       shadow-lg hover:shadow-xl
                       transform transition-all duration-300 hover:scale-110
                       group/btn"
            onClick={(e) => {
              e.stopPropagation()
              // Add to cart logic
            }}
          >
            <ShoppingCart className="h-4 w-4 text-white" strokeWidth={2} />
          </button>
        </div>
      </div>
    </div>
  )
}

export default ProductCard