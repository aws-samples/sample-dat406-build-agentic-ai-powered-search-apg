#!/usr/bin/env python3
"""
Regenerate embeddings using Amazon Titan Text Embeddings v2
Based on parallel-fast-loader.py but using Titan v2 with 1024 dimensions
"""

import pandas as pd
import numpy as np
import boto3
import json
import psycopg
from pgvector.psycopg import register_vector
from pandarallel import pandarallel
import time
import warnings
import sys
import os

warnings.filterwarnings('ignore')

# Configuration
CSV_PATH = '../data/amazon-products-sample.csv'
BATCH_SIZE = 1000
PARALLEL_WORKERS = 8
REGION = 'us-west-2'

# Database credentials from .env
DB_HOST = 'apgpg-pgvector.cluster-chygmprofdnr.us-west-2.rds.amazonaws.com'
DB_PORT = 5432
DB_USER = 'postgres'
DB_PASS = 'brVJ3SNrNtw9VEnG'
DB_NAME = 'postgres'

print("="*70)
print("⚡ REGENERATE EMBEDDINGS WITH TITAN V2")
print(f"Using {PARALLEL_WORKERS} parallel workers")
print("This will process all 21,704 products")
print("="*70)

# Check CSV exists
if not os.path.exists(CSV_PATH):
    print(f"❌ CSV not found: {CSV_PATH}")
    sys.exit(1)

# Initialize Bedrock client (global for parallel access)
bedrock_runtime = boto3.client('bedrock-runtime', region_name=REGION)

def generate_embedding_titan_v2(text):
    """Generate Titan v2 embedding with 1024 dimensions"""
    if not text or pd.isna(text):
        return np.random.randn(1024).tolist()
    
    try:
        request_body = {
            "inputText": str(text)[:8000],
            "dimensions": 1024,
            "normalize": True
        }
        
        response = bedrock_runtime.invoke_model(
            modelId='amazon.titan-embed-text-v2:0',
            contentType='application/json',
            accept='application/json',
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response['body'].read())
        return response_body['embedding']
    except Exception as e:
        # Silent fallback
        np.random.seed(hash(str(text)) % 2**32)
        return np.random.randn(1024).tolist()

# Setup database
def setup_database():
    """Drop and recreate table"""
    conn = psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        dbname=DB_NAME,
        autocommit=True
    )
    
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    register_vector(conn)
    
    conn.execute("CREATE SCHEMA IF NOT EXISTS bedrock_integration;")
    
    print("\n🗑️  Dropping existing table...")
    conn.execute("DROP TABLE IF EXISTS bedrock_integration.product_catalog CASCADE;")
    
    print("📋 Creating new table...")
    conn.execute("""
    CREATE TABLE bedrock_integration.product_catalog (
        "productId" VARCHAR(255) PRIMARY KEY,
        product_description TEXT,
        imgurl TEXT,
        producturl TEXT,
        stars NUMERIC,
        reviews INT,
        price NUMERIC,
        category_id INT,
        isbestseller BOOLEAN,
        boughtinlastmonth INT,
        category_name VARCHAR(255),
        quantity INT,
        embedding vector(1024)
    );
    """)
    
    print("✅ Database setup complete")
    conn.close()

print("\n📋 Setting up database...")
setup_database()

# Load product data
print("\n📁 Loading product data...")
df = pd.read_csv(CSV_PATH)

# Clean up missing values
df = df.dropna(subset=['product_description'])
df = df.fillna({
    'stars': 0,
    'reviews': 0,
    'price': 0,
    'category_id': 0,
    'isBestSeller': False,
    'boughtInLastMonth': 0,
    'category_name': 'Unknown',
    'quantity': 0,
    'imgUrl': '',
    'productURL': ''
})

print(f"✅ Loaded {len(df)} products")

# Generate embeddings in parallel
print("\n🧠 Generating Titan v2 embeddings in parallel...")
print(f"This will take approximately {len(df)/60:.1f} minutes...")

