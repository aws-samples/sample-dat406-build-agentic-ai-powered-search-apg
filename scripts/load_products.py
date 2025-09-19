#!/usr/bin/env python3
"""
Load Amazon products from CSV into Aurora PostgreSQL with pgvector embeddings
Using psycopg3 (from Lambda layer) and updated model IDs for us-west-2
"""

import os
import csv
import json
import boto3
import pandas as pd
import numpy as np
from typing import List, Dict
import logging
import sys

# Use psycopg3 (from the Lambda layer)
try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    # Fallback to psycopg2 for local testing
    import psycopg2 as psycopg
    dict_row = None

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProductLoader:
    def __init__(self):
        """Initialize database connection and Bedrock client"""
        self.db_config = self._get_db_config()
        # Use us-west-2 region
        self.bedrock_client = boto3.client('bedrock-runtime', region_name='us-west-2')
        self.conn = None
        self.cur = None
        
    def _get_db_config(self) -> Dict:
        """Get database configuration from environment variables or Secrets Manager"""
        if os.environ.get('DB_SECRET_ARN'):
            # Get from Secrets Manager
            sm_client = boto3.client('secretsmanager', region_name='us-west-2')
            secret = sm_client.get_secret_value(SecretId=os.environ['DB_SECRET_ARN'])
            config = json.loads(secret['SecretString'])
            return {
                'host': config['host'],
                'port': config['port'],
                'dbname': config.get('dbname', 'postgres'),
                'user': config['username'],
                'password': config['password']
            }
        else:
            # Get from environment variables
            return {
                'host': os.environ.get('PGHOST', 'localhost'),
                'port': os.environ.get('PGPORT', 5432),
                'dbname': os.environ.get('PGDATABASE', 'postgres'),
                'user': os.environ.get('PGUSER', 'postgres'),
                'password': os.environ.get('PGPASSWORD', '')
            }
    
    def connect(self):
        """Connect to the database using psycopg3"""
        try:
            # psycopg3 connection string format
            conn_str = f"host={self.db_config['host']} port={self.db_config['port']} dbname={self.db_config['dbname']} user={self.db_config['user']} password={self.db_config['password']}"
            self.conn = psycopg.connect(conn_str)
            
            if dict_row:  # psycopg3
                self.cur = self.conn.cursor(row_factory=dict_row)
            else:  # psycopg2 fallback
                from psycopg2.extras import RealDictCursor
                self.cur = self.conn.cursor(cursor_factory=RealDictCursor)
            
            logger.info("Connected to Aurora PostgreSQL")
            
            # Register pgvector extension
            self.cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            self.conn.commit()
            logger.info("pgvector extension ready")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def create_schema(self):
        """Create the products table with vector column"""
        schema_sql = """
        -- Drop existing table if exists
        DROP TABLE IF EXISTS products CASCADE;
        
        -- Create products table
        CREATE TABLE products (
            product_id VARCHAR(50) PRIMARY KEY,
            product_description TEXT NOT NULL,
            img_url TEXT,
            product_url TEXT,
            stars DECIMAL(2,1),
            reviews INTEGER DEFAULT 0,
            price DECIMAL(10,2),
            category_id INTEGER,
            is_best_seller BOOLEAN DEFAULT FALSE,
            bought_in_last_month INTEGER DEFAULT 0,
            category_name VARCHAR(255),
            quantity INTEGER DEFAULT 0,
            
            -- Vector embedding for semantic search (1024 dimensions for Titan)
            embedding vector(1024),
            
            -- Additional metadata as JSONB
            metadata JSONB DEFAULT '{}',
            
            -- Timestamps
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        
        -- Create indexes
        CREATE INDEX idx_products_category ON products(category_name);
        CREATE INDEX idx_products_price ON products(price);
        CREATE INDEX idx_products_stars ON products(stars);
        CREATE INDEX idx_products_best_seller ON products(is_best_seller);
        
        -- Create text search index for hybrid search
        CREATE INDEX idx_products_description_gin ON products 
        USING gin(to_tsvector('english', product_description));
        """
        
        try:
            self.cur.execute(schema_sql)
            self.conn.commit()
            logger.info("Database schema created successfully")
        except Exception as e:
            logger.error(f"Failed to create schema: {e}")
            self.conn.rollback()
            raise
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using Amazon Titan on Bedrock"""
        try:
            response = self.bedrock_client.invoke_model(
                modelId='amazon.titan-embed-text-v2:0',
                body=json.dumps({
                    'inputText': text[:8000]  # Titan has a token limit
                })
            )
            result = json.loads(response['body'].read())
            return result['embedding']
        except Exception as e:
            logger.warning(f"Failed to generate embedding: {e}")
            # Return zero vector as fallback
            return [0.0] * 1024
    
    def load_products(self, csv_file: str, batch_size: int = 100):
        """Load products from CSV file"""
        logger.info(f"Loading products from {csv_file}")
        
        if not os.path.exists(csv_file):
            logger.error(f"CSV file not found: {csv_file}")
            return 0
        
        # Read CSV
        df = pd.read_csv(csv_file)
        logger.info(f"Found {len(df)} products to load")
        
        # Clean data
        df = df.fillna({
            'stars': 0.0,
            'reviews': 0,
            'price': 0.0,
            'boughtInLastMonth': 0,
            'quantity': 0,
            'isBestSeller': False
        })
        
        # Process in batches
        total_loaded = 0
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]
            batch_data = []
            
            for _, row in batch.iterrows():
                # Generate embedding for product description
                embedding_text = f"{row['product_description']} {row.get('category_name', '')}"
                embedding = self.generate_embedding(embedding_text)
                
                # Prepare row data
                batch_data.append((
                    row['productId'],
                    row['product_description'],
                    row.get('imgUrl', ''),
                    row.get('productURL', ''),
                    float(row.get('stars', 0)),
                    int(row.get('reviews', 0)),
                    float(row.get('price', 0)),
                    int(row.get('category_id', 0)),
                    bool(row.get('isBestSeller', False)),
                    int(row.get('boughtInLastMonth', 0)),
                    row.get('category_name', ''),
                    int(row.get('quantity', 0)),
                    embedding,
                    json.dumps({
                        'original_index': int(i + batch.index[0])
                    })
                ))
            
            # Insert batch
            insert_sql = """
                INSERT INTO products (
                    product_id, product_description, img_url, product_url,
                    stars, reviews, price, category_id, is_best_seller,
                    bought_in_last_month, category_name, quantity, embedding, metadata
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (product_id) DO NOTHING
            """
            
            try:
                # For psycopg3, use executemany
                if hasattr(self.cur, 'executemany'):
                    self.cur.executemany(insert_sql, batch_data)
                else:
                    # psycopg2 fallback
                    from psycopg2.extras import execute_batch
                    execute_batch(self.cur, insert_sql, batch_data)
                
                self.conn.commit()
                total_loaded += len(batch_data)
                logger.info(f"Loaded {total_loaded}/{len(df)} products")
            except Exception as e:
                logger.error(f"Failed to insert batch: {e}")
                self.conn.rollback()
                continue
        
        logger.info(f"Successfully loaded {total_loaded} products")
        return total_loaded
    
    def create_vector_index(self):
        """Create HNSW index for fast similarity search"""
        logger.info("Creating HNSW index for vector search...")
        
        index_sql = """
        -- Create HNSW index for cosine distance
        CREATE INDEX IF NOT EXISTS idx_products_embedding_hnsw 
        ON products USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);
        
        -- Analyze table for query optimization
        ANALYZE products;
        """
        
        try:
            self.cur.execute(index_sql)
            self.conn.commit()
            logger.info("HNSW index created successfully")
        except Exception as e:
            logger.error(f"Failed to create index: {e}")
            self.conn.rollback()
    
    def verify_load(self):
        """Verify data was loaded correctly"""
        checks = [
            ("Total products", "SELECT COUNT(*) FROM products"),
            ("Products with embeddings", "SELECT COUNT(*) FROM products WHERE embedding IS NOT NULL"),
            ("Categories", "SELECT COUNT(DISTINCT category_name) FROM products"),
            ("Average price", "SELECT AVG(price) FROM products"),
            ("Average rating", "SELECT AVG(stars) FROM products")
        ]
        
        for label, query in checks:
            self.cur.execute(query)
            result = self.cur.fetchone()
            # Handle both dict and tuple results
            if isinstance(result, dict):
                value = list(result.values())[0]
            else:
                value = result[0]
            logger.info(f"{label}: {value}")
    
    def close(self):
        """Close database connection"""
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()
        logger.info("Database connection closed")

def main():
    """Main execution function"""
    # Look for CSV in multiple locations
    csv_locations = [
        '/workshop/data/amazon-products-sample.csv',
        '/workshop/sample-dat406-build-agentic-ai-powered-search-apg/data/amazon-products-sample.csv',
        '../data/amazon-products-sample.csv',
        'data/amazon-products-sample.csv',
        '/tmp/amazon-products-sample.csv'
    ]
    
    csv_file = None
    for location in csv_locations:
        if os.path.exists(location):
            csv_file = location
            break
    
    if not csv_file:
        logger.error("CSV file not found in any expected location")
        sys.exit(1)
    
    # Load products
    loader = ProductLoader()
    try:
        loader.connect()
        loader.create_schema()
        loaded = loader.load_products(csv_file)
        if loaded > 0:
            loader.create_vector_index()
            loader.verify_load()
        logger.info("Product loading completed successfully!")
    except Exception as e:
        logger.error(f"Failed to load products: {e}")
        sys.exit(1)
    finally:
        loader.close()

if __name__ == "__main__":
    main()