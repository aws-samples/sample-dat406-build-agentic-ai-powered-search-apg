-- Migration 015: proof-carrying storefront commerce.
--
-- The seeded pellier.orders table remains workshop history for personas and
-- returns. These commerce_* tables are the authoritative storefront purchase
-- lifecycle: quote, consent, inventory reservation, payment state, outbox,
-- and immutable evidence.

\set ON_ERROR_STOP on

BEGIN;

-- Reservation and payment-release movements are distinct from completed
-- sales. Keep that distinction in the inventory source-of-truth ledger.
ALTER TABLE pellier.inventory_ledger
    DROP CONSTRAINT IF EXISTS inventory_ledger_reason_check;
ALTER TABLE pellier.inventory_ledger
    ADD CONSTRAINT inventory_ledger_reason_check
    CHECK (reason IN (
        'restock',
        'return_damaged',
        'return_resellable',
        'reservation',
        'release',
        'sale',
        'seed',
        'adjustment'
    ));

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
        'reservation',
        'release',
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

CREATE TABLE IF NOT EXISTS pellier.commerce_quotes (
    quote_id         UUID PRIMARY KEY,
    principal_sub    TEXT NOT NULL,
    session_id       TEXT,
    turn_id          TEXT,
    currency         TEXT NOT NULL CHECK (currency = 'USD'),
    subtotal         NUMERIC(12,2) NOT NULL CHECK (subtotal >= 0),
    shipping         NUMERIC(12,2) NOT NULL CHECK (shipping >= 0),
    tax              NUMERIC(12,2) NOT NULL CHECK (tax >= 0),
    total            NUMERIC(12,2) NOT NULL CHECK (total >= 0),
    rule_snapshot    JSONB NOT NULL,
    quote_hash       CHAR(64) NOT NULL,
    status           TEXT NOT NULL DEFAULT 'open'
                     CHECK (status IN ('open', 'consumed', 'expired')),
    expires_at       TIMESTAMPTZ NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (total = subtotal + shipping + tax)
);

CREATE UNIQUE INDEX IF NOT EXISTS commerce_quotes_hash_uidx
    ON pellier.commerce_quotes (quote_hash);
CREATE INDEX IF NOT EXISTS commerce_quotes_principal_idx
    ON pellier.commerce_quotes (principal_sub, created_at DESC);

CREATE TABLE IF NOT EXISTS pellier.commerce_quote_lines (
    quote_id           UUID NOT NULL
                       REFERENCES pellier.commerce_quotes(quote_id)
                       ON DELETE CASCADE,
    product_id         TEXT NOT NULL
                       REFERENCES pellier.product_catalog("productId"),
    product_name       TEXT NOT NULL,
    image_url          TEXT,
    unit_price         NUMERIC(12,2) NOT NULL CHECK (unit_price >= 0),
    quantity           INTEGER NOT NULL CHECK (quantity > 0),
    available_quantity INTEGER NOT NULL CHECK (available_quantity >= 0),
    line_total         NUMERIC(12,2) NOT NULL CHECK (line_total >= 0),
    PRIMARY KEY (quote_id, product_id),
    CHECK (line_total = unit_price * quantity)
);

CREATE TABLE IF NOT EXISTS pellier.commerce_confirmation_grants (
    grant_id         UUID PRIMARY KEY,
    quote_id         UUID NOT NULL UNIQUE
                     REFERENCES pellier.commerce_quotes(quote_id),
    principal_sub    TEXT NOT NULL,
    quote_hash       CHAR(64) NOT NULL,
    confirmed_total  NUMERIC(12,2) NOT NULL,
    currency         TEXT NOT NULL CHECK (currency = 'USD'),
    acknowledged_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at       TIMESTAMPTZ NOT NULL,
    used_at          TIMESTAMPTZ,
    used_order_id    UUID
);

CREATE INDEX IF NOT EXISTS commerce_grants_principal_idx
    ON pellier.commerce_confirmation_grants
       (principal_sub, acknowledged_at DESC);

