#!/usr/bin/env python3
"""
Regenerate product embeddings using Amazon Titan Text Embeddings v2
Drops existing table, creates new schema, generates embeddings, and creates HNSW index
"""

import asyncio
import csv
import sys
import os
import boto3
import json
from typing import List
import time

os.chdir('backend')
sys.path.insert(0, '.')

from services.database import DatabaseService
from config import settings

# Initialize Bedrock client
bedrock = boto3.client('bedrock-runtime', region_name=settings.AWS_REGION)

def generate_embedding(text: str) -> List[float]:
    """Generate embedding using Titan v2 with 1024 dimensions"""
    request_body = {
        "inputText": text,
        "dimensions": 1024,
        "normalize": True
    }
    
    response = bedrock.invoke_model(
        modelId='amazon.titan-embed-text-v2:0',
        contentType='application/json',
        accept='application/json',
        body=json.dumps(request_body)
    )
    
    response_body = json.loads(response['body'].read())
    return response_body['embedding']

async def regenerate_all():
    db = DatabaseService()
    await db.connect()
    
    print("=" * 70)
    print("REGENERATING PRODUCT EMBEDDINGS")
    print("=" * 70)
    
    # Step 1: Drop existing table
    print("\n1. Dropping existing table...")
    await db.execute_query("DROP TABLE IF EXISTS bedrock_integration.product_catalog CASCADE")
    print("   ✓ Table dropped")
    
    # Step 2: Create new table with vector column
    print("\n2. Creating new table...")
    create_table_sql = """
        CREATE TABLE bedrock_integration.product_catalog (
            "productId" VARCHAR(50) PRIMARY KEY,
            product_description TEXT,
            imgurl TEXT,
            producturl TEXT,
            stars FLOAT,
            reviews INTEGER,
            price FLOAT,
            category_id INTEGER,
            isbestseller BOOLEAN,
            boughtinlastmonth INTEGER,
            category_name VARCHAR(255),
            quantity INTEGER,
            embedding vector(1024)
        )
    """
    await db.execute_query(create_table_sql)
    print("   ✓ Table created")
    
    # Step 3: Load CSV and generate embeddings
    print("\n3. Loading products and generating embeddings...")
    csv_path = '../data/amazon-products-sample.csv'
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        products = list(reader)
    
    print(f"   Found {len(products)} products")
    
    batch_size = 10
    total = len(products)
    
    for i in range(0, total, batch_size):
        batch = products[i:i+batch_size]
        
        for product in batch:
            # Generate embedding
            text = product['product_description']
            embedding = generate_embedding(text)
            
            # Insert into database
            insert_sql = """
                INSERT INTO bedrock_integration.product_catalog 
                ("productId", product_description, imgurl, producturl, stars, reviews, 
                 price, category_id, isbestseller, boughtinlastmonth, category_name, 
                 quantity, embedding)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            await db.execute_query(
                insert_sql,
                product['productId'],
                product['product_description'],
                product['imgUrl'],
                product['productURL'],
                float(product['stars']) if product['stars'] else 0,
                int(product['reviews']) if product['reviews'] else 0,
                float(product['price']) if product['price'] else 0,
                int(product['category_id']) if product['category_id'] else 0,
                product['isBestSeller'].upper() == 'TRUE',
                int(product['boughtInLastMonth']) if product['boughtInLastMonth'] else 0,
                product['category_name'],
                int(product['quantity']) if product['quantity'] else 0,
                embedding
            )
        
        progress = min(i + batch_size, total)
        print(f"   Progress: {progress}/{total} ({progress*100//total}%)")
        time.sleep(0.5)  # Rate limiting
    
    print("   ✓ All embeddings generated and loaded")
    
    # Step 4: Create HNSW index
    print("\n4. Creating HNSW index...")
    index_sql = """
        CREATE INDEX product_embedding_hnsw_idx 
        ON bedrock_integration.product_catalog 
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """
    await db.execute_query(index_sql)
    print("   ✓ HNSW index created")
    
    # Step 5: Verify
    print("\n5. Verifying...")
    count_result = await db.fetch_one("SELECT COUNT(*) as count FROM bedrock_integration.product_catalog")
    count = dict(count_result)['count']
    print(f"   ✓ Total products: {count}")
    
    await db.disconnect()
    
    print("\n" + "=" * 70)
    print("REGENERATION COMPLETE!")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(regenerate_all())
