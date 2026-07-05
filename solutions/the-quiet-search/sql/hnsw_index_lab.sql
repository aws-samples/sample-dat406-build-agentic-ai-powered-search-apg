-- hnsw_index_lab.sql -- Act I: B3 reference rebuild for product_catalog embedding index
--
-- The CREATE INDEX statement is byte-identical to scripts/migrations/001_schema.sql.
-- Use after the index lab if a participant dropped the HNSW index and needs the
-- exact recovery command.

CREATE INDEX IF NOT EXISTS product_catalog_embedding_hnsw
    ON pellier.product_catalog
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

ANALYZE pellier.product_catalog;
