-- Migration 035: expand named persona discovery grids to nine cards.
--
-- Each named cohort already owns ten distinct products. Promote the remaining
-- product at rank 10 so the storefront can render one featured piece followed
-- by a symmetric 3x3 discovery grid. The unsigned Fresh edit remains nine
-- promoted pieces and keeps its existing composition.

\set ON_ERROR_STOP on

BEGIN;

WITH final_rank (persona_id, product_id, storefront_rank) AS (
    VALUES
        ('marco', '20', 10),
        ('anna', '30', 10),
        ('theo', '40', 10)
)
UPDATE pellier.product_catalog AS product
   SET storefront_rank = final_rank.storefront_rank
  FROM final_rank
 WHERE product.persona_id = final_rank.persona_id
   AND product."productId" = final_rank.product_id
   AND product.storefront_rank IS DISTINCT FROM final_rank.storefront_rank;

DO $$
DECLARE
    invalid_named_edits INTEGER;
    fresh_count INTEGER;
BEGIN
    SELECT count(*)
      INTO invalid_named_edits
      FROM (
          SELECT persona_id
            FROM pellier.product_catalog
           WHERE persona_id IN ('marco', 'anna', 'theo')
             AND storefront_rank IS NOT NULL
           GROUP BY persona_id
          HAVING count(*) <> 10
              OR min(storefront_rank) <> 1
              OR max(storefront_rank) <> 10
              OR count(DISTINCT storefront_rank) <> 10
      ) invalid;

    SELECT count(*)
      INTO fresh_count
      FROM pellier.product_catalog
     WHERE persona_id = 'fresh'
       AND storefront_rank IS NOT NULL;

    IF invalid_named_edits <> 0 OR fresh_count <> 9 THEN
        RAISE EXCEPTION
            'Expected three ten-piece named edits and one nine-piece Fresh edit; invalid named %, Fresh count %',
            invalid_named_edits,
            fresh_count;
    END IF;
END $$;

COMMIT;
