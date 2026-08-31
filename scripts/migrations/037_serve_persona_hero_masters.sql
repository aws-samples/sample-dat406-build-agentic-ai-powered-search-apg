-- Migration 037: serve approved persona hero PNG masters directly.
--
-- The final generated hero files are already sized for the full-bleed slot.
-- Keep Aurora's image contract on those lossless masters rather than routing
-- the primary scene through compressed responsive derivatives.

\set ON_ERROR_STOP on

BEGIN;

UPDATE pellier.persona_profiles AS profile
   SET hero_image = hero.hero_image
  FROM (
      VALUES
          ('marco', '/products/hero-marco.png'),
          ('anna', '/products/hero-anna.png'),
          ('theo', '/products/hero-theo.png')
  ) AS hero(persona_id, hero_image)
 WHERE profile.persona_id = hero.persona_id
   AND profile.hero_image IS DISTINCT FROM hero.hero_image;

DO $$
DECLARE
    mismatched_count INTEGER;
BEGIN
    SELECT count(*)
      INTO mismatched_count
      FROM (
          VALUES
              ('marco', '/products/hero-marco.png'),
              ('anna', '/products/hero-anna.png'),
              ('theo', '/products/hero-theo.png')
      ) AS expected(persona_id, hero_image)
      LEFT JOIN pellier.persona_profiles AS actual
        ON actual.persona_id = expected.persona_id
       AND actual.hero_image = expected.hero_image
     WHERE actual.persona_id IS NULL;

    IF mismatched_count <> 0 THEN
        RAISE EXCEPTION
            'Expected all three approved persona hero masters; % are missing or mismatched',
            mismatched_count;
    END IF;
END $$;

COMMIT;
