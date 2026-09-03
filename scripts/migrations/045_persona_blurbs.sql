-- 045: persona chooser blurbs that match the seeded orders and the voice rules.
--
-- The 029 blurbs predate the catalog: Marco "bought the oat Maren tunic", a
-- product that has never existed in pellier.product_catalog, and Anna's and
-- Theo's lines carry em dashes, which VOICE.md bans in shopper-facing copy.
-- Marco's seven orders (003_persona_seed) run from linen shirts to a leather
-- holdall and travel socks; the blurb now says that. Idempotent.

UPDATE pellier.persona_profiles
   SET blurb = 'Brooklyn-based, partial to natural fibers. Seven orders of linen and leather, the latest for travel.'
 WHERE persona_id = 'marco';

UPDATE pellier.persona_profiles
   SET blurb = 'Buys for others: partner, mother, friends. Recent searches lean milestone.'
 WHERE persona_id = 'anna';

UPDATE pellier.persona_profiles
   SET blurb = 'Keeps a short list of quiet pieces: ceramics, linen throws, stoneware. Finishes what he buys, slowly.'
 WHERE persona_id = 'theo';
