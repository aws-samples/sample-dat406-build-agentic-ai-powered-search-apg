\set ON_ERROR_STOP on

DROP TABLE IF EXISTS pg_temp.lab_2_fusion;

CREATE TEMP TABLE lab_2_fusion AS
WITH receipt AS (
  SELECT *
    FROM pellier.retrieval_receipts
   WHERE receipt_id > :'receipt_high_water'::bigint
     AND query_preview =
       'Keep the gift under $100 and show me the strongest two options.'
   ORDER BY receipt_id DESC
   LIMIT 1
)
SELECT keys.product_id,
       (r.vector_ranks->>keys.product_id)::int AS vector_rank,
       (r.lexical_ranks->>keys.product_id)::int AS lexical_rank,
       -- === WORKSHOP · PostgreSQL RRF · fusion expression: START ===
       coalesce(
         1.0 / (60 + (r.vector_ranks->>keys.product_id)::int),
         0
       ) + coalesce(
         1.0 / (60 + (r.lexical_ranks->>keys.product_id)::int),
         0
       ) AS recomputed_rrf,
       -- === WORKSHOP · PostgreSQL RRF · fusion expression: END ===
       (r.rrf_scores->>keys.product_id)::numeric AS recorded_rrf
  FROM receipt r
 CROSS JOIN LATERAL jsonb_object_keys(
   r.vector_ranks || r.lexical_ranks
 ) AS keys(product_id);

SELECT product_id,
       vector_rank,
       lexical_rank,
       round(recomputed_rrf, 6) AS recomputed_rrf,
       round(recorded_rrf, 6) AS recorded_rrf,
       abs(recorded_rrf - recomputed_rrf) <= 0.000001 AS matches_receipt
  FROM lab_2_fusion
 ORDER BY recorded_rrf DESC NULLS LAST;

SELECT coalesce(
         count(*) > 0
         AND bool_and(
           recorded_rrf IS NOT NULL
           AND abs(recorded_rrf - recomputed_rrf) <= 0.000001
         ),
         false
       ) AS fusion_matches
  FROM lab_2_fusion
\gset

\if :fusion_matches
  \echo 'Lab 2 RRF build passed'
\else
  \echo 'Lab 2 RRF build failed: complete the fusion expression'
  \quit 1
\endif
