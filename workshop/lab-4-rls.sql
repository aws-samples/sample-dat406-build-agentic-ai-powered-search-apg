\set ON_ERROR_STOP on

-- Lab 4 proof artifact: exercise the same customer boundary through PostgreSQL
-- RLS. The script fails closed if the mapping, positive control, denial, or
-- runtime role is wrong. Every write is enclosed by an explicit ROLLBACK.
--
-- Run with:
--   psql -X -v ON_ERROR_STOP=1 -P pager=off \
--     -f workshop/lab-4-rls.sql

DO $mapping$
DECLARE
    mapped_shoppers INTEGER;
    marco_mappings INTEGER;
    jessica_mappings INTEGER;
BEGIN
    SELECT count(*) INTO mapped_shoppers
      FROM pellier.principal_customers;
    SELECT count(*) INTO marco_mappings
      FROM pellier.principal_customers
     WHERE customer_id = 'CUST-MARCO';
    SELECT count(*) INTO jessica_mappings
      FROM pellier.principal_customers
     WHERE customer_id = 'CUST-JESSICA';

    IF mapped_shoppers <> 4 THEN
        RAISE EXCEPTION
            'Lab 4 needs exactly four workshop principal mappings; found %',
            mapped_shoppers;
    END IF;
    IF marco_mappings <> 1 OR jessica_mappings <> 1 THEN
        RAISE EXCEPTION
            'Lab 4 needs one Marco and one Jessica principal mapping';
    END IF;
END;
$mapping$;

SELECT principal_sub AS marco_sub
  FROM pellier.principal_customers
 WHERE customer_id = 'CUST-MARCO'
\gset

SELECT principal_sub AS jessica_sub
  FROM pellier.principal_customers
 WHERE customer_id = 'CUST-JESSICA'
\gset

WITH ordered AS (
    SELECT product_id, sum(quantity)::INTEGER AS ordered_quantity
      FROM pellier.orders
     WHERE customer_id = 'CUST-JESSICA'
     GROUP BY product_id
),
returned AS (
    SELECT product_id, sum(quantity)::INTEGER AS returned_quantity
      FROM pellier.returns
     WHERE customer_id = 'CUST-JESSICA'
       AND status <> 'rejected'
     GROUP BY product_id
)
SELECT o.product_id AS jessica_product_id
  FROM ordered o
  LEFT JOIN returned r USING (product_id)
 WHERE o.ordered_quantity > coalesce(r.returned_quantity, 0)
 ORDER BY o.product_id
 LIMIT 1
\gset

\if :{?jessica_product_id}
\else
  \warn 'Lab 4 needs one returnable Jessica product for the positive write control'
  \quit 1
\endif

BEGIN;
SET LOCAL ROLE pellier_query;
SELECT set_config('pellier.principal_sub', :'jessica_sub', true);
SELECT current_setting('pellier.principal_sub', true) = :'jessica_sub'
       AS jessica_principal_bound
\gset
\if :jessica_principal_bound
\else
  \warn 'Jessica principal was not bound to the RLS transaction'
  \quit 1
\endif

SELECT count(*) AS jessica_jessica_rows
  FROM pellier.orders
 WHERE customer_id = 'CUST-JESSICA'
\gset

SELECT 'RLS_READ_JESSICA_JESSICA_ROWS:' || :'jessica_jessica_rows';
SELECT :'jessica_jessica_rows'::INTEGER = 0 AS jessica_read_failed
\gset
\if :jessica_read_failed
  \warn 'Jessica could not read any Jessica rows; the positive control failed'
  \quit 1
\endif
ROLLBACK;

BEGIN;
SET LOCAL ROLE pellier_query;
SELECT set_config('pellier.principal_sub', :'marco_sub', true);
SELECT current_setting('pellier.principal_sub', true) = :'marco_sub'
       AS marco_principal_bound
\gset
\if :marco_principal_bound
\else
  \warn 'Marco principal was not bound to the RLS transaction'
  \quit 1
\endif

SELECT count(*) AS marco_jessica_rows
  FROM pellier.orders
 WHERE customer_id = 'CUST-JESSICA'
\gset

SELECT 'RLS_READ_MARCO_JESSICA_ROWS:' || :'marco_jessica_rows';
SELECT :'marco_jessica_rows'::INTEGER <> 0 AS marco_read_failed
\gset
\if :marco_read_failed
  \warn 'Marco could read Jessica rows; the RLS read boundary failed'
  \quit 1
\endif
ROLLBACK;

BEGIN;
SET LOCAL ROLE pellier_agent;
SELECT CASE
         WHEN current_user = 'pellier_agent' THEN 'RLS_PROBE_ROLE_OK'
         ELSE 'RLS_PROBE_ROLE_WRONG'
       END;
SELECT current_user <> 'pellier_agent' AS role_probe_failed
\gset
\if :role_probe_failed
  \warn 'The write proof is not running as pellier_agent'
  \quit 1
\endif

SELECT set_config('pellier.lab4_product_id', :'jessica_product_id', true);
SELECT set_config('pellier.principal_sub', :'marco_sub', true);

DO $marco_write$
DECLARE
    error_message TEXT;
BEGIN
    BEGIN
        INSERT INTO pellier.returns
            (customer_id, product_id, reason, status, quantity)
        VALUES
            (
                'CUST-JESSICA',
                current_setting('pellier.lab4_product_id'),
                'other',
                'pending',
                1
            );
        RAISE EXCEPTION
            'RLS_PROBE_MARCO_SQLSTATE:00000: out-of-scope write succeeded';
    EXCEPTION
        WHEN insufficient_privilege THEN
            GET STACKED DIAGNOSTICS error_message = MESSAGE_TEXT;
            IF position('row-level security policy' IN error_message) = 0 THEN
                RAISE EXCEPTION
                    'Marco received 42501 for a non-RLS reason: %',
                    error_message;
            END IF;
            RAISE NOTICE 'RLS_PROBE_MARCO_SQLSTATE:42501';
    END;
END;
$marco_write$;

SELECT set_config('pellier.principal_sub', :'jessica_sub', true);
INSERT INTO pellier.returns
    (customer_id, product_id, reason, status, quantity)
VALUES
    ('CUST-JESSICA', :'jessica_product_id', 'other', 'pending', 1);
DO $jessica_write$
BEGIN
    RAISE NOTICE 'RLS_PROBE_JESSICA_SQLSTATE:00000';
END;
$jessica_write$;

ROLLBACK;
