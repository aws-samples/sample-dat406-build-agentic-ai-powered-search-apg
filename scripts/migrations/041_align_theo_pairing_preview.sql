-- Migration 041: align Theo's authored pairing preview with the governed
-- retrieval outcome.
--
-- Ceramic Tumblers are the top vector neighbor of the Pour-Over Set, but
-- Theo already owns them. The guided result must teach the next valid
-- selection: the first novel companion returned by the same Aurora query.

\set ON_ERROR_STOP on

BEGIN;

UPDATE pellier.workshop_scenarios
   SET preview_product_id = '34'
 WHERE persona_id = 'theo'
   AND ordinal IN (2, 4);

DO $$
DECLARE
    exercise_preview TEXT;
    continuation_preview TEXT;
BEGIN
    SELECT preview_product_id
      INTO exercise_preview
      FROM pellier.workshop_scenarios
     WHERE persona_id = 'theo'
       AND ordinal = 2
       AND journey_role = 'required'
       AND journey_stage = 'exercise';

    SELECT preview_product_id
      INTO continuation_preview
      FROM pellier.workshop_scenarios
     WHERE persona_id = 'theo'
       AND ordinal = 4
       AND journey_role = 'explore';

    IF exercise_preview IS DISTINCT FROM '34'
       OR continuation_preview IS DISTINCT FROM '34' THEN
        RAISE EXCEPTION
            'Theo pairing scenarios must preview the novel Terracotta Planter result';
    END IF;
END $$;

COMMIT;
