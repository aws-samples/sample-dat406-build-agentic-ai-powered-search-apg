/**
 * Client-side helpers for the live Tools surface.
 */
import type { Tool } from '../../types';

export type ToolFilter = 'all' | 'shipped' | 'exercise' | 'read' | 'write';

export const DISCOVERY_EXAMPLES: Array<{ label: string; query: string }> = [
  { label: 'Catalog search', query: 'find products matching customer preferences' },
  { label: 'Hybrid + rerank', query: 'hybrid search with rerank for thoughtful gifts' },
  { label: 'Compare products', query: 'compare two products side by side' },
  { label: 'Price bands', query: 'price range and value picks for linen shirts' },
  { label: 'Warehouse stock', query: 'check floor stock at Brooklyn warehouse' },
  { label: 'Process return', query: 'start a product return with audit trail' },
];

export function filterTools(tools: Tool[], filter: ToolFilter): Tool[] {
  switch (filter) {
    case 'shipped':
      return tools.filter((t) => t.status === 'shipped');
    case 'exercise':
      return tools.filter((t) => t.status === 'exercise');
    case 'read':
      return tools.filter((t) => t.mutationType === 'read');
    case 'write':
      return tools.filter((t) => t.mutationType === 'write');
    default:
      return tools;
  }
}

export function discoveryQueryForTool(tool: Tool): string {
  const presets: Record<string, string> = {
    search_products: 'find products matching customer preferences',
    search_products_hybrid: 'hybrid search with rerank for gift-ready pieces',
    browse_category: 'browse the weekend edit collection',
    compare_products: 'compare two products side by side',
    get_related_products: 'pieces that pair with this product',
    get_trending_products: 'what is trending in the catalog right now',
    get_price_analysis: 'price range for linen shirts',
    check_inventory: 'is this sku on the floor at Brooklyn warehouse',
    restock_inventory: 'restock low inventory on the shelf',
    initiate_return: 'process a customer return with audit',
    get_customer_preferences: 'what do you remember about this shopper',
    get_audit_trail: 'show me the tool audit receipt for this call',
  };
  return presets[tool.functionName] ?? tool.description;
}
