# Workshop Data

## Catalog seed data

`boutique_catalog_40.csv` is the stable 40-product story catalog: 10 signed-out baseline products and 10 curated products per named persona. It intentionally does not carry embeddings inline.

`embeddings_cache.json` stores the real Cohere Embed v4 1024-dimensional vectors for those 40 curated products. `scripts/seed_boutique_catalog.py --from-cache` loads those vectors, then derives generated high-ID archive distractors so the governed retrieval lab seeds a 1,000-row corpus without calling Bedrock during bootstrap. Archive distractors carry the `archive` tag: app-facing product tools filter them out, while the eval harness keeps them in the candidate set.

Columns for CSV exports: `productId`, `product_description`, `imgUrl`, `productURL`, `stars`, `reviews`, `price`, `category_id`, `isBestSeller`, `boughtInLastMonth`, `category_name`, `quantity`, `embedding`.
