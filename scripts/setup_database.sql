-- Aurora PostgreSQL setup script for Blaize Bazaar

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create products table
CREATE TABLE IF NOT EXISTS products (
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
    embedding vector(1024),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_name);
CREATE INDEX IF NOT EXISTS idx_products_price ON products(price);
CREATE INDEX IF NOT EXISTS idx_products_stars ON products(stars);
