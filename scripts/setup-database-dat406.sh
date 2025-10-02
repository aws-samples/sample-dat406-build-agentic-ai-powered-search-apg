#!/bin/bash
# ===========================================================================
# DAT406 Workshop - Database Setup and Data Loading Script
# ===========================================================================
# Sets up PostgreSQL database with pgvector, creates tables, generates
# embeddings, and loads ~21,704 products into the catalog
#
# Prerequisites:
# - bootstrap-code-editor-dat406.sh must be run first
# - Amazon Bedrock Titan Text Embeddings v2 model must be enabled
# - PostgreSQL with pgvector extension available
#
# Usage: ./setup-database-dat406.sh
# ===========================================================================

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}[$(date +'%H:%M:%S')] WARNING:${NC} $1"; }
error() { echo -e "${RED}[$(date +'%H:%M:%S')] ERROR:${NC} $1"; exit 1; }
info() { echo -e "${BLUE}[$(date +'%H:%M:%S')] INFO:${NC} $1"; }

# ============================================================================
# ENVIRONMENT SETUP
# ============================================================================

log "==================== DAT406 Database Setup Starting ===================="

REPO_DIR="/workshop/sample-dat406-build-agentic-ai-powered-search-apg"

# Load environment variables
if [ -f "$REPO_DIR/.env" ]; then
    source "$REPO_DIR/.env"
    log "✅ Environment file loaded"
else
    error ".env file not found at $REPO_DIR/.env"
fi

# Verify required variables
REQUIRED_VARS=("DB_HOST" "DB_PORT" "DB_NAME" "DB_USER" "DB_PASSWORD" "AWS_REGION")
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var:-}" ]; then
        error "Required environment variable $var is not set"
    fi
done

log "Database Configuration:"
log "  Host: $DB_HOST:$DB_PORT"
log "  Database: $DB_NAME"
log "  User: $DB_USER"
log "  Region: $AWS_REGION"

# ============================================================================
# CONNECTIVITY TESTS
# ============================================================================

log "Testing database connectivity..."
if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    -c "SELECT version();" &>/dev/null; then
    log "✅ Database connection successful"
else
    error "Database connection failed"
fi

log "Testing Bedrock Titan Embeddings v2 access..."
TEST_INPUT='{"inputText":"test","dimensions":1024}'

if aws bedrock-runtime invoke-model \
    --model-id amazon.titan-embed-text-v2:0 \
    --body "$TEST_INPUT" \
    --region "$AWS_REGION" \
    /tmp/bedrock_test.json 2>/dev/null; then
    
    if [ -f /tmp/bedrock_test.json ] && [ $(stat -c%s /tmp/bedrock_test.json 2>/dev/null || stat -f%z /tmp/bedrock_test.json) -gt 50 ]; then
        log "✅ Bedrock Titan Embeddings model accessible"
        rm -f /tmp/bedrock_test.json
    else
        error "Bedrock model response invalid"
    fi
else
    error "Cannot access Bedrock Titan Embeddings. Enable it in AWS Console first"
fi

# ============================================================================
# CREATE DATABASE SCHEMA
# ============================================================================

log "==================== Creating Database Schema ===================="

log "Creating schema and tables..."
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" << 'SQL_SCHEMA'
-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create bedrock_integration schema
CREATE SCHEMA IF NOT EXISTS bedrock_integration;

-- Drop existing table if present (clean slate)
DROP TABLE IF EXISTS bedrock_integration.product_catalog CASCADE;

