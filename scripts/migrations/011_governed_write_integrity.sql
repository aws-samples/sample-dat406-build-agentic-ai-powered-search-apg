-- Migration 011: idempotent governed writes and inventory consistency.

\set ON_ERROR_STOP on

BEGIN;

CREATE TABLE IF NOT EXISTS pellier.write_operations (
    idempotency_key TEXT PRIMARY KEY,
    operation       TEXT NOT NULL
                    CHECK (operation IN ('process_return', 'restock_shelf')),
    request_hash    TEXT NOT NULL,
    result          JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ
);

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
        (p_idempotency_key, 'process_return', p_request_hash)
    ON CONFLICT (idempotency_key) DO NOTHING;
    GET DIAGNOSTICS v_rows = ROW_COUNT;
    v_claimed := v_rows = 1;

    SELECT *
      INTO v_existing
      FROM pellier.write_operations
     WHERE idempotency_key = p_idempotency_key
     FOR UPDATE;

    IF v_existing.operation <> 'process_return'
       OR v_existing.request_hash <> p_request_hash THEN
        RETURN jsonb_build_object(
            'status', 'idempotency_conflict',
            'message', 'Idempotency key was already used with different arguments.'
        );
    END IF;
    IF NOT v_claimed AND v_existing.result IS NOT NULL THEN
        RETURN v_existing.result || jsonb_build_object('idempotent_replay', true);
    END IF;

    PERFORM 1
      FROM pellier.orders
     WHERE customer_id = p_customer_id
       AND product_id = p_product_id
     LIMIT 1;
    IF NOT FOUND THEN
        v_result := jsonb_build_object(
            'status', 'error',
            'message', format(
                'Customer %s did not order product %s; cannot process return.',
                p_customer_id, p_product_id
            )
        );
    ELSE
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
                   AND quantity > 0
                 ORDER BY quantity DESC, warehouse_id
                 FOR UPDATE
                 LIMIT 1;
                IF v_warehouse_id IS NULL THEN
                    v_result := jsonb_build_object(
                        'status', 'error',
                        'message', format(
                            'Product %s has no positive warehouse inventory.',
                            p_product_id
                        )
                    );
                ELSE
                    -- Migration 013 installs an inventory-ledger trigger.
                    -- Transaction-local context lets that trigger record the
                    -- business reason and stable write key without trusting a
                    -- second, caller-supplied copy of either value.
                    PERFORM set_config(
                        'pellier.inventory_reason',
                        'return_damaged',
                        true
                    );
                    PERFORM set_config(
                        'pellier.inventory_idempotency_key',
                        p_idempotency_key,
                        true
                    );
                    UPDATE pellier.warehouse_inventory
                       SET quantity = quantity - 1,
                           updated_at = now()
                     WHERE warehouse_id = v_warehouse_id
                       AND product_id = p_product_id;
                END IF;
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
    END IF;

    UPDATE pellier.write_operations
       SET result = v_result,
           completed_at = now()
     WHERE idempotency_key = p_idempotency_key;
    RETURN v_result;
END;
$$;

CREATE OR REPLACE FUNCTION pellier.restock_shelf_idempotent(
    p_idempotency_key TEXT,
    p_request_hash TEXT,
    p_product_id TEXT,
    p_quantity INTEGER,
    p_warehouse_id TEXT DEFAULT 'BK-01'
) RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_claimed BOOLEAN;
    v_rows INTEGER;
    v_existing pellier.write_operations%ROWTYPE;
    v_name TEXT;
    v_quantity INTEGER;
    v_result JSONB;
BEGIN
    IF NULLIF(btrim(p_idempotency_key), '') IS NULL THEN
        RETURN jsonb_build_object(
            'status', 'error',
            'message', 'idempotency_key is required.'
        );
    END IF;
    IF p_quantity <= 0 THEN
        RETURN jsonb_build_object(
            'status', 'error',
            'message', 'Quantity must be positive.'
        );
    END IF;
    IF p_quantity > 500 THEN
        RETURN jsonb_build_object(
            'status', 'policy_blocked',
            'message', 'Restock quantity exceeds the 500-unit policy limit.'
        );
    END IF;

    INSERT INTO pellier.write_operations
        (idempotency_key, operation, request_hash)
    VALUES
        (p_idempotency_key, 'restock_shelf', p_request_hash)
    ON CONFLICT (idempotency_key) DO NOTHING;
    GET DIAGNOSTICS v_rows = ROW_COUNT;
    v_claimed := v_rows = 1;

    SELECT *
      INTO v_existing
      FROM pellier.write_operations
     WHERE idempotency_key = p_idempotency_key
     FOR UPDATE;

    IF v_existing.operation <> 'restock_shelf'
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
        PERFORM set_config(
            'pellier.inventory_reason',
            'restock',
            true
        );
        PERFORM set_config(
            'pellier.inventory_idempotency_key',
            p_idempotency_key,
            true
        );
        UPDATE pellier.warehouse_inventory
           SET quantity = quantity + p_quantity,
               updated_at = now()
         WHERE warehouse_id = p_warehouse_id
           AND product_id = p_product_id;

        IF NOT FOUND THEN
            v_result := jsonb_build_object(
                'status', 'error',
                'message', format(
                    'Warehouse %s has no inventory row for product %s.',
                    p_warehouse_id, p_product_id
                )
            );
        ELSE
            SELECT COALESCE(sum(quantity), 0)::INTEGER
              INTO v_quantity
              FROM pellier.warehouse_inventory
             WHERE product_id = p_product_id;

            UPDATE pellier.product_catalog
               SET quantity = v_quantity,
                   updated_at = now()
             WHERE "productId" = p_product_id;

            v_result := jsonb_build_object(
                'status', 'success',
                'product_id', p_product_id,
                'name', v_name,
                'new_quantity', v_quantity,
                'added', p_quantity,
                'warehouse_id', p_warehouse_id,
                'idempotent_replay', false
            );
        END IF;
    END IF;

    UPDATE pellier.write_operations
       SET result = v_result,
           completed_at = now()
     WHERE idempotency_key = p_idempotency_key;
    RETURN v_result;
END;
$$;

COMMIT;
