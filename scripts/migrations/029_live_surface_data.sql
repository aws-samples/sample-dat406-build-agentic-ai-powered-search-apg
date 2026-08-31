-- Migration 029: live storefront and Observatory surface data.
--
-- The participant UI must read one durable contract. Earlier revisions kept
-- persona cards, canonical shopper prompts, product grouping, and the active
-- persona session in separate browser or process-local fixtures. That made a
-- successful-looking workshop surface possible even when Aurora was absent.
--
-- This migration makes those records ordinary Aurora data:
--   * persona_profiles: presentation metadata tied to a real customer row
--   * workshop_scenarios: guided requests owned by the workshop database
--   * shopper_sessions: durable persona/session association
--   * product_catalog.persona_id: editorial grouping for the live floor
--
-- It is safe on a fresh account (after 003_persona_seed.sql) and upgrades an
-- existing account without deleting catalog, customer, or evidence rows.

\set ON_ERROR_STOP on

BEGIN;

CREATE SCHEMA IF NOT EXISTS pellier;

ALTER TABLE pellier.product_catalog
    ADD COLUMN IF NOT EXISTS persona_id TEXT;

UPDATE pellier.product_catalog
   SET persona_id = CASE
       WHEN "productId" ~ '^[0-9]+$'
            AND "productId"::integer BETWEEN 1 AND 10 THEN 'fresh'
       WHEN "productId" ~ '^[0-9]+$'
            AND "productId"::integer BETWEEN 11 AND 20 THEN 'marco'
       WHEN "productId" ~ '^[0-9]+$'
            AND "productId"::integer BETWEEN 21 AND 30 THEN 'anna'
       WHEN "productId" ~ '^[0-9]+$'
            AND "productId"::integer BETWEEN 31 AND 40 THEN 'theo'
       WHEN "productId" ~ '^[0-9]+$'
            AND "productId"::integer BETWEEN 41 AND 50 THEN 'house'
       WHEN "productId" ~ '^[0-9]+$'
            AND "productId"::integer BETWEEN 51 AND 60 THEN 'signature'
       ELSE COALESCE(persona_id, 'archive')
   END
 WHERE persona_id IS NULL
    OR persona_id = '';

-- PNG masters are deliberately not shipped. The catalog points at the
-- responsive WebP derivative, while the frontend adds the AVIF candidate via
-- <picture>. This update also repairs an already-provisioned account.
UPDATE pellier.product_catalog
   SET "imgUrl" = regexp_replace("imgUrl", '\.png$', '.webp')
 WHERE "imgUrl" ~ '\.png$';

CREATE INDEX IF NOT EXISTS product_catalog_persona_idx
    ON pellier.product_catalog (persona_id, tier, "productId");