-- Create product catalog table
CREATE TABLE bedrock_integration.product_catalog (
    "productId" VARCHAR(255) PRIMARY KEY,
    product_description TEXT NOT NULL,
    imgurl TEXT,
    producturl TEXT,
    stars NUMERIC(3,2),
    reviews INTEGER,
    price NUMERIC(10,2),
    category_id INTEGER,
    isbestseller BOOLEAN DEFAULT FALSE,
    boughtinlastmonth INTEGER,
    category_name VARCHAR(255),
    quantity INTEGER DEFAULT 0,
    embedding vector(1024),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create standard indexes
CREATE INDEX idx_product_category ON bedrock_integration.product_catalog(category_id);
CREATE INDEX idx_product_price ON bedrock_integration.product_catalog(price);
CREATE INDEX idx_product_stars ON bedrock_integration.product_catalog(stars);
CREATE INDEX idx_product_quantity ON bedrock_integration.product_catalog(quantity);

SELECT 'Schema created successfully' as status;
SQL_SCHEMA

if [ $? -eq 0 ]; then
    log "✅ Database schema created"
else
    error "Failed to create schema"
fi

# ============================================================================
# LOAD PRODUCT DATA WITH EMBEDDINGS
# ============================================================================

log "==================== Loading Product Data ===================="

DATA_FILE="$REPO_DIR/data/amazon-products-sample.csv"

# Check if data file exists
if [ ! -f "$DATA_FILE" ]; then
    # Try alternate names
    ALT_FILES=(
        "$REPO_DIR/data/amazon-products.csv"
        "$REPO_DIR/data/products.csv"
    )
    
    for alt in "${ALT_FILES[@]}"; do
        if [ -f "$alt" ]; then
            DATA_FILE="$alt"
            break
        fi
    done
    
    if [ ! -f "$DATA_FILE" ]; then
        error "Product data CSV not found in $REPO_DIR/data/"
    fi
fi

log "Using data file: $DATA_FILE"

# Count rows
TOTAL_ROWS=$(wc -l < "$DATA_FILE")
log "Data file contains $(($TOTAL_ROWS - 1)) products (excluding header)"

# Create Python data loader
cat > /tmp/load_products_dat406.py << 'PYTHON_LOADER'
#!/usr/bin/env python3
"""
DAT406 Workshop - Product Data Loader
Loads products with Bedrock Titan embeddings into PostgreSQL
"""

import os
import sys
import time
import json
import boto3
import psycopg
import pandas as pd
import numpy as np
from pathlib import Path
from pgvector.psycopg import register_vector
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')

# Constants
BATCH_SIZE = 100
MAX_RETRIES = 3
RETRY_DELAY = 1
EMBEDDING_DIM = 1024

print("="*70)
print(" DAT406 Workshop - Product Data Loader")
print(" Loading products with Titan Text Embeddings v2")
print("="*70)

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'port': int(os.getenv('DB_PORT', '5432')),
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD')
}

AWS_REGION = os.getenv('AWS_REGION', 'us-west-2')
DATA_FILE = sys.argv[1] if len(sys.argv) > 1 else None

if not DATA_FILE or not os.path.exists(DATA_FILE):
    print("❌ Data file not provided or doesn't exist")
    sys.exit(1)

# Validate database config
if not all(DB_CONFIG.values()):
    print("❌ Missing database configuration")
    sys.exit(1)

print(f"📊 Data file: {DATA_FILE}")
print(f"🗄️  Database: {DB_CONFIG['dbname']} @ {DB_CONFIG['host']}")

# Initialize Bedrock client
bedrock_runtime = boto3.client('bedrock-runtime', region_name=AWS_REGION)

def generate_embedding(text: str) -> list:
    """Generate 1024-dimensional embedding using Titan v2"""
    if pd.isna(text) or not str(text).strip():
        return [0.0] * EMBEDDING_DIM
    
    # Clean and truncate text
    clean_text = str(text)[:2000].strip()
    
    for attempt in range(MAX_RETRIES):
        try:
            body = json.dumps({
                "inputText": clean_text,
                "dimensions": EMBEDDING_DIM,
                "normalize": True
            })
            
            response = bedrock_runtime.invoke_model(
                modelId="amazon.titan-embed-text-v2:0",
                body=body,
                contentType="application/json",
                accept="application/json"
            )
            
            result = json.loads(response['body'].read())
            
            if 'embedding' in result:
                embedding = result['embedding']
                if len(embedding) == EMBEDDING_DIM:
                    return embedding
            
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
            else:
                print(f"\n⚠️  Failed to generate embedding: {str(e)}")
    
    return [0.0] * EMBEDDING_DIM

# Load data
print("\n📥 Loading CSV data...")
df = pd.read_csv(DATA_FILE)

# Data validation and cleaning
print(f"📊 Initial rows: {len(df)}")

# Drop rows with missing descriptions
df = df.dropna(subset=['product_description'])

# Fill missing values
df = df.fillna({
    'stars': 0,
    'reviews': 0,
    'price': 0,
    'category_id': 0,
    'isbestseller': False,
    'boughtinlastmonth': 0,
    'category_name': 'Unknown',
    'quantity': 0,
    'imgurl': '',
    'producturl': ''
})

