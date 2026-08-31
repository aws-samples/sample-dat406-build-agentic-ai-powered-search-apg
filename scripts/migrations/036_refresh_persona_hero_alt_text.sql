-- Migration 036: align persona hero descriptions with the approved masters.
--
-- The full-bleed Marco, Anna, and Theo photographs were replaced with final
-- generated masters. Keep Aurora-owned alt text synchronized with the scenes
-- the responsive derivatives actually render.

\set ON_ERROR_STOP on

BEGIN;

UPDATE pellier.persona_profiles AS profile
   SET hero_alt = hero.hero_alt
  FROM (
      VALUES
          (
              'marco',
              'Leather weekender with folded linen and brass travel details in warm daylight'
          ),
          (
              'anna',
              'Ribbon-wrapped gift beside an amber candle, ceramic bud vase, and blank card'
          ),
          (
              'theo',
              'Charcoal stoneware bowl beside natural linen, a beeswax candle, and olive branches'
          )
  ) AS hero(persona_id, hero_alt)
 WHERE profile.persona_id = hero.persona_id
   AND profile.hero_alt IS DISTINCT FROM hero.hero_alt;

DO $$
DECLARE
    mismatched_count INTEGER;
BEGIN
    SELECT count(*)
      INTO mismatched_count
      FROM (
          VALUES
              (
                  'marco',
                  'Leather weekender with folded linen and brass travel details in warm daylight'
              ),
              (
                  'anna',
                  'Ribbon-wrapped gift beside an amber candle, ceramic bud vase, and blank card'
              ),
              (
                  'theo',
                  'Charcoal stoneware bowl beside natural linen, a beeswax candle, and olive branches'
              )
      ) AS expected(persona_id, hero_alt)
      LEFT JOIN pellier.persona_profiles AS actual
        ON actual.persona_id = expected.persona_id
       AND actual.hero_alt = expected.hero_alt
     WHERE actual.persona_id IS NULL;

    IF mismatched_count <> 0 THEN
        RAISE EXCEPTION
            'Expected all three approved hero descriptions; % are missing or mismatched',
            mismatched_count;
    END IF;
END $$;

COMMIT;
