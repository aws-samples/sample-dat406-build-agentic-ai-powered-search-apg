# DAT406 Workshop - Sample Data

## Amazon Products Dataset

**File**: `amazon-products-sample.csv`  
**Size**: 21,704 products  
**Format**: CSV with headers

### Schema

| Column | Type | Description |
|--------|------|-------------|
| productId | string | Unique product identifier |
| product_description | text | Full product description |
| price | decimal | Product price in USD |
| stars | decimal | Average rating (0-5) |
| reviews | integer | Number of reviews |
| category_name | string | Product category |
| quantity | integer | Current stock |

### Loading the Data

Run `scripts/setup-database.sh` to:
1. Create database schema
2. Load 21,704 products
3. Generate embeddings
4. Create HNSW index

**Note**: Place CSV file in this directory before running setup.
