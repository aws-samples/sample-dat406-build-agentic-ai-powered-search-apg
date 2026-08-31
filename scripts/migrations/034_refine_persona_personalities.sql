-- Migration 034: replace lifecycle labels with editorial personalities.
--
-- The persona selector is a shopping entry point, so its concise descriptor
-- should explain taste rather than account status. Keep the detailed Aurora
-- profile blurb unchanged for surfaces that need visit and order context.

\set ON_ERROR_STOP on

BEGIN;

UPDATE pellier.persona_profiles AS profile
   SET role_tag = personality.role_tag
  FROM (
      VALUES
          ('marco', 'Travel, utility, leather, linen'),
          ('anna', 'Gifting, ceremony, silk, glass'),
          ('theo', 'Slow living, craft, stoneware, natural materials')
  ) AS personality(persona_id, role_tag)
 WHERE profile.persona_id = personality.persona_id
   AND profile.role_tag IS DISTINCT FROM personality.role_tag;

DO $$
DECLARE
    mismatched_count INTEGER;
BEGIN
    SELECT count(*)
      INTO mismatched_count
      FROM (
          VALUES
              ('marco', 'Travel, utility, leather, linen'),
              ('anna', 'Gifting, ceremony, silk, glass'),
              ('theo', 'Slow living, craft, stoneware, natural materials')
      ) AS expected(persona_id, role_tag)
      LEFT JOIN pellier.persona_profiles AS actual
        ON actual.persona_id = expected.persona_id
       AND actual.role_tag = expected.role_tag
     WHERE actual.persona_id IS NULL;

    IF mismatched_count <> 0 THEN
        RAISE EXCEPTION
            'Expected all three editorial persona personalities; % are missing or mismatched',
            mismatched_count;
    END IF;
END $$;

COMMIT;
