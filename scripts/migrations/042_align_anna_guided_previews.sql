-- Migration 042: keep Anna's Lab 2 journey honest about what each turn can
-- actually show.
--
-- Turn two's grounded live result is the Leather Journal. Turn three reaches
-- the intentionally unbuilt Inventory Agent, so it has no catalog result to
-- preview until participants complete that build step.

\set ON_ERROR_STOP on

BEGIN;

UPDATE pellier.workshop_scenarios
   SET preview_product_id = '28'
 WHERE persona_id = 'anna'
   AND ordinal = 2;

UPDATE pellier.workshop_scenarios
   SET preview_product_id = NULL
 WHERE persona_id = 'anna'
   AND ordinal = 3;

DO $$
DECLARE
    exercise_preview TEXT;
    proof_preview TEXT;
BEGIN
    SELECT preview_product_id
      INTO exercise_preview
      FROM pellier.workshop_scenarios
     WHERE persona_id = 'anna'
       AND ordinal = 2
       AND journey_role = 'required'
       AND journey_stage = 'exercise';

    SELECT preview_product_id
      INTO proof_preview
      FROM pellier.workshop_scenarios
     WHERE persona_id = 'anna'
       AND ordinal = 3
       AND journey_role = 'required'
       AND journey_stage = 'prove';

    IF exercise_preview IS DISTINCT FROM '28'
       OR proof_preview IS NOT NULL THEN
        RAISE EXCEPTION
            'Anna Lab 2 must preview the live retrieval result and the unbuilt inventory checkpoint';
    END IF;
END $$;

COMMIT;
