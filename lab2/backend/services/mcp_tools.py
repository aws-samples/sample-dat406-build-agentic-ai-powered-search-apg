"""
Custom MCP Tools for Aurora PostgreSQL
Extends base MCP with business-specific functionality
"""
from typing import Dict, Any, List
import json


class CustomMCPTools:
    """Custom tools that extend Aurora PostgreSQL MCP"""
    
    def __init__(self, db_service):
        self.db = db_service
    
    async def get_trending_products(self, limit: int = 10) -> Dict[str, Any]:
        """
        Get trending products based on reviews, ratings, and popularity.
        
        Trending score = (reviews * stars) with high-rated products prioritized
        
        Args:
            limit: Number of trending products to return
            
        Returns:
            Dictionary with trending products and metadata
        """
        query = """
            SELECT 
                "productId",
                product_description,
                price,
                stars,
                reviews,
                category_name,
                quantity,
                (reviews * stars) as trending_score
            FROM bedrock_integration.product_catalog
            WHERE quantity > 0 
              AND stars >= 4.0
              AND reviews > 50
            ORDER BY trending_score DESC, stars DESC
            LIMIT %s
        """
        
        results = await self.db.fetch_all(query, limit)
        
        products = [dict(row) for row in results]
        
        return {
            "status": "success",
            "count": len(products),
            "products": products,
            "metadata": {
                "criteria": "reviews * stars, min 4.0 stars, min 50 reviews",
                "limit": limit
            }
        }
    
    async def get_inventory_health(self) -> Dict[str, Any]:
        """
        Get overall inventory health statistics.
        
        Returns:
            Dictionary with inventory health metrics and alerts
        """
        # Get inventory statistics
        stats_query = """
            SELECT 
                COUNT(*) as total_products,
                COUNT(CASE WHEN quantity = 0 THEN 1 END) as out_of_stock,
                COUNT(CASE WHEN quantity > 0 AND quantity < 10 THEN 1 END) as low_stock,
                COUNT(CASE WHEN quantity >= 10 THEN 1 END) as healthy_stock,
                AVG(quantity) as avg_quantity,
                SUM(quantity) as total_quantity
            FROM bedrock_integration.product_catalog
        """
        
        stats = await self.db.fetch_one(stats_query)
        stats_dict = dict(stats)
        
        # Get critical items (low stock with high demand)
        critical_query = """
            SELECT 
                "productId",
                product_description,
                stars,
                reviews,
                quantity
            FROM bedrock_integration.product_catalog
            WHERE quantity < 10
              AND stars >= 4.0
              AND reviews > 100
            ORDER BY quantity ASC, reviews DESC
            LIMIT 10
        """
        
        critical_items = await self.db.fetch_all(critical_query)
        
        # Calculate health score (0-100)
        total = stats_dict['total_products']
        healthy = stats_dict['healthy_stock']
        health_score = int((healthy / total * 100)) if total > 0 else 0
        
        return {
            "status": "success",
            "health_score": health_score,
            "statistics": {
                "total_products": stats_dict['total_products'],
                "out_of_stock": stats_dict['out_of_stock'],
                "low_stock": stats_dict['low_stock'],
                "healthy_stock": stats_dict['healthy_stock'],
                "avg_quantity": float(stats_dict['avg_quantity']) if stats_dict['avg_quantity'] else 0,
                "total_quantity": stats_dict['total_quantity']
            },
            "critical_items": [dict(row) for row in critical_items],
            "alerts": self._generate_inventory_alerts(stats_dict)
        }
    
    async def get_price_statistics(self, category: str = None) -> Dict[str, Any]:
        """
        Get price statistics by category or overall.
        
        Args:
            category: Optional category filter
            
        Returns:
            Dictionary with price statistics and insights
        """
        if category:
            query = """
                SELECT 
                    category_name,
                    COUNT(*) as product_count,
                    MIN(price) as min_price,
                    MAX(price) as max_price,
                    AVG(price) as avg_price,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price) as median_price
                FROM bedrock_integration.product_catalog
                WHERE category_name ILIKE %s
                  AND quantity > 0
                GROUP BY category_name
            """
            results = await self.db.fetch_all(query, f"%{category}%")
        else:
            query = """
                SELECT 
                    category_name,
                    COUNT(*) as product_count,
                    MIN(price) as min_price,
                    MAX(price) as max_price,
                    AVG(price) as avg_price,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price) as median_price
                FROM bedrock_integration.product_catalog
                WHERE quantity > 0
                GROUP BY category_name
                ORDER BY product_count DESC
                LIMIT 10
            """
            results = await self.db.fetch_all(query)
        
        categories = [dict(row) for row in results]
        
        # Calculate overall statistics
        overall_query = """
            SELECT 
                COUNT(*) as total_products,
                MIN(price) as min_price,
                MAX(price) as max_price,
                AVG(price) as avg_price,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price) as median_price
            FROM bedrock_integration.product_catalog
            WHERE quantity > 0
        """
        
        overall = await self.db.fetch_one(overall_query)
        overall_dict = dict(overall)
        
        return {
            "status": "success",
            "overall": {
                "total_products": overall_dict['total_products'],
                "min_price": float(overall_dict['min_price']) if overall_dict['min_price'] else 0,
                "max_price": float(overall_dict['max_price']) if overall_dict['max_price'] else 0,
                "avg_price": float(overall_dict['avg_price']) if overall_dict['avg_price'] else 0,
                "median_price": float(overall_dict['median_price']) if overall_dict['median_price'] else 0
            },
            "by_category": categories,
            "filter": category if category else "all"
        }
    
    async def restock_product(self, product_id: str, quantity: int) -> Dict[str, Any]:
        """
        Add stock to a product.
        
        Args:
            product_id: Product ID to restock
            quantity: Quantity to add
            
        Returns:
            Dictionary with restock confirmation
        """
        # Get current product info
        product_query = """
            SELECT "productId", product_description, quantity
            FROM bedrock_integration.product_catalog
            WHERE "productId" = %s
        """
        
        product = await self.db.fetch_one(product_query, product_id)
        
        if not product:
            return {
                "status": "error",
                "message": f"Product {product_id} not found"
            }
        
        old_quantity = product['quantity']
        new_quantity = old_quantity + quantity
        
        # Update quantity
        update_query = """
            UPDATE bedrock_integration.product_catalog
            SET quantity = quantity + %s
            WHERE "productId" = %s
        """
        
        await self.db.execute_query(update_query, quantity, product_id)
        
        return {
            "status": "success",
            "product_id": product_id,
            "product_name": product['product_description'],
            "old_quantity": old_quantity,
            "added_quantity": quantity,
            "new_quantity": new_quantity,
            "message": f"✅ Added {quantity} units to {product['product_description']}"
        }
    
    async def list_custom_tools(self) -> Dict[str, Any]:
        """
        List all available custom MCP tools with descriptions.
        
        Returns:
            Dictionary with tool information
        """
        tools = [
            {
                "name": "get_trending_products",
                "description": "Get trending products based on reviews and ratings",
                "parameters": {
                    "limit": "Number of products to return (default: 10)"
                },
                "returns": "List of trending products with scores"
            },
            {
                "name": "get_inventory_health",
                "description": "Get overall inventory health statistics and alerts",
                "parameters": {},
                "returns": "Health score, statistics, and critical items"
            },
            {
                "name": "get_price_statistics",
                "description": "Get price statistics by category or overall",
                "parameters": {
                    "category": "Optional category filter"
                },
                "returns": "Price statistics by category"
            },
            {
                "name": "restock_product",
                "description": "Add stock quantity to a product",
                "parameters": {
                    "product_id": "Product ID to restock",
                    "quantity": "Quantity to add"
                },
                "returns": "Restock confirmation with old and new quantities"
            },
            {
                "name": "list_custom_tools",
                "description": "List all available custom MCP tools",
                "parameters": {},
                "returns": "Tool information and descriptions"
            }
        ]
        
        return {
            "status": "success",
            "tool_count": len(tools),
            "tools": tools,
            "base_mcp_tools": ["run_query", "get_schema"],
            "note": "These custom tools extend the base Aurora PostgreSQL MCP"
        }
    
    def _generate_inventory_alerts(self, stats: Dict) -> List[str]:
        """Generate inventory alerts based on statistics"""
        alerts = []
        
        if stats['out_of_stock'] > 0:
            alerts.append(f"🚨 {stats['out_of_stock']} products out of stock")
        
        if stats['low_stock'] > 100:
            alerts.append(f"⚠️ {stats['low_stock']} products low stock (<10 units)")
        elif stats['low_stock'] > 0:
            alerts.append(f"⚠️ {stats['low_stock']} products need monitoring")
        
        if not alerts:
            alerts.append("✅ Inventory healthy")
        
        return alerts