CREATE TABLE IF NOT EXISTS pellier.commerce_orders (
    order_id               UUID PRIMARY KEY,
    order_number           TEXT NOT NULL UNIQUE,
    principal_sub          TEXT NOT NULL,
    quote_id               UUID NOT NULL UNIQUE
                           REFERENCES pellier.commerce_quotes(quote_id),
    confirmation_grant_id  UUID NOT NULL UNIQUE
                           REFERENCES pellier.commerce_confirmation_grants(grant_id),
    idempotency_key        TEXT NOT NULL,
    session_id             TEXT,
    turn_id                TEXT,
    currency               TEXT NOT NULL CHECK (currency = 'USD'),
    subtotal               NUMERIC(12,2) NOT NULL CHECK (subtotal >= 0),
    shipping               NUMERIC(12,2) NOT NULL CHECK (shipping >= 0),
    tax                    NUMERIC(12,2) NOT NULL CHECK (tax >= 0),
    total                  NUMERIC(12,2) NOT NULL CHECK (total >= 0),
    status                 TEXT NOT NULL
                           CHECK (status IN (
                               'payment_pending',
                               'paid',
                               'payment_declined',
                               'payment_failed'
                           )),
    payment_status         TEXT NOT NULL
                           CHECK (payment_status IN (
                               'pending',
                               'settled',
                               'declined',
                               'failed'
                           )),
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (principal_sub, idempotency_key),
    CHECK (total = subtotal + shipping + tax),
    CHECK (
        (status = 'payment_pending' AND payment_status = 'pending')
        OR (status = 'paid' AND payment_status = 'settled')
        OR (status = 'payment_declined' AND payment_status = 'declined')
        OR (status = 'payment_failed' AND payment_status = 'failed')
    )
);

ALTER TABLE pellier.commerce_confirmation_grants
    DROP CONSTRAINT IF EXISTS commerce_confirmation_grants_used_order_fk;
ALTER TABLE pellier.commerce_confirmation_grants
    ADD CONSTRAINT commerce_confirmation_grants_used_order_fk
    FOREIGN KEY (used_order_id)
    REFERENCES pellier.commerce_orders(order_id);

CREATE INDEX IF NOT EXISTS commerce_orders_principal_idx
    ON pellier.commerce_orders (principal_sub, created_at DESC);

CREATE TABLE IF NOT EXISTS pellier.commerce_order_lines (
    order_id       UUID NOT NULL
                   REFERENCES pellier.commerce_orders(order_id)
                   ON DELETE CASCADE,
    product_id     TEXT NOT NULL
                   REFERENCES pellier.product_catalog("productId"),
    product_name   TEXT NOT NULL,
    image_url      TEXT,
    unit_price     NUMERIC(12,2) NOT NULL CHECK (unit_price >= 0),
    quantity       INTEGER NOT NULL CHECK (quantity > 0),
    line_total     NUMERIC(12,2) NOT NULL CHECK (line_total >= 0),
    PRIMARY KEY (order_id, product_id),
    CHECK (line_total = unit_price * quantity)
);

