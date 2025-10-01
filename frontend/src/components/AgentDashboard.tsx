import { useState, useEffect } from 'react';
import { Activity, Package, TrendingDown, RefreshCw } from 'lucide-react';
import { getInventoryAnalysis, getLowStockProducts } from '../services/api';
import type { Product, InventoryAnalysis } from '../services/types';

export default function AgentDashboard() {
  const [analysis, setAnalysis] = useState<InventoryAnalysis | null>(null);
  const [lowStock, setLowStock] = useState<Product[]>([]);
  const [loading, setLoading] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [analysisData, lowStockData] = await Promise.all([
        getInventoryAnalysis(),
        getLowStockProducts(10),
      ]);
      setAnalysis(analysisData);
      setLowStock(lowStockData);
    } catch (error) {
      console.error('Failed to load agent data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Activity className="w-8 h-8 text-primary-600" />
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Agent Dashboard</h2>
            <p className="text-sm text-gray-500">Real-time inventory insights</p>
          </div>
        </div>
        <button
          onClick={loadData}
          disabled={loading}
          className="px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors flex items-center space-x-2"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Stats Grid */}
      {analysis && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-500">Total Inventory Value</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">
                  ${analysis.total_inventory_value.toLocaleString()}
                </p>
              </div>
              <Package className="w-12 h-12 text-green-600" />
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-500">Low Stock Items</p>
                <p className="text-3xl font-bold text-orange-600 mt-2">
                  {analysis.low_stock_products.length}
                </p>
              </div>
              <TrendingDown className="w-12 h-12 text-orange-600" />
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-500">Out of Stock</p>
                <p className="text-3xl font-bold text-red-600 mt-2">
                  {analysis.out_of_stock_products.length}
                </p>
              </div>
              <Package className="w-12 h-12 text-red-600" />
            </div>
          </div>
        </div>
      )}

      {/* Low Stock Products */}
      {lowStock.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Low Stock Alert ({lowStock.length} items)
          </h3>
          <div className="space-y-3">
            {lowStock.slice(0, 5).map((product) => (
              <div
                key={product.productId}
                className="flex items-center justify-between p-3 bg-orange-50 border border-orange-200 rounded-lg"
              >
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-900 line-clamp-1">
                    {product.product_description}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">{product.category_name}</p>
                </div>
                <div className="ml-4 text-right">
                  <p className="text-sm font-bold text-orange-600">{product.quantity} left</p>
                  <p className="text-xs text-gray-500">${product.price.toFixed(2)}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {analysis && analysis.recommendations.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">AI Recommendations</h3>
          <ul className="space-y-2">
            {analysis.recommendations.map((rec, index) => (
              <li key={index} className="flex items-start space-x-2 text-sm text-gray-700">
                <span className="text-primary-600 font-bold">•</span>
                <span>{rec}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}