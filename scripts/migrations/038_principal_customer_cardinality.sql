\set ON_ERROR_STOP on

-- Migration 038: one verified Cognito subject may own one customer scope.
--
-- `current_principal_customers()` is deliberately set-returning so policies can
-- express the mapping in one shared SQL expression. Without a cardinality
-- constraint, however, a second row for one subject widened every USING and
-- WITH CHECK policy at once. Multiple principals for one customer remain
-- legitimate and are intentionally allowed.

BEGIN;

DO $$
DECLARE
    conflicting_subjects TEXT;
BEGIN
    SELECT string_agg(
               format('%s maps to {%s}', principal_sub, customer_ids),
               '; ' ORDER BY principal_sub
           )
      INTO conflicting_subjects
      FROM (
          SELECT principal_sub,
                 string_agg(customer_id, ', ' ORDER BY customer_id) AS customer_ids
            FROM pellier.principal_customers
           GROUP BY principal_sub
          HAVING count(*) > 1
      ) conflicts;

    IF conflicting_subjects IS NOT NULL THEN
        RAISE EXCEPTION
            'principal_customers maps a subject to multiple customers; resolve before constraining: %',
            conflicting_subjects;
    END IF;
END
$$;

DO $$
DECLARE
    principal_sub_attnum SMALLINT;
BEGIN
    SELECT attnum
      INTO principal_sub_attnum
      FROM pg_attribute
     WHERE attrelid = 'pellier.principal_customers'::regclass
       AND attname = 'principal_sub'
       AND NOT attisdropped;

    IF principal_sub_attnum IS NULL THEN
        RAISE EXCEPTION 'principal_customers.principal_sub is missing';
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conrelid = 'pellier.principal_customers'::regclass
           AND contype = 'u'
           AND conkey = ARRAY[principal_sub_attnum]::SMALLINT[]
    ) THEN
        ALTER TABLE pellier.principal_customers
            ADD CONSTRAINT principal_customers_one_customer_per_subject
            UNIQUE (principal_sub);
    END IF;
END
$$;

COMMIT;
