\set ON_ERROR_STOP on

-- Migration 039: re-establish RLS ownership before returning an idempotent replay.
--
-- `write_operations` is global by idempotency key, while ownership is scoped by
-- the caller's transaction-local `pellier.principal_sub`. The prior function
-- selected a completed result before querying `orders`, so a caller outside the
-- return owner's RLS scope could receive that stored result by reusing its key
-- and exact request hash. The ownership query now runs after the durable claim
-- is locked, but before either conflict or replay is returned:
--
--   * failed or out-of-scope attempts keep their unfinalized claim as evidence;
--   * an authorized same-request replay still returns the prior result;
--   * an unauthorized replay reaches the same RLS-scoped denial path as an
--     unauthorized first attempt and never receives another customer's result.
--
-- This is forward-only. Existing clusters already applied migration 023, so
-- editing that historical migration would leave the deployed function unsafe.

BEGIN;

CREATE OR REPLACE FUNCTION pellier.process_return_idempotent(
    p_idempotency_key TEXT,
    p_request_hash TEXT,
    p_customer_id TEXT,
    p_product_id TEXT,
    p_reason TEXT
) RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_claimed BOOLEAN;
    v_rows INTEGER;
    v_existing pellier.write_operations%ROWTYPE;
    v_return_id BIGINT;
    v_name TEXT;
    v_warehouse_id TEXT;
    v_quantity INTEGER;
    v_result JSONB;
BEGIN
    IF NULLIF(btrim(p_idempotency_key), '') IS NULL THEN
        RETURN jsonb_build_object(
            'status', 'error',
            'message', 'idempotency_key is required.'
        );
    END IF;
    IF p_reason NOT IN (
        'damaged',
        'wrong_size',
        'not_as_described',
        'changed_mind',
        'other'
    ) THEN
        RETURN jsonb_build_object(
            'status', 'policy_blocked',
            'message', format('Reason %s is not allowed.', p_reason)
        );
    END IF;

    INSERT INTO pellier.write_operations
        (idempotency_key, operation, request_hash)
    VALUES
        (p_idempotency_key, 'initiate_return', p_request_hash)
    ON CONFLICT (idempotency_key) DO NOTHING;
    GET DIAGNOSTICS v_rows = ROW_COUNT;
    v_claimed := v_rows = 1;

    SELECT *
      INTO v_existing
      FROM pellier.write_operations
     WHERE idempotency_key = p_idempotency_key
     FOR UPDATE;

    IF NOT FOUND THEN
        -- A concurrent caller released its failed claim between the INSERT and
        -- this lock. Adopt the claim rather than continuing against an all-NULL
        -- record, where the argument guard below would silently not fire.
        INSERT INTO pellier.write_operations
            (idempotency_key, operation, request_hash)
        VALUES
            (p_idempotency_key, 'initiate_return', p_request_hash)
        ON CONFLICT (idempotency_key) DO NOTHING;
        SELECT *
          INTO v_existing
          FROM pellier.write_operations
         WHERE idempotency_key = p_idempotency_key
         FOR UPDATE;
        v_claimed := TRUE;
    END IF;

    -- This SELECT is the ownership enforcement point because the function is
    -- SECURITY INVOKER and `orders_principal_scope` applies to its caller.
    -- It must happen before every response that could expose state associated
    -- with a durable idempotency key.
    PERFORM 1
      FROM pellier.orders
     WHERE customer_id = p_customer_id
       AND product_id = p_product_id
     LIMIT 1;
    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'status', 'error',
            'message', format(
                'Customer %s did not order product %s; cannot process return.',
                p_customer_id, p_product_id
            )
        );
    END IF;

    IF v_existing.operation <> 'initiate_return'
       OR v_existing.request_hash <> p_request_hash THEN
        RETURN jsonb_build_object(
            'status', 'idempotency_conflict',
            'message', 'Idempotency key was already used with different arguments.'
        );
    END IF;
    IF NOT v_claimed AND v_existing.result IS NOT NULL THEN
        RETURN v_existing.result || jsonb_build_object('idempotent_replay', true);
    END IF;

    SELECT name
      INTO v_name
      FROM pellier.product_catalog
     WHERE "productId" = p_product_id
     FOR UPDATE;

    IF v_name IS NULL THEN
        v_result := jsonb_build_object(
            'status', 'error',
            'message', format('Product %s not found.', p_product_id)
        );
    ELSE
        IF p_reason = 'damaged' THEN
            SELECT warehouse_id
              INTO v_warehouse_id
              FROM pellier.warehouse_inventory
             WHERE product_id = p_product_id
             ORDER BY quantity DESC
             LIMIT 1;
        END IF;

        IF v_result IS NULL THEN
            INSERT INTO pellier.returns (customer_id, product_id, reason)
            VALUES (p_customer_id, p_product_id, p_reason)
            RETURNING id INTO v_return_id;

            IF p_reason = 'damaged' THEN
                SELECT COALESCE(sum(quantity), 0)::INTEGER
                  INTO v_quantity
                  FROM pellier.warehouse_inventory
                 WHERE product_id = p_product_id;

                UPDATE pellier.product_catalog
                   SET quantity = v_quantity,
                       updated_at = now()
                 WHERE "productId" = p_product_id;
            END IF;

            v_result := jsonb_build_object(
                'status', 'success',
                'return_id', v_return_id,
                'product_id', p_product_id::INTEGER,
                'name', v_name,
                'reason', p_reason,
                'new_quantity', CASE
                    WHEN p_reason = 'damaged' THEN v_quantity
                    ELSE NULL
                END,
                'warehouse_id', v_warehouse_id,
                'idempotent_replay', false
            );
        END IF;
    END IF;

    -- Failed attempts remain unfinalized and retryable. Only a successful
    -- return becomes the canonical durable result for an idempotency key.
    IF v_result->>'status' = 'success' THEN
        UPDATE pellier.write_operations
           SET result = v_result,
               completed_at = now()
         WHERE idempotency_key = p_idempotency_key;
    END IF;
    RETURN v_result;
END;
$$;

COMMIT;