CREATE TABLE IF NOT EXISTS pellier.persona_profiles (
    persona_id       TEXT PRIMARY KEY,
    customer_id      TEXT NOT NULL UNIQUE
                     REFERENCES pellier.customers(id) ON DELETE CASCADE,
    display_name     TEXT NOT NULL,
    role_tag         TEXT NOT NULL,
    blurb            TEXT NOT NULL,
    avatar_color     TEXT NOT NULL,
    avatar_initial   TEXT NOT NULL,
    membership       TEXT NOT NULL
                     CHECK (membership IN ('registered', 'circle', 'maison')),
    visit_count      INTEGER NOT NULL DEFAULT 0 CHECK (visit_count >= 0),
    last_seen_at     TIMESTAMPTZ,
    hero_image       TEXT NOT NULL,
    hero_alt         TEXT NOT NULL,
    hero_subheadline TEXT NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

DROP TRIGGER IF EXISTS persona_profiles_set_updated_at
    ON pellier.persona_profiles;
CREATE TRIGGER persona_profiles_set_updated_at
    BEFORE UPDATE ON pellier.persona_profiles
    FOR EACH ROW EXECUTE FUNCTION pellier.set_updated_at();

INSERT INTO pellier.persona_profiles (
    persona_id, customer_id, display_name, role_tag, blurb, avatar_color,
    avatar_initial, membership, visit_count, last_seen_at, hero_image,
    hero_alt, hero_subheadline
) VALUES
    (
        'fresh', 'CUST-FRESH', 'Pellier guest', 'New visitor',
        'A new visitor exploring the current Pellier collection.',
        '#4D3A30', 'P', 'registered', 0, NULL,
        '/products/landing-hero-weekender.webp',
        'Leather weekender on a travertine bench beside linen and an olive branch',
        'Explore the current collection, then ask the concierge about a piece or occasion.'
    ),
    (
        'marco', 'CUST-MARCO', 'Marco', 'Returning',
        'Brooklyn-based, partial to natural fibers. Last visit, three weeks ago. Bought the oat Maren tunic.',
        '#5a3528', 'M', 'maison', 11, now() - interval '21 days',
        '/products/hero-marco.webp',
        'Leather weekender and folded linen shirts in warm daylight',
        'Marco’s profile is grounded in Aurora orders, preferences, and current inventory.'
    ),
    (
        'anna', 'CUST-ANNA', 'Anna', 'Gift-giver',
        'Buys for others — partner, mother, friends. Recent searches lean milestone.',
        '#6b3d2a', 'A', 'circle', 6, now() - interval '9 days',
        '/products/hero-anna.webp',
        'Wrapped gift, beeswax candles, and ceramic ring dish',
        'Anna’s profile is grounded in Aurora orders, preferences, and current catalog signals.'
    ),
    (
        'theo', 'CUST-THEO', 'Theo', 'Home + slow craft',
        'Keeps a short list of quiet pieces — ceramics, linen throws, stoneware. Finishes what he buys, slowly.',
        '#5a4535', 'T', 'registered', 8, now() - interval '14 days',
        '/products/hero-theo.webp',
        'Stoneware pour-over set on a sunlit wooden table',
        'Theo’s profile is grounded in Aurora orders, support history, and return policy.'
    )
ON CONFLICT (persona_id) DO UPDATE SET
    customer_id = EXCLUDED.customer_id,
    display_name = EXCLUDED.display_name,
    role_tag = EXCLUDED.role_tag,
    blurb = EXCLUDED.blurb,
    avatar_color = EXCLUDED.avatar_color,
    avatar_initial = EXCLUDED.avatar_initial,
    membership = EXCLUDED.membership,
    visit_count = EXCLUDED.visit_count,
    last_seen_at = EXCLUDED.last_seen_at,
    hero_image = EXCLUDED.hero_image,
    hero_alt = EXCLUDED.hero_alt,
    hero_subheadline = EXCLUDED.hero_subheadline;

CREATE TABLE IF NOT EXISTS pellier.shopper_sessions (
    session_id TEXT PRIMARY KEY,
    persona_id TEXT NOT NULL
               REFERENCES pellier.persona_profiles(persona_id)
               ON DELETE RESTRICT,
    customer_id TEXT NOT NULL
                REFERENCES pellier.customers(id)
                ON DELETE RESTRICT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at TIMESTAMPTZ,
    CHECK (length(session_id) >= 33)
);

CREATE INDEX IF NOT EXISTS shopper_sessions_persona_started_idx
    ON pellier.shopper_sessions (persona_id, started_at DESC);

CREATE TABLE IF NOT EXISTS pellier.workshop_scenarios (
    scenario_id BIGSERIAL PRIMARY KEY,
    persona_id TEXT NOT NULL
               REFERENCES pellier.persona_profiles(persona_id)
               ON DELETE CASCADE,
    ordinal SMALLINT NOT NULL CHECK (ordinal BETWEEN 1 AND 5),
    prompt TEXT NOT NULL CHECK (length(trim(prompt)) > 0),
    preview_product_id TEXT
                       REFERENCES pellier.product_catalog("productId")
                       ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (persona_id, ordinal)
);

DROP TRIGGER IF EXISTS workshop_scenarios_set_updated_at
    ON pellier.workshop_scenarios;
CREATE TRIGGER workshop_scenarios_set_updated_at
    BEFORE UPDATE ON pellier.workshop_scenarios
    FOR EACH ROW EXECUTE FUNCTION pellier.set_updated_at();

INSERT INTO pellier.workshop_scenarios (
    persona_id, ordinal, prompt, preview_product_id
) VALUES
    ('fresh', 1, 'A considered carry-all for a long weekend.', '10'),
    ('fresh', 2, 'Pieces for slow Sunday mornings', '8'),
    ('fresh', 3, 'Something to wear for warm evenings out', '2'),
    ('fresh', 4, 'Linen pieces that travel well', '3'),
    ('fresh', 5, 'A cozy layer for cooler nights', '8'),
    ('marco', 1, 'What linen do you have for 10 days in Goa?', '11'),
    ('marco', 2, 'Build a carry-on wardrobe around what I already own.', '12'),
    ('marco', 3, 'What is the value range for the pieces you picked?', '17'),
    ('marco', 4, 'Is the Kyoto Linen Overshirt in cedar, size M, on the floor?', '14'),
    ('marco', 5, 'Connect me with a stylist for my brother’s wedding.', '19'),
    ('anna', 1, 'A thoughtful gift for someone who loves morning rituals', '22'),
    ('anna', 2, 'Something beautiful under $100', '24'),
    ('anna', 3, 'Help me pair a candle with something else', '21'),
    ('anna', 4, 'Wrap-ready gifts with no extra effort', '26'),
    ('anna', 5, 'I need a human to help with a sympathy gift.', '28'),
    ('theo', 1, 'A pour-over set with a little patina', '31'),
    ('theo', 2, 'Pair it with something for a slow Sunday breakfast.', '32'),
    ('theo', 3, 'Washed linen for every season, not a wardrobe.', '35'),
    ('theo', 4, 'The Wabi-Sabi Bowl arrived chipped. Can I start a return?', '37'),
    ('theo', 5, 'Can a person help with an exception return?', '38')
ON CONFLICT (persona_id, ordinal) DO UPDATE SET
    prompt = EXCLUDED.prompt,
    preview_product_id = EXCLUDED.preview_product_id;

COMMIT;
