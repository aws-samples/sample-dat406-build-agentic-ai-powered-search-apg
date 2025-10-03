import asyncio
import sys
import os
os.chdir('backend')
sys.path.insert(0, '.')
from services.database import DatabaseService
import numpy as np

async def check_embeddings():
    db = DatabaseService()
    await db.connect()
    
    # Get a bluetooth headphone product and its embedding
    query = '''
        SELECT 
            "productId",
            product_description,
            embedding
        FROM bedrock_integration.product_catalog
        WHERE LOWER(product_description) LIKE '%%bluetooth%%headphone%%'
        LIMIT 1
    '''
    
    result = await db.fetch_one(query)
    if result:
        r = dict(result)
        emb = r['embedding']
        print(f'Product: {r["product_description"][:80]}')
        print(f'Embedding length: {len(emb)}')
        print(f'First 10 values: {emb[:10]}')
        print(f'Embedding stats:')
        print(f'  Min: {min(emb):.6f}')
        print(f'  Max: {max(emb):.6f}')
        print(f'  Mean: {np.mean(emb):.6f}')
        print(f'  Std: {np.std(emb):.6f}')
        print(f'  Norm: {np.linalg.norm(emb):.6f}')
        
        # Check if all zeros
        if all(v == 0 for v in emb):
            print('\n⚠️  WARNING: Embedding is all zeros!')
        
        # Check if normalized
        norm = np.linalg.norm(emb)
        if abs(norm - 1.0) < 0.01:
            print(f'\n✓ Embedding appears normalized (norm={norm:.6f})')
        else:
            print(f'\n✗ Embedding NOT normalized (norm={norm:.6f})')
    
    await db.disconnect()

asyncio.run(check_embeddings())