# Generate unique product IDs if missing
if 'productId' not in df.columns or df['productId'].isna().any():
    df['productId'] = ['B' + str(i).zfill(7) for i in range(len(df))]

# Ensure unique product IDs
df = df.drop_duplicates(subset=['productId'], keep='first')

# Truncate fields to database limits
df['product_description'] = df['product_description'].astype(str).str[:2000]
df['imgurl'] = df['imgurl'].astype(str).str[:500]
df['producturl'] = df['producturl'].astype(str).str[:500]
df['category_name'] = df['category_name'].astype(str).str[:255]
df['productId'] = df['productId'].astype(str).str[:255]

# Convert data types
df['stars'] = pd.to_numeric(df['stars'], errors='coerce').fillna(0)
df['reviews'] = pd.to_numeric(df['reviews'], errors='coerce').fillna(0).astype(int)
df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0)
df['category_id'] = pd.to_numeric(df['category_id'], errors='coerce').fillna(0).astype(int)
df['isbestseller'] = df['isbestseller'].astype(bool)
df['boughtinlastmonth'] = pd.to_numeric(df['boughtinlastmonth'], errors='coerce').fillna(0).astype(int)
df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0).astype(int)

print(f"✅ Cleaned data: {len(df)} products ready")

# Generate embeddings
print(f"\n🧠 Generating embeddings for {len(df)} products...")
print("   This will take 5-10 minutes depending on dataset size...")

start_time = time.time()
embeddings = []

with tqdm(total=len(df), desc="Generating embeddings") as pbar:
    for idx, row in df.iterrows():
        embedding = generate_embedding(row['product_description'])
        embeddings.append(embedding)
        pbar.update(1)
        
        # Brief pause to avoid rate limiting
        if (idx + 1) % 10 == 0:
            time.sleep(0.1)

df['embedding'] = embeddings

embed_time = time.time() - start_time
print(f"✅ Embeddings generated in {embed_time/60:.1f} minutes")
print(f"   Rate: {len(df)/embed_time:.1f} products/second")

# Connect to database
print("\n💾 Connecting to PostgreSQL...")
try:
    conn = psycopg.connect(**DB_CONFIG, autocommit=False)
    register_vector(conn)
    print("✅ Database connection established")
except Exception as e:
    print(f"❌ Database connection failed: {e}")
    sys.exit(1)

# Clear existing data
print("\n🗑️  Clearing existing data...")
with conn.cursor() as cur:
    cur.execute("TRUNCATE TABLE bedrock_integration.product_catalog CASCADE;")
    conn.commit()

# Insert products in batches
print(f"\n📝 Inserting {len(df)} products...")
total_inserted = 0
failed_inserts = 0

