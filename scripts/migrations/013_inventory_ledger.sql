-- Migration 013: inventory ledger + return-line quantity integrity.
--
-- Two write-path consistency problems this closes.
--
-- 1. Returns had no quantity model. `pellier.returns` records a customer,
--    a product, and a reason — but not how many units came back, and
--    nothing bounded the total returned against what was ordered. Two
--    valid-looking requests could return three units of a one-unit order.
--
-- 2. Two stock representations could drift. A damaged return decrements
--    the aggregate `product_catalog.quantity`, while `floor_check` reads
--    per-warehouse `warehouse_inventory.quantity`. Nothing tied them
--    together, so the number a shopper is told and the number an operator
--    sees could disagree with no failing query anywhere.
--
-- The fix is a ledger. Every stock movement appends one row here, and both
-- representations are derivable from it. The ledger is the source of
-- truth; the two quantity columns become caches that a check query can
-- reconcile against.
--
-- Rollout note: this migration is additive. It creates the ledger, seeds
-- it from current warehouse rows, and installs one trigger at the database
-- write boundary. Migration 011 supplies transaction-local reason and
-- idempotency context for the known return/restock functions. Direct SQL
-- writes are still captured, but are labeled as adjustments.

\set ON_ERROR_STOP on

BEGIN;

-- ---------------------------------------------------------------------
-- Return lines: how many units of an order line came back
-- ---------------------------------------------------------------------
ALTER TABLE pellier.returns
    ADD COLUMN IF NOT EXISTS quantity INTEGER NOT NULL DEFAULT 1;

ALTER TABLE pellier.returns
    DROP CONSTRAINT IF EXISTS returns_quantity_positive;
ALTER TABLE pellier.returns
    ADD CONSTRAINT returns_quantity_positive CHECK (quantity > 0);

