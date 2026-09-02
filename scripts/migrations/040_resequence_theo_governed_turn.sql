-- Migration 040: make Theo's governed return the required Lab 3 close.
--
-- The original live-surface seed used the managed-memory continuity prompt as
-- turn three and hid the governed damaged-return path in Explore. That left
-- the actual Lab 3 outcome disconnected from the participant's required
-- three-turn journey. Keep the continuity proof as an optional follow-up, and
-- make the return the authored outcome of the managed path.

\set ON_ERROR_STOP on

BEGIN;

UPDATE pellier.workshop_scenarios
   SET preview_product_id = '34'
 WHERE persona_id = 'theo'
   AND ordinal = 2;

UPDATE pellier.workshop_scenarios
   SET prompt = 'My Wabi-Sabi Bowl arrived chipped. Please help me return it.',
       journey_role = 'required',
       journey_stage = 'prove',
       preview_product_id = '37'
 WHERE persona_id = 'theo'
   AND ordinal = 3;

UPDATE pellier.workshop_scenarios
   SET prompt = 'Without asking me to repeat the ritual or material, which pairing should I choose and why?',
       journey_role = 'explore',
       journey_stage = NULL,
       preview_product_id = '34'
 WHERE persona_id = 'theo'
   AND ordinal = 4;

DO $$
DECLARE
    exercise_preview TEXT;
    required_prompt TEXT;
    required_preview TEXT;
    optional_prompt TEXT;
    optional_preview TEXT;
BEGIN
    SELECT preview_product_id
      INTO exercise_preview
      FROM pellier.workshop_scenarios
     WHERE persona_id = 'theo'
       AND ordinal = 2
       AND journey_role = 'required'
       AND journey_stage = 'exercise';

    SELECT prompt, preview_product_id
      INTO required_prompt, required_preview
      FROM pellier.workshop_scenarios
     WHERE persona_id = 'theo'
       AND ordinal = 3
       AND journey_role = 'required'
       AND journey_stage = 'prove';

    SELECT prompt, preview_product_id
      INTO optional_prompt, optional_preview
      FROM pellier.workshop_scenarios
     WHERE persona_id = 'theo'
       AND ordinal = 4
       AND journey_role = 'explore'
       AND journey_stage IS NULL;

    IF exercise_preview IS DISTINCT FROM '34'
       OR required_prompt IS DISTINCT FROM
       'My Wabi-Sabi Bowl arrived chipped. Please help me return it.'
       OR required_preview IS DISTINCT FROM '37'
       OR optional_prompt IS DISTINCT FROM
       'Without asking me to repeat the ritual or material, which pairing should I choose and why?'
       OR optional_preview IS DISTINCT FROM '34' THEN
        RAISE EXCEPTION
            'Theo Lab 3 sequence must close with the governed Wabi-Sabi Bowl return';
    END IF;
END $$;

COMMIT;