with tqdm(total=len(df), desc="Inserting products") as pbar:
    for i in range(0, len(df), BATCH_SIZE):
        batch = df.iloc[i:i+BATCH_SIZE]
        
        with conn.cursor() as cur:
            for _, row in batch.iterrows():
                try:
                    cur.execute('''
                        INSERT INTO bedrock_integration.product_catalog 
                        ("productId", product_description, imgurl, producturl, 
                         stars, reviews, price, category_id, isbestseller,
                         boughtinlastmonth, category_name, quantity, embedding)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (
                        row['productId'],
                        str(row['product_description']),
                        str(row['imgurl']),
                        str(row['producturl']),
                        float(row['stars']),
                        int(row['reviews']),
                        float(row['price']),
                        int(row['category_id']),
                        bool(row['isbestseller']),
                        int(row['boughtinlastmonth']),
                        str(row['category_name']),
                        int(row['quantity']),
                        row['embedding']
                    ))
                    total_inserted += 1
                except Exception as e:
                    failed_inserts += 1
                    if failed_inserts <= 5:
                        print(f"\n⚠️  Insert error: {str(e)[:100]}")
        
        conn.commit()
        pbar.update(len(batch))

print(f"\n✅ Inserted {total_inserted} products")
if failed_inserts > 0:
    print(f"⚠️  Failed inserts: {failed_inserts}")

# Create indexes
print("\n🔍 Creating search indexes...")

with conn.cursor() as cur:
    # HNSW index for vector similarity (cosine distance)
    print("  Creating HNSW vector index...")
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_product_embedding_hnsw 
        ON bedrock_integration.product_catalog 
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);
    """)
    
    # GIN index for full-text search
    print("  Creating full-text search index...")
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_product_fts 
        ON bedrock_integration.product_catalog
        USING GIN (to_tsvector('english', coalesce(product_description, '')));
    """)
    
    # Trigram index for fuzzy matching
    print("  Creating trigram index...")
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_product_trgm 
        ON bedrock_integration.product_catalog
        USING GIN (product_description gin_trgm_ops);
    """)
    
    conn.commit()

print("✅ Indexes created")

# Final statistics
with conn.cursor() as cur:
    cur.execute("SELECT COUNT(*) FROM bedrock_integration.product_catalog;")
    final_count = cur.fetchone()[0]
    
    cur.execute("""
        SELECT COUNT(*) 
        FROM bedrock_integration.product_catalog 
        WHERE embedding IS NOT NULL;
    """)
    embeddings_count = cur.fetchone()[0]
    
    cur.execute("""
        SELECT 
            MIN(price) as min_price,
            MAX(price) as max_price,
            AVG(price) as avg_price,
            COUNT(DISTINCT category_name) as categories
        FROM bedrock_integration.product_catalog;
    """)
    stats = cur.fetchone()

conn.close()

# Print summary
print("\n" + "="*70)
print(" ✅ Data Loading Complete!")
print("="*70)
print(f" Total products: {final_count:,}")
print(f" Products with embeddings: {embeddings_count:,}")
print(f" Success rate: {(embeddings_count/final_count)*100:.1f}%")
print(f" Price range: ${stats[0]:.2f} - ${stats[1]:.2f}")
print(f" Average price: ${stats[2]:.2f}")
print(f" Categories: {stats[3]}")
print("="*70)
PYTHON_LOADER

# Run the loader
log "Running data loader (this will take 5-10 minutes)..."
if python3 /tmp/load_products_dat406.py "$DATA_FILE"; then
    log "✅ Product data loaded successfully"
    rm -f /tmp/load_products_dat406.py
else
    error "Failed to load product data"
fi

# ============================================================================
# CREATE VERIFICATION QUERIES
# ============================================================================

log "==================== Creating Verification Queries ===================="

# Create test queries file
cat > "$REPO_DIR/scripts/test_database.sql" << 'TEST_SQL'
-- DAT406 Database Verification Queries

-- 1. Count total products
SELECT 'Total Products' as metric, COUNT(*) as value
FROM bedrock_integration.product_catalog;

-- 2. Count products with embeddings
SELECT 'Products with Embeddings' as metric, COUNT(*) as value
FROM bedrock_integration.product_catalog
WHERE embedding IS NOT NULL;

-- 3. Category distribution
SELECT 
    category_name,
    COUNT(*) as products,
    ROUND(AVG(price), 2) as avg_price,
    ROUND(AVG(stars), 2) as avg_rating
FROM bedrock_integration.product_catalog
GROUP BY category_name
ORDER BY products DESC
LIMIT 10;

-- 4. Test vector similarity search
SELECT 
    "productId",
    LEFT(product_description, 80) as description,
    stars,
    price,
    1 - (embedding <=> (
        SELECT embedding 
        FROM bedrock_integration.product_catalog 
        LIMIT 1
    )) as similarity
FROM bedrock_integration.product_catalog
WHERE embedding IS NOT NULL
ORDER BY embedding <=> (
    SELECT embedding 
    FROM bedrock_integration.product_catalog 
    LIMIT 1
)
LIMIT 5;

-- 5. Test full-text search
SELECT 
    "productId",
    LEFT(product_description, 80) as description,
    stars,
    price
FROM bedrock_integration.product_catalog
WHERE to_tsvector('english', product_description) @@ to_tsquery('english', 'wireless & headphone')
LIMIT 5;
TEST_SQL

log "✅ Test queries created at $REPO_DIR/scripts/test_database.sql"

# ============================================================================
# CREATE HELPER SCRIPTS
# ============================================================================

log "Creating helper scripts..."

# Database test script
cat > "$REPO_DIR/scripts/test_connection.sh" << 'TEST_CONN'
#!/bin/bash
source "$(dirname "$0")/../.env"

echo "Testing database connection..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT version();"

echo ""
echo "Checking product count..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c \
    "SELECT COUNT(*) as products FROM bedrock_integration.product_catalog;"

echo ""
echo "Checking embeddings..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c \
    "SELECT COUNT(*) as with_embeddings FROM bedrock_integration.product_catalog WHERE embedding IS NOT NULL;"
TEST_CONN

chmod +x "$REPO_DIR/scripts/test_connection.sh"

# Sample search script
cat > "$REPO_DIR/scripts/sample_search.py" << 'SAMPLE_SEARCH'
#!/usr/bin/env python3
"""Sample semantic search using the loaded product data"""

import os
import sys
import json
import boto3
import psycopg
from pathlib import Path
from pgvector.psycopg import register_vector

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment
from dotenv import load_dotenv
load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'port': int(os.getenv('DB_PORT', '5432')),
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD')
}

AWS_REGION = os.getenv('AWS_REGION', 'us-west-2')

def generate_query_embedding(query: str) -> list:
    """Generate embedding for search query"""
    bedrock = boto3.client('bedrock-runtime', region_name=AWS_REGION)
    
    body = json.dumps({
        "inputText": query,
        "dimensions": 1024,
        "normalize": True
    })
    
    response = bedrock.invoke_model(
        modelId="amazon.titan-embed-text-v2:0",
        body=body
    )
    
    result = json.loads(response['body'].read())
    return result['embedding']

def semantic_search(query: str, limit: int = 10):
    """Perform semantic search"""
    print(f"\n🔍 Searching for: '{query}'\n")
    
    # Generate query embedding
    query_embedding = generate_query_embedding(query)
    
    # Connect to database
    conn = psycopg.connect(**DB_CONFIG)
    register_vector(conn)
    
    with conn.cursor() as cur:
        cur.execute('''
            SELECT 
                "productId",
                product_description,
                stars,
                reviews,
                price,
                category_name,
                1 - (embedding <=> %s::vector) as similarity
            FROM bedrock_integration.product_catalog
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        ''', (query_embedding, query_embedding, limit))
        
        results = cur.fetchall()
    
    conn.close()
    
    # Display results
    for i, row in enumerate(results, 1):
        print(f"{i}. {row[1][:70]}...")
        print(f"   ID: {row[0]} | ⭐ {row[2]:.1f} ({row[3]} reviews) | ${row[4]:.2f}")
        print(f"   Category: {row[5]} | Similarity: {row[6]:.3f}\n")

if __name__ == '__main__':
    query = sys.argv[1] if len(sys.argv) > 1 else "wireless headphones with noise cancellation"
    semantic_search(query)
SAMPLE_SEARCH

chmod +x "$REPO_DIR/scripts/sample_search.py"

log "✅ Helper scripts created in $REPO_DIR/scripts/"

# ============================================================================
# FINAL VERIFICATION
# ============================================================================

log "==================== Final Verification ===================="

# Get statistics
TOTAL_PRODUCTS=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    -t -c "SELECT COUNT(*) FROM bedrock_integration.product_catalog;" 2>/dev/null | xargs)

WITH_EMBEDDINGS=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    -t -c "SELECT COUNT(*) FROM bedrock_integration.product_catalog WHERE embedding IS NOT NULL;" 2>/dev/null | xargs)

INDEXES=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    -t -c "SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'bedrock_integration' AND tablename = 'product_catalog';" 2>/dev/null | xargs)

# ============================================================================
# SUMMARY
# ============================================================================

echo
log "==================== Setup Complete! ===================="
echo
echo "📊 Database Statistics:"
echo "   Products loaded: ${TOTAL_PRODUCTS:-0}"
echo "   Products with embeddings: ${WITH_EMBEDDINGS:-0}"
echo "   Indexes created: ${INDEXES:-0}"
echo
echo "🧪 Test Commands:"
echo "   Test connection:"
echo "     $REPO_DIR/scripts/test_connection.sh"
echo
echo "   Run verification queries:"
echo "     psql -f $REPO_DIR/scripts/test_database.sql"
echo
echo "   Try semantic search:"
echo "     python3 $REPO_DIR/scripts/sample_search.py 'laptop computer'"
echo
echo "🚀 Ready to start the application!"
echo "   Frontend: cd $REPO_DIR/frontend && npm run dev"
echo "   Backend: cd $REPO_DIR/backend && uvicorn app:app --reload"
echo
log "============================================================"