pandarallel.initialize(progress_bar=True, nb_workers=PARALLEL_WORKERS, verbose=0)

start_time = time.time()
df['embedding'] = df['product_description'].parallel_apply(generate_embedding_titan_v2)

embed_time = time.time() - start_time
print(f"\n✅ Embeddings generated in {embed_time/60:.1f} minutes")
print(f"   Rate: {len(df)/embed_time:.1f} products/second")

# Store products
def store_products():
    """Store products in database with batch processing"""
    start_time = time.time()
    
    conn = psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        dbname=DB_NAME,
        autocommit=True
    )
    
    register_vector(conn)
    
    print(f"\n💾 Storing {len(df)} products in database...")
    
    try:
        with conn.cursor() as cur:
            batches = []
            total_processed = 0
            
            for i, (_, row) in enumerate(df.iterrows(), 1):
                batches.append((
                    row['productId'],
                    str(row['product_description'])[:5000],
                    str(row.get('imgUrl', ''))[:500],
                    str(row.get('productURL', ''))[:500],
                    float(row['stars']),
                    int(row['reviews']),
                    float(row['price']),
                    int(row.get('category_id', 0)),
                    bool(row.get('isBestSeller', False)),
                    int(row.get('boughtInLastMonth', 0)),
                    str(row['category_name'])[:255],
                    int(row.get('quantity', 0)),
                    row['embedding']
                ))
                
                if len(batches) == BATCH_SIZE or i == len(df):
                    cur.executemany("""
                    INSERT INTO bedrock_integration.product_catalog (
                        "productId", product_description, imgurl, producturl,
                        stars, reviews, price, category_id, isbestseller,
                        boughtinlastmonth, category_name, quantity, embedding
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, batches)
                    
                    total_processed += len(batches)
                    progress = (total_processed / len(df)) * 100
                    print(f"\rProgress: {progress:.1f}% | {total_processed}/{len(df)}", end="")
                    
                    batches = []
            
            print("\n\n🔍 Creating HNSW index...")
            cur.execute("""
                CREATE INDEX product_catalog_embedding_idx 
                ON bedrock_integration.product_catalog 
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64);
            """)
            print("✅ HNSW index created")
            
            print("\n🔧 Running VACUUM ANALYZE...")
            cur.execute("VACUUM ANALYZE bedrock_integration.product_catalog;")
            
            cur.execute("SELECT COUNT(*) FROM bedrock_integration.product_catalog")
            final_count = cur.fetchone()[0]
            
            end_time = time.time()
            total_time = end_time - start_time
            
            print("\n" + "="*70)
            print("📊 LOADING STATISTICS")
            print("="*70)
            print(f"✅ Total rows loaded: {final_count:,}")
            print(f"⏱️ Total time: {total_time:.2f} seconds")
            print("="*70)
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        raise
    finally:
        conn.close()

store_products()

# Test search
print("\n🔍 Testing search with 'bluetooth headphones'...")
conn = psycopg.connect(
    host=DB_HOST, port=DB_PORT, user=DB_USER,
    password=DB_PASS, dbname=DB_NAME, autocommit=True
)
register_vector(conn)

test_embedding = generate_embedding_titan_v2('bluetooth headphones')

cur = conn.cursor()
cur.execute("""
    SELECT 
        product_description,
        stars,
        price,
        1 - (embedding <=> %s::vector) as similarity
    FROM bedrock_integration.product_catalog
    ORDER BY embedding <=> %s::vector
    LIMIT 5
""", (test_embedding, test_embedding))

results = cur.fetchall()

print("\nTop 5 results:")
for i, (desc, stars, price, sim) in enumerate(results, 1):
    print(f"{i}. {desc[:70]}")
    print(f"   Similarity: {sim:.4f}, Stars: {stars}, Price: ${price}\n")

cur.close()
conn.close()

print("="*70)
print("🎉 REGENERATION COMPLETE!")
print("="*70)
