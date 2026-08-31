-- Migration 033: extend governed inventory to all 60 curated products.
--
-- The catalog contains 40 persona pieces, 10 House pieces used by the
-- Operator client book, and 10 Signature pieces used by premium journeys.
-- Inventory previously covered only IDs 1-40, which made "curated product"
-- mean different things across the storefront and Labs. This migration adds
-- the same exact three-warehouse split for IDs 41-60 without rewriting any
-- existing stock movement.

\set ON_ERROR_STOP on

BEGIN;

SET LOCAL pellier.inventory_reason = 'seed';

INSERT INTO pellier.warehouse_inventory
    (warehouse_id, product_id, quantity)
SELECT
    wh.id,
    pc."productId",
    CASE wh.id
        WHEN 'BK-01' THEN GREATEST(
            0,
            pc.quantity
              - FLOOR(pc.quantity * 0.30)::INTEGER
              - FLOOR(pc.quantity * 0.30)::INTEGER
        )::SMALLINT
        WHEN 'ATX-02' THEN GREATEST(
            0, FLOOR(pc.quantity * 0.30)::INTEGER
        )::SMALLINT
        WHEN 'PDX-01' THEN GREATEST(
            0, FLOOR(pc.quantity * 0.30)::INTEGER
        )::SMALLINT
    END
FROM pellier.warehouses wh
CROSS JOIN pellier.product_catalog pc
WHERE wh.id IN ('BK-01', 'ATX-02', 'PDX-01')
  AND pc."productId" ~ '^[0-9]+$'
  AND pc."productId"::int BETWEEN 1 AND 60
ON CONFLICT (warehouse_id, product_id) DO NOTHING;

DO $$
DECLARE
    curated_count INTEGER;
    inventory_rows INTEGER;
    invalid_products INTEGER;
    drift_count INTEGER;
BEGIN
    SELECT count(*)
      INTO curated_count
      FROM pellier.product_catalog
     WHERE "productId" ~ '^[0-9]+$'
       AND "productId"::int BETWEEN 1 AND 60;

    SELECT count(*)
      INTO inventory_rows
      FROM pellier.warehouse_inventory wi
     WHERE wi.product_id ~ '^[0-9]+$'
       AND wi.product_id::int BETWEEN 1 AND 60;

    SELECT count(*)
      INTO invalid_products
      FROM (
          SELECT product_id
            FROM pellier.warehouse_inventory
           WHERE product_id ~ '^[0-9]+$'
             AND product_id::int BETWEEN 1 AND 60
           GROUP BY product_id
          HAVING count(*) <> 3
      ) invalid;

    SELECT count(*)
      INTO drift_count
      FROM pellier.product_catalog pc
     WHERE pc."productId" ~ '^[0-9]+$'
       AND pc."productId"::int BETWEEN 1 AND 60
       AND pc.quantity <> (
           SELECT COALESCE(sum(wi.quantity), 0)
             FROM pellier.warehouse_inventory wi
            WHERE wi.product_id = pc."productId"
       );

    IF curated_count <> 60
       OR inventory_rows <> 180
       OR invalid_products <> 0
       OR drift_count <> 0 THEN
        RAISE EXCEPTION
            'Expected 60 curated products and 180 reconciled warehouse rows; got curated %, rows %, invalid products %, drift %',
            curated_count,
            inventory_rows,
            invalid_products,
            drift_count;
    END IF;
END $$;

COMMIT;
