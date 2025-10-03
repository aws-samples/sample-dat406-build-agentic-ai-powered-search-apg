/**
 * Premium Product Modal Component - Apple-inspired Design
 * Full-screen modal with smooth animations and glassmorphism
 * DARK MODE READY
 */
import { X, Star, Package, TrendingUp, ExternalLink, ShoppingCart, Heart, Share2 } from 'lucide-react'
import { Product } from '../services/types'

interface ProductModalProps {
  product: Product
  onClose: () => void
}

const ProductModal = ({ product, onClose }: ProductModalProps) => {
  const {
    productId,
    product_description,
    imgurl,
    producturl,
    stars,
    reviews,
    price,
    category_name,
    isbestseller,
    boughtinlastmonth,
    quantity,
  } = product

  const formattedPrice = price ? `$${price.toFixed(2)}` : 'Price not available'

  const stockStatus =
    quantity === undefined || quantity === null
      ? 'Stock status unknown'
      : quantity === 0
      ? 'Out of Stock'
      : quantity < 10
      ? `Only ${quantity} left`
      : `${quantity} in stock`

  const stockColor =
    quantity === 0
      ? 'text-red-500 bg-red-50 dark:text-red-400 dark:bg-red-900/30'
      : quantity !== undefined && quantity < 10
      ? 'text-amber-500 bg-amber-50 dark:text-amber-400 dark:bg-amber-900/30'
      : 'text-emerald-500 bg-emerald-50 dark:text-emerald-400 dark:bg-emerald-900/30'

  return (
    <div
      className="fixed inset-0 z-50 overflow-hidden animate-in fade-in duration-300"
      aria-labelledby="modal-title"
      role="dialog"
      aria-modal="true"
    >
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Modal Container */}
      <div className="flex min-h-full items-center justify-center p-4 sm:p-8">
        <div 
          className="relative bg-white dark:bg-gray-900 rounded-[32px] shadow-2xl w-full max-w-5xl 
                     overflow-hidden animate-in zoom-in-95 slide-in-from-bottom-8 duration-500
                     border border-gray-100 dark:border-gray-700"
          style={{
            maxHeight: 'calc(100vh - 64px)',
            boxShadow: '0 24px 60px rgba(0, 0, 0, 0.2), 0 0 0 1px rgba(0, 0, 0, 0.05)'
          }}
        >
          {/* Close Button */}
          <button
            onClick={onClose}
            className="absolute top-6 right-6 z-10 p-3 rounded-full 
                     bg-white/90 dark:bg-gray-800/90 backdrop-blur-xl shadow-lg hover:shadow-xl
                     border border-gray-100 dark:border-gray-700
                     transition-all duration-300 hover:scale-110 group"
          >
            <X className="h-5 w-5 text-gray-600 dark:text-gray-400 
                         group-hover:text-gray-900 dark:group-hover:text-white" strokeWidth={2} />
          </button>

          {/* Content Container */}
          <div className="overflow-y-auto custom-scrollbar" style={{ maxHeight: 'calc(100vh - 64px)' }}>
            <div className="grid md:grid-cols-2 gap-0">
              {/* Left: Image Section */}
              <div className="relative bg-gradient-to-br from-gray-50 to-gray-100 
                            dark:from-gray-800 dark:to-gray-700 p-12 
                            flex flex-col justify-center min-h-[500px]">
                {/* Bestseller Badge */}
                {isbestseller && (
                  <div className="absolute top-8 left-8 px-4 py-2 rounded-full
                                bg-gradient-to-r from-amber-400 to-orange-500
                                shadow-lg">
                    <span className="text-sm font-bold text-white tracking-wide">
                      ⭐ BESTSELLER
                    </span>
                  </div>
                )}

                {/* Product Image */}
                <div className="aspect-square rounded-3xl overflow-hidden 
                              bg-white dark:bg-gray-900 shadow-lg">
                  {imgurl ? (
                    <img
                      src={imgurl}
                      alt={product_description}
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        const target = e.target as HTMLImageElement
                        target.src = 'https://via.placeholder.com/600x600?text=No+Image'
                      }}
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <Package className="h-32 w-32 text-gray-300 dark:text-gray-600" strokeWidth={1.5} />
                    </div>
                  )}
                </div>

                {/* Stock Badge */}
                <div className={`mt-6 px-5 py-3 rounded-2xl font-semibold text-center ${stockColor}
                               shadow-sm border border-current/10`}>
                  {stockStatus}
                </div>
              </div>

              {/* Right: Details Section */}
              <div className="p-12 flex flex-col bg-white dark:bg-gray-900">
                {/* Product ID */}
                <div className="text-xs text-gray-500 dark:text-gray-400 font-mono mb-4 tracking-wider">
                  SKU: {productId}
                </div>

                {/* Category */}
                {category_name && (
                  <div className="inline-block self-start px-4 py-2 mb-4
                                bg-purple-50 dark:bg-purple-900/30 
                                text-purple-600 dark:text-purple-400 
                                text-sm font-semibold rounded-full
                                border border-purple-100 dark:border-purple-800">
                    {category_name}
                  </div>
                )}

                {/* Title */}
                <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-6 leading-tight">
                  {product_description}
                </h2>

                {/* Rating */}
                {stars !== undefined && stars !== null && (
                  <div className="flex items-center gap-4 mb-6 pb-6 
                                border-b border-gray-100 dark:border-gray-700">
                    <div className="flex items-center gap-1">
                      {[...Array(5)].map((_, i) => (
                        <Star
                          key={i}
                          className={`h-5 w-5 ${
                            i < Math.floor(stars)
                              ? 'text-amber-400 fill-amber-400'
                              : 'text-gray-200 dark:text-gray-600 fill-gray-200 dark:fill-gray-600'
                          }`}
                          strokeWidth={0}
                        />
                      ))}
                    </div>
                    <span className="text-xl font-bold text-gray-900 dark:text-white">
                      {stars.toFixed(1)}
                    </span>
                    {reviews && (
                      <span className="text-gray-500 dark:text-gray-400 font-medium">
                        ({reviews.toLocaleString()} reviews)
                      </span>
                    )}
                  </div>
                )}

                {/* Price */}
                <div className="mb-6">
                  <div className="text-5xl font-bold mb-2
                                bg-gradient-to-r from-purple-600 to-blue-600 
                                dark:from-purple-400 dark:to-blue-400
                                bg-clip-text text-transparent">
                    {formattedPrice}
                  </div>
                  {boughtinlastmonth && boughtinlastmonth > 0 && (
                    <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
                      <TrendingUp className="h-4 w-4" strokeWidth={2} />
                      <span className="text-sm font-medium">
                        {boughtinlastmonth.toLocaleString()} bought in the last month
                      </span>
                    </div>
                  )}
                </div>

                {/* Action Buttons */}
                <div className="flex gap-3 mb-8">
                  <button
                    className="flex-1 flex items-center justify-center gap-2 px-6 py-4 
                             rounded-2xl font-semibold text-white
                             bg-gradient-to-br from-purple-600 to-blue-600
                             hover:from-purple-700 hover:to-blue-700
                             shadow-lg hover:shadow-xl
                             transform transition-all duration-300 hover:scale-[1.02]"
                  >
                    <ShoppingCart className="h-5 w-5" strokeWidth={2} />
                    Add to Cart
                  </button>

                  <button
                    className="p-4 rounded-2xl font-semibold
                             bg-gray-50 dark:bg-gray-800 
                             hover:bg-gray-100 dark:hover:bg-gray-700
                             border border-gray-200 dark:border-gray-700 
                             hover:border-gray-300 dark:hover:border-gray-600
                             transition-all duration-300 hover:scale-105 group"
                  >
                    <Heart className="h-5 w-5 text-gray-600 dark:text-gray-400 
                                    group-hover:text-red-500 dark:group-hover:text-red-400" 
                           strokeWidth={2} />
                  </button>

                  <button
                    className="p-4 rounded-2xl font-semibold
                             bg-gray-50 dark:bg-gray-800 
                             hover:bg-gray-100 dark:hover:bg-gray-700
                             border border-gray-200 dark:border-gray-700 
                             hover:border-gray-300 dark:hover:border-gray-600
                             transition-all duration-300 hover:scale-105"
                  >
                    <Share2 className="h-5 w-5 text-gray-600 dark:text-gray-400" strokeWidth={2} />
                  </button>
                </div>

                {/* External Link */}
                {producturl && (
                  <a
                    href={producturl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center justify-center gap-2 px-6 py-3 
                             rounded-2xl font-medium
                             bg-white dark:bg-gray-800 
                             hover:bg-gray-50 dark:hover:bg-gray-700
                             border border-gray-200 dark:border-gray-700 
                             hover:border-gray-300 dark:hover:border-gray-600
                             text-gray-700 dark:text-gray-300 
                             hover:text-gray-900 dark:hover:text-white
                             transition-all duration-300 group"
                  >
                    <span>View on Amazon</span>
                    <ExternalLink className="h-4 w-4 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 
                                           transition-transform duration-300" strokeWidth={2} />
                  </a>
                )}

                {/* Product Information */}
                <div className="mt-auto pt-8 border-t border-gray-100 dark:border-gray-700">
                  <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">
                    Product Information
                  </h3>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <div className="text-gray-500 dark:text-gray-400 mb-1">Product ID</div>
                      <div className="font-mono font-semibold text-gray-900 dark:text-white">
                        {productId}
                      </div>
                    </div>

                    {category_name && (
                      <div>
                        <div className="text-gray-500 dark:text-gray-400 mb-1">Category</div>
                        <div className="font-semibold text-gray-900 dark:text-white">
                          {category_name}
                        </div>
                      </div>
                    )}

                    <div>
                      <div className="text-gray-500 dark:text-gray-400 mb-1">Availability</div>
                      <div className={`font-semibold ${
                        quantity === 0
                          ? 'text-red-600 dark:text-red-400'
                          : quantity !== undefined && quantity < 10
                          ? 'text-amber-600 dark:text-amber-400'
                          : 'text-emerald-600 dark:text-emerald-400'
                      }`}>
                        {quantity !== undefined ? `${quantity} units` : 'Unknown'}
                      </div>
                    </div>

                    <div>
                      <div className="text-gray-500 dark:text-gray-400 mb-1">Status</div>
                      <div className="font-semibold text-gray-900 dark:text-white">
                        {quantity === 0 ? 'Unavailable' : 'Available'}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <style>{`
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
    </div>
  )
}

export default ProductModal