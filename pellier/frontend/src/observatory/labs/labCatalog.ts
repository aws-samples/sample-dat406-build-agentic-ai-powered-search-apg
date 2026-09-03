export const LAB_EXERCISE_IDS = [
  'grounded-inventory',
  'retrieval-acceptance',
  'managed-agent-path',
  'fail-closed-policy',
] as const;

export type LabExerciseId = (typeof LAB_EXERCISE_IDS)[number];

export interface LabAction {
  label: string;
  to: string;
}

export interface LabMeasurement {
  label: string;
  value: string;
}

export interface LabExercise {
  id: LabExerciseId;
  number: string;
  anchorName: 'Marco' | 'Anna' | 'Theo' | 'Jessica';
  title: string;
  shortTitle: string;
  summary: string;
  image: string;
  imageWidth: number;
  imageHeight: number;
  proofCardIds: string[];
  objective: string;
  participantTodo: string;
  command: string;
  measurements: {
    before: LabMeasurement;
    after: LabMeasurement;
  };
  evidenceAssertion: string;
  decisionPrompt: string;
  primaryAction?: LabAction;
  supportingActions: LabAction[];
  unavailableReason?: string;
}

export const LAB_EXERCISES: readonly LabExercise[] = [
  {
    id: 'grounded-inventory',
    number: '01',
    anchorName: 'Marco',
    title: 'Build a PostgreSQL-Grounded Agent',
    shortTitle: 'PostgreSQL-grounded agent',
    summary:
      'Complete the Inventory Agent and its Aurora tool, then prove the answer against the exact warehouse rows and execution receipt.',
    image: '/assets/personas/marco-720.webp',
    imageWidth: 720,
    imageHeight: 1080,
    proofCardIds: ['marco-floor-check'],
    objective:
      'Select Marco in the Storefront scenario switcher before the three-turn journey begins.',
    participantTodo:
      'Complete the two marked source regions, verify both build markers, and replay Marco\'s warehouse request under a unique session.',
    command:
      'psql -X -v ON_ERROR_STOP=1 -P pager=off -c "\nSELECT p.product_id, p.quantity AS catalog_units,\n       sum(wi.quantity)::int AS warehouse_units,\n       p.quantity = sum(wi.quantity) AS reconciled\n  FROM pellier.product_catalog p\n  JOIN pellier.warehouse_inventory wi USING (product_id)\n WHERE p.product_id = \'2\'\n GROUP BY p.product_id, p.quantity;"',
    measurements: {
      before: {
        label: 'Before',
        value: 'The answer is bounded or the catalog and warehouse totals are not reconciled.',
      },
      after: {
        label: 'Acceptance target',
        value: 'Both markers are shipped, Marco receives live warehouse facts, and one session-scoped audit row exists.',
      },
    },
    evidenceAssertion:
      'One session-scoped invocation identifies the requested product and warehouse, reports live Aurora values, and links exactly one check_inventory execution row.',
    decisionPrompt:
      'Which table owns inventory truth, and what invariant prevents the aggregate and warehouse ledger from drifting?',
    primaryAction: {
      label: 'Open live workbench',
      to: '/observatory/workbench',
    },
    supportingActions: [
      {
        label: 'Inspect inventory proof',
        to: '/observatory/proof-board#marco-floor-check',
      },
      {
        label: 'Open tool reference',
        to: '/observatory/tools',
      },
    ],
  },
  {
    id: 'retrieval-acceptance',
    number: '02',
    anchorName: 'Anna',
    title: 'Build and Measure PostgreSQL Hybrid Retrieval',
    shortTitle: 'PostgreSQL retrieval',
    summary:
      'Author the RRF expression, reconstruct vector, FTS, fusion, and rerank evidence, then verify PostgreSQL enforced eligibility.',
    image: '/assets/personas/anna-720.webp',
    imageWidth: 720,
    imageHeight: 1080,
    proofCardIds: ['retrieval-comparison'],
    objective:
      'With Anna selected, author the PostgreSQL RRF expression, then separate model proposals from SQL enforcement.',
    participantTodo:
      'Complete the PostgreSQL RRF worksheet, run Anna\'s bounded request, and prove the fused ranks and returned product IDs satisfy the SQL contract.',
    command:
      'psql -X -v ON_ERROR_STOP=1 -P pager=off -c "\nSELECT receipt_id, hard_constraints, retrieval_config,\n       latency_breakdown, modeled_cost_usd\n  FROM pellier.retrieval_receipts\n ORDER BY receipt_id DESC\n LIMIT 1;"',
    measurements: {
      before: {
        label: 'Before',
        value: 'Strategy choice is based on an unmeasured result or inconsistent corpus filters.',
      },
      after: {
        label: 'Acceptance target',
        value: 'One receipt exposes branch ranks, RRF, rerank, observed latency, modeled cost, returned products, and enforced eligibility.',
      },
    },
    evidenceAssertion:
      'SQL recomputes the recorded RRF contribution and finds no price, stock, or archive violation in the exact returned IDs.',
    decisionPrompt:
      'Which measured tradeoff justifies the selected strategy for this query class?',
    primaryAction: {
      label: 'Open retrieval comparison',
      to: '/observatory/performance',
    },
    supportingActions: [
      {
        label: 'Inspect retrieval proof',
        to: '/observatory/proof-board#retrieval-comparison',
      },
      {
        label: 'Open search reference',
        to: '/observatory/search',
      },
    ],
  },
  {
    id: 'managed-agent-path',
    number: '03',
    anchorName: 'Theo',
    title: 'Operate and Observe the AgentCore Managed Path',
    shortTitle: 'AgentCore managed path',
    summary:
      'Operate Runtime, Gateway, and Memory for Theo\'s three-turn thread, then author an OpenTelemetry trace contract and correlate the managed evidence.',
    image: '/assets/personas/theo-720.webp',
    imageWidth: 720,
    imageHeight: 1080,
    proofCardIds: ['managed-rail', 'audit-ledger'],
    objective:
      'With Theo selected, author the OTEL predicates, then prove Gateway, fresh-process Memory, and correlated spans across his managed thread.',
    participantTodo:
      'Invoke Runtime as Theo, complete the OTEL trace contract, run his three-turn Storefront thread, and verify Memory from a separate process.',
    command:
      'cd .agentcore-project/pellier\nnpx -y @aws/agentcore@0.26.0 invoke \\\n  --runtime pellier_orchestrator \\\n  --session-id "$RUNTIME_SESSION" \\\n  --bearer-token "$PELLIER_TOKEN" \\\n  --prompt "Hand-thrown ceramics for a slower morning routine" \\\n  --json',
    measurements: {
      before: {
        label: 'Before',
        value: 'A successful answer alone does not prove Runtime, Gateway, managed Memory, or trace continuity.',
      },
      after: {
        label: 'Acceptance target',
        value: 'Runtime reports gateway-mcp, fresh-process Memory recalls the turn, and one trace carries agent, model, and tool spans.',
      },
    },
    evidenceAssertion:
      'The Runtime receipt, Memory verifier, and trace assertions all pass; SQL separately reconstructs the principal, requested customer, policy receipt, and execution row.',
    decisionPrompt:
      'Which artifact proves each managed boundary, and which claims remain unproven when one artifact is missing?',
    primaryAction: {
      label: 'Open live workbench',
      to: '/observatory/workbench',
    },
    supportingActions: [
      {
        label: 'Inspect managed evidence',
        to: '/observatory/proof-board#managed-rail',
      },
      {
        label: 'Inspect live sessions',
        to: '/observatory/sessions',
      },
    ],
  },
  {
    id: 'fail-closed-policy',
    number: '04',
    anchorName: 'Jessica',
    title: 'Enforce Identity and Prove Non-Execution',
    shortTitle: 'Identity and non-execution',
    summary:
      'Bind verified identity in Cedar, prove the four-case execution matrix and Aurora RLS backstop, then investigate Jessica\'s case as separately authorized staff.',
    image: '/assets/personas/jessica-720.webp',
    imageWidth: 720,
    imageHeight: 900,
    proofCardIds: ['runtime-gateway-policy'],
    objective:
      'Use Marco, Anna, and Jessica to prove the customer boundary from Cognito through Cedar, execution receipts, PostgreSQL RLS, and the Operator checkpoint.',
    participantTodo:
      'Complete and deploy the Cedar rule, run the four-case identity matrix, prove RLS read and write behavior, complete Jessica\'s three-turn Operator investigation, stop at human review, and reset the policy.',
    command:
      'python3 scripts/prove_identity_boundary.py \\\n  --json /tmp/pellier-evidence/lab-4.json\npsql -X -v ON_ERROR_STOP=1 -P pager=off \\\n  -f workshop/lab-4-rls.sql',
    measurements: {
      before: {
        label: 'Before',
        value: 'The baseline policy does not bind the verified username to the requested Aurora customer.',
      },
      after: {
        label: 'Acceptance target',
        value: 'Both mismatches deny without execution, Jessica executes once and replays safely, RLS proves read and write scope, and Operator stops before approval.',
      },
    },
    evidenceAssertion:
      'The keyed matrix distinguishes policy, execution, write, and durable effect; the RLS worksheet proves an independent database boundary; Jessica\'s staff investigation remains pending at the human checkpoint.',
    decisionPrompt:
      'Which layer proves identity, authorization, execution, database scope, and human approval, and what remains unproven if any layer is missing?',
    primaryAction: {
      label: 'Open Jessica in Operator',
      to: '/operator/clients/CUST-JESSICA?guided=service-recovery#operator-concierge-title',
    },
    supportingActions: [
      {
        label: 'Open policy and write path',
        to: '/observatory/write-path',
      },
      {
        label: 'Inspect policy checkpoint',
        to: '/observatory/proof-board#runtime-gateway-policy',
      },
    ],
  },
] as const;

const LAB_BY_ID = new Map(LAB_EXERCISES.map((exercise) => [exercise.id, exercise]));
const LEGACY_LAB_ALIASES = new Map<string, LabExerciseId>([
  ['exactly-once-return', 'managed-agent-path'],
]);

export function findLabExercise(id: string | undefined): LabExercise | undefined {
  if (!id) return undefined;
  const canonicalId = LEGACY_LAB_ALIASES.get(id) ?? (id as LabExerciseId);
  return LAB_BY_ID.get(canonicalId);
}