CREATE TABLE IF NOT EXISTS pellier.commerce_inventory_reservations (
    reservation_id UUID PRIMARY KEY,
    order_id        UUID NOT NULL
                    REFERENCES pellier.commerce_orders(order_id)
                    ON DELETE CASCADE,
    product_id      TEXT NOT NULL,
    warehouse_id    TEXT NOT NULL,
    quantity        INTEGER NOT NULL CHECK (quantity > 0),
    status          TEXT NOT NULL
                    CHECK (status IN ('reserved', 'captured', 'released')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (order_id, product_id, warehouse_id),
    FOREIGN KEY (warehouse_id, product_id)
        REFERENCES pellier.warehouse_inventory(warehouse_id, product_id)
);

CREATE INDEX IF NOT EXISTS commerce_reservations_order_idx
    ON pellier.commerce_inventory_reservations (order_id, created_at);

CREATE TABLE IF NOT EXISTS pellier.commerce_payment_attempts (
    attempt_id      UUID PRIMARY KEY,
    order_id        UUID NOT NULL UNIQUE
                    REFERENCES pellier.commerce_orders(order_id)
                    ON DELETE CASCADE,
    provider        TEXT NOT NULL CHECK (provider = 'pellier-sandbox'),
    mode            TEXT NOT NULL CHECK (mode = 'sandbox'),
    amount          NUMERIC(12,2) NOT NULL CHECK (amount >= 0),
    currency        TEXT NOT NULL CHECK (currency = 'USD'),
    status          TEXT NOT NULL
                    CHECK (status IN ('pending', 'settled', 'declined', 'failed')),
    provider_ref    TEXT,
    failure_code    TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS pellier.commerce_payment_events (
    event_id       BIGSERIAL PRIMARY KEY,
    attempt_id     UUID NOT NULL
                   REFERENCES pellier.commerce_payment_attempts(attempt_id)
                   ON DELETE CASCADE,
    event_key      TEXT NOT NULL UNIQUE,
    event_type     TEXT NOT NULL
                   CHECK (event_type IN (
                       'payment.settled',
                       'payment.declined',
                       'payment.failed'
                   )),
    payload        JSONB NOT NULL,
    occurred_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS pellier.commerce_outbox (
    event_id         UUID PRIMARY KEY,
    aggregate_type   TEXT NOT NULL CHECK (aggregate_type = 'commerce_order'),
    aggregate_id     UUID NOT NULL
                     REFERENCES pellier.commerce_orders(order_id)
                     ON DELETE CASCADE,
    event_type       TEXT NOT NULL,
    payload          JSONB NOT NULL,
    delivery_status  TEXT NOT NULL DEFAULT 'pending'
                     CHECK (delivery_status IN ('pending', 'published', 'failed')),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    published_at     TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS commerce_outbox_pending_idx
    ON pellier.commerce_outbox (created_at)
    WHERE delivery_status = 'pending';

CREATE TABLE IF NOT EXISTS pellier.commerce_receipts (
    receipt_id       UUID PRIMARY KEY,
    order_id         UUID NOT NULL UNIQUE
                     REFERENCES pellier.commerce_orders(order_id),
    principal_sub    TEXT NOT NULL,
    quote_id         UUID NOT NULL
                     REFERENCES pellier.commerce_quotes(quote_id),
    confirmation_grant_id UUID NOT NULL
                     REFERENCES pellier.commerce_confirmation_grants(grant_id),
    payment_attempt_id UUID NOT NULL
                     REFERENCES pellier.commerce_payment_attempts(attempt_id),
    outcome          TEXT NOT NULL
                     CHECK (outcome IN ('paid', 'payment_declined', 'payment_failed')),
    evidence         JSONB NOT NULL,
    receipt_hash     CHAR(64) NOT NULL UNIQUE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS commerce_receipts_principal_idx
    ON pellier.commerce_receipts (principal_sub, created_at DESC);

CREATE OR REPLACE FUNCTION pellier.reject_commerce_evidence_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION '% is append-only', TG_TABLE_NAME;
END;
$$;

DROP TRIGGER IF EXISTS commerce_payment_events_append_only
    ON pellier.commerce_payment_events;
CREATE TRIGGER commerce_payment_events_append_only
    BEFORE UPDATE OR DELETE ON pellier.commerce_payment_events
    FOR EACH ROW
    EXECUTE FUNCTION pellier.reject_commerce_evidence_mutation();

DROP TRIGGER IF EXISTS commerce_receipts_append_only
    ON pellier.commerce_receipts;
CREATE TRIGGER commerce_receipts_append_only
    BEFORE UPDATE OR DELETE ON pellier.commerce_receipts
    FOR EACH ROW
    EXECUTE FUNCTION pellier.reject_commerce_evidence_mutation();

COMMIT;