-- Ties a return to the order it came from, so returned quantity can be
-- bounded by ordered quantity. Nullable: historical rows predate it.
ALTER TABLE pellier.returns
    ADD COLUMN IF NOT EXISTS order_id BIGINT
    REFERENCES pellier.orders(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS returns_order_idx
    ON pellier.returns (order_id)
    WHERE order_id IS NOT NULL;

-- Rejects a return that would take a customer past what they ordered for
-- that product. Enforced in the database so a misbehaving agent, a retry
-- storm, and a direct SQL caller are all bounded by the same rule.
CREATE OR REPLACE FUNCTION pellier.assert_return_within_ordered_quantity()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_ordered  INTEGER;
    v_returned INTEGER;
BEGIN
    SELECT COALESCE(sum(quantity), 0) INTO v_ordered
      FROM pellier.orders
     WHERE customer_id = NEW.customer_id
       AND product_id = NEW.product_id;

    -- No order history for this pair: nothing to bound against. The
    -- ownership check in the tool layer already refuses these, and
    -- failing here too would block legitimate seed/backfill rows.
    IF v_ordered = 0 THEN
        RETURN NEW;
    END IF;

    SELECT COALESCE(sum(quantity), 0) INTO v_returned
      FROM pellier.returns
     WHERE customer_id = NEW.customer_id
       AND product_id = NEW.product_id
       AND status <> 'rejected'
       AND (TG_OP = 'INSERT' OR id <> NEW.id);

    IF v_returned + NEW.quantity > v_ordered THEN
        RAISE EXCEPTION
            'return quantity % exceeds unreturned ordered quantity % for customer % product %',
            NEW.quantity, v_ordered - v_returned, NEW.customer_id, NEW.product_id
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS returns_quantity_guard ON pellier.returns;
CREATE TRIGGER returns_quantity_guard
    BEFORE INSERT OR UPDATE OF quantity, status ON pellier.returns
    FOR EACH ROW
    EXECUTE FUNCTION pellier.assert_return_within_ordered_quantity();

-- ---------------------------------------------------------------------
-- Inventory ledger: the single source of truth for stock movement
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pellier.inventory_ledger (
    entry_id        BIGSERIAL PRIMARY KEY,
    product_id      TEXT NOT NULL
                    REFERENCES pellier.product_catalog("productId")
                    ON DELETE CASCADE,
    -- NULL warehouse means an aggregate-only movement (e.g. a legacy
    -- catalog adjustment with no warehouse attribution).
    warehouse_id    TEXT,
    -- Signed: positive receives stock, negative removes it. One column
    -- rather than separate in/out columns so the balance is a plain sum.
    delta           INTEGER NOT NULL CHECK (delta <> 0),
    reason          TEXT NOT NULL
                    CHECK (reason IN
                    ('restock', 'return_damaged', 'return_resellable',
                     'sale', 'seed', 'adjustment')),
    -- Correlates a movement with the write that caused it, so a ledger
    -- row is traceable back to a tool_audit row and a governed receipt.
    idempotency_key TEXT,
    principal_sub   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS inventory_ledger_product_idx
    ON pellier.inventory_ledger (product_id, created_at DESC);

CREATE INDEX IF NOT EXISTS inventory_ledger_warehouse_idx
    ON pellier.inventory_ledger (warehouse_id, product_id)
    WHERE warehouse_id IS NOT NULL;

-- One ledger row per idempotency key per product: a replayed write cannot
-- append a second movement.
CREATE UNIQUE INDEX IF NOT EXISTS inventory_ledger_idempotency_idx
    ON pellier.inventory_ledger (idempotency_key, product_id)
    WHERE idempotency_key IS NOT NULL;

-- Seed the ledger from current warehouse rows so balances reconcile from
-- the first query rather than starting at zero against live stock.
INSERT INTO pellier.inventory_ledger
    (product_id, warehouse_id, delta, reason, idempotency_key)
SELECT wi.product_id, wi.warehouse_id, wi.quantity, 'seed',
       'seed:' || wi.warehouse_id || ':' || wi.product_id
  FROM pellier.warehouse_inventory wi
 WHERE wi.quantity > 0
   AND NOT EXISTS (
       SELECT 1 FROM pellier.inventory_ledger il
        WHERE il.idempotency_key =
              'seed:' || wi.warehouse_id || ':' || wi.product_id
          AND il.product_id = wi.product_id
   );

-- A prior revision of this migration created the ledger without wiring the
-- live write path. On upgrade, absorb only that pre-existing difference
-- into one deterministic baseline row per warehouse/product. Future writes
-- are appended by the trigger below. Deleting/rebuilding the baseline on a
-- rerun keeps this migration idempotent without hiding later trigger-backed
-- movements.
DELETE FROM pellier.inventory_ledger
 WHERE idempotency_key LIKE 'baseline:013:%';

INSERT INTO pellier.inventory_ledger
    (product_id, warehouse_id, delta, reason, idempotency_key)
SELECT wi.product_id,
       wi.warehouse_id,
       wi.quantity - COALESCE(sum(il.delta), 0)::INTEGER,
       'adjustment',
       'baseline:013:' || wi.warehouse_id || ':' || wi.product_id
  FROM pellier.warehouse_inventory wi
  LEFT JOIN pellier.inventory_ledger il
         ON il.product_id = wi.product_id
        AND il.warehouse_id = wi.warehouse_id
 GROUP BY wi.product_id, wi.warehouse_id, wi.quantity
HAVING wi.quantity - COALESCE(sum(il.delta), 0) <> 0;

-- ---------------------------------------------------------------------
-- One database boundary for every warehouse stock movement
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION pellier.record_inventory_movement()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_product_id      TEXT;
    v_warehouse_id    TEXT;
    v_delta           INTEGER;
    v_reason          TEXT;
    v_idempotency_key TEXT;
    v_principal_sub   TEXT;
BEGIN
    IF TG_OP = 'INSERT' THEN
        v_product_id := NEW.product_id;
        v_warehouse_id := NEW.warehouse_id;
        v_delta := NEW.quantity;
    ELSIF TG_OP = 'DELETE' THEN
        v_product_id := OLD.product_id;
        v_warehouse_id := OLD.warehouse_id;
        v_delta := -OLD.quantity;
    ELSE
        v_product_id := NEW.product_id;
        v_warehouse_id := NEW.warehouse_id;
        v_delta := NEW.quantity - OLD.quantity;
    END IF;

    IF v_delta = 0 THEN
        IF TG_OP = 'DELETE' THEN
            RETURN OLD;
        END IF;
        RETURN NEW;
    END IF;

    v_reason := COALESCE(
        NULLIF(current_setting('pellier.inventory_reason', true), ''),
        'adjustment'
    );
    IF v_reason NOT IN (
        'restock',
        'return_damaged',
        'return_resellable',
        'sale',
        'seed',
        'adjustment'
    ) THEN
        v_reason := 'adjustment';
    END IF;

    v_idempotency_key := NULLIF(
        current_setting('pellier.inventory_idempotency_key', true),
        ''
    );
    v_principal_sub := NULLIF(
        current_setting('pellier.principal_sub', true),
        ''
    );

    INSERT INTO pellier.inventory_ledger
        (product_id, warehouse_id, delta, reason, idempotency_key, principal_sub)
    VALUES
        (
            v_product_id,
            v_warehouse_id,
            v_delta,
            v_reason,
            v_idempotency_key,
            v_principal_sub
        );

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS warehouse_inventory_ledger_write
    ON pellier.warehouse_inventory;
CREATE TRIGGER warehouse_inventory_ledger_write
    AFTER INSERT OR DELETE OR UPDATE OF quantity
    ON pellier.warehouse_inventory
    FOR EACH ROW
    EXECUTE FUNCTION pellier.record_inventory_movement();

-- ---------------------------------------------------------------------
-- Derived views + a reconciliation check
-- ---------------------------------------------------------------------

-- Per-warehouse balance derived from the ledger.
CREATE OR REPLACE VIEW pellier.warehouse_balance AS
SELECT product_id,
       warehouse_id,
       sum(delta)::INTEGER AS quantity
  FROM pellier.inventory_ledger
 WHERE warehouse_id IS NOT NULL
 GROUP BY product_id, warehouse_id;

-- Catalog-level balance derived from the same ledger.
CREATE OR REPLACE VIEW pellier.catalog_balance AS
SELECT product_id,
       sum(delta)::INTEGER AS quantity
  FROM pellier.inventory_ledger
 GROUP BY product_id;

-- Reports drift between the cached quantity columns and the ledger.
-- Returns zero rows when everything agrees, which makes it usable as a
-- one-SELECT proof in the workshop: "the number the shopper was told and
-- the number the operator sees come from the same ledger."
CREATE OR REPLACE FUNCTION pellier.reconcile_inventory()
RETURNS TABLE (
    scope         TEXT,
    product_id    TEXT,
    warehouse_id  TEXT,
    cached        INTEGER,
    ledger        INTEGER
)
LANGUAGE sql
STABLE
AS $$
    SELECT 'warehouse'::TEXT,
           COALESCE(wi.product_id, wb.product_id),
           COALESCE(wi.warehouse_id, wb.warehouse_id),
           COALESCE(wi.quantity, 0)::INTEGER,
           COALESCE(wb.quantity, 0)
      FROM pellier.warehouse_inventory wi
      FULL OUTER JOIN pellier.warehouse_balance wb
             ON wb.product_id = wi.product_id
            AND wb.warehouse_id = wi.warehouse_id
     WHERE COALESCE(wi.quantity, 0) <> COALESCE(wb.quantity, 0)
    UNION ALL
    SELECT 'catalog'::TEXT,
           pc."productId",
           NULL::TEXT,
           pc.quantity::INTEGER,
           COALESCE(cb.quantity, 0)
      FROM pellier.product_catalog pc
      LEFT JOIN pellier.catalog_balance cb
             ON cb.product_id = pc."productId"
     WHERE EXISTS (SELECT 1 FROM pellier.inventory_ledger il
                    WHERE il.product_id = pc."productId")
       AND pc.quantity <> COALESCE(cb.quantity, 0);
$$;

COMMIT;
