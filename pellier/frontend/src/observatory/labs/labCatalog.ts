export const LAB_EXERCISE_IDS = [
  'grounded-inventory',
  'retrieval-acceptance',
  'exactly-once-return',
  'fail-closed-policy',
  'governed-evidence-bundle',
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
    title: 'Grounded Inventory Contract',
    shortTitle: 'Grounded inventory',
    summary:
      'Build a typed inventory snapshot and reconcile the catalog with the warehouse ledger before the answer is trusted.',
    image: '/products/marco-linen-overshirt-sage-960.avif',
    imageWidth: 960,
    imageHeight: 1200,
    proofCardIds: ['marco-floor-check'],
    objective:
      'Make the Inventory Agent return a scoped inventory fact that can be checked against live Aurora rows.',
    participantTodo:
      'Implement the inventory tool contract, preserve warehouse identity, and add a reconciliation query for the requested SKU.',
    command:
      'curl -sN http://localhost:8000/api/chat/stream \\\n  -H "Content-Type: application/json" \\\n  -H "Authorization: Bearer $ACCESS_TOKEN" \\\n  -d \'{"message":"Marco needs the floor count for the Kyoto Linen Overshirt in cedar, size M","conversation_history":[],"session_id":"marco-proof"}\'',
    measurements: {
      before: {
        label: 'Before',
        value: 'The answer is bounded or the catalog and warehouse totals are not reconciled.',
      },
      after: {
        label: 'Acceptance target',
        value: 'The scoped catalog quantity equals the warehouse-ledger sum for the same product.',
      },
    },
    evidenceAssertion:
      'One scoped invocation identifies the product and warehouses, reports live Aurora values, and links execution telemetry without treating telemetry as authorization proof.',
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
    title: 'Retrieval Acceptance Gate',
    shortTitle: 'Retrieval gate',
    summary:
      'Complete hybrid retrieval, bound the corpus and filters, then choose a strategy with measured quality, latency, and cost.',
    image: '/products/anna-ceramic-bud-vase-960.webp',
    imageWidth: 960,
    imageHeight: 1200,
    proofCardIds: ['retrieval-comparison'],
    objective:
      'Make vector, hybrid RRF, rerank, and agentic retrieval obey one shopper-facing corpus and stock contract.',
    participantTodo:
      'Complete the hybrid/RRF path, expose bounded parameters, and define a threshold that the experiment can pass or fail.',
    command:
      'curl -s "http://localhost:8000/api/observatory/search-strategies/compare?query=A%20milestone%20gift%20for%20a%20new%20homeowner"',
    measurements: {
      before: {
        label: 'Before',
        value: 'Strategy choice is based on an unmeasured result or inconsistent corpus filters.',
      },
      after: {
        label: 'Acceptance target',
        value: 'One bounded comparison reports quality, latency, cost model, corpus, filters, and model provenance.',
      },
    },
    evidenceAssertion:
      'The selected strategy passes a declared threshold and exposes the raw plan, returned products, model IDs, and filter contract.',
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
    id: 'exactly-once-return',
    number: '03',
    title: 'Exactly-Once Return and Evidence Contract',
    shortTitle: 'Exactly-once return',
    summary:
      'Add idempotency, order-line locking, and an atomic activity receipt so retries cannot duplicate a return.',
    image: '/products/theo-ceramic-tumblers-960.webp',
    imageWidth: 960,
    imageHeight: 1200,
    proofCardIds: ['managed-rail', 'audit-ledger'],
    objective:
      'Prove that concurrent retries produce one business mutation and one durable activity record.',
    participantTodo:
      'Bind the return to an order line, enforce remaining returnable quantity, and write the mutation, activity receipt, and outbox intent in one Aurora transaction.',
    command:
      'psql "$DATABASE_URL" -c "SELECT audit_id, session_id, tool, caller, args, result FROM pellier.tool_audit WHERE tool = \'initiate_return\' ORDER BY audit_id DESC LIMIT 3;"',
    measurements: {
      before: {
        label: 'Before',
        value: 'A retry can replay the mutation, and execution telemetry can be missing after commit.',
      },
      after: {
        label: 'Acceptance target',
        value: 'Concurrent duplicate requests yield one mutation, one activity receipt, and one outbox record.',
      },
    },
    evidenceAssertion:
      'The same invocation key correlates the order-line result, transaction state, immutable receipt, outbox row, and execution telemetry.',
    decisionPrompt:
      'Which facts must commit together, and which managed evidence can be correlated only after the transaction?',
    primaryAction: {
      label: 'Inspect managed evidence',
      to: '/observatory/proof-board#managed-rail',
    },
    supportingActions: [
      {
        label: 'Inspect audit ledger',
        to: '/observatory/proof-board#audit-ledger',
      },
      {
        label: 'Open write-path reference',
        to: '/observatory/write-path',
      },
    ],
  },
  {
    id: 'fail-closed-policy',
    number: '04',
    title: 'Fail-Closed Identity Policy and Aurora Backstop',
    shortTitle: 'Fail-closed policy',
    summary:
      'Derive customer identity from verified claims, enforce the policy matrix, and block database bypass with an Aurora backstop.',
    image: '/products/hero-theo-960.webp',
    imageWidth: 960,
    imageHeight: 540,
    proofCardIds: ['runtime-gateway-policy'],
    objective:
      'Prove that missing identity or a policy outage cannot select a less-governed mutation path.',
    participantTodo:
      'Complete the Cedar ownership rules, deny missing claims, and add a narrow database role with RLS or a constrained procedure.',
    command:
      'grep -E "COGNITO|AGENTCORE_(RUNTIME|GATEWAY|POLICY)" pellier/backend/.env',
    measurements: {
      before: {
        label: 'Before',
        value: 'Configuration readiness is visible, but it does not prove an authoritative policy decision or blocked execution.',
      },
      after: {
        label: 'Acceptance target',
        value: 'The policy matrix records authoritative ALLOW and DENY events, exact invocation correlation, and the Aurora outcome.',
      },
    },
    evidenceAssertion:
      'A DENY is proven only by an authoritative provider decision tied to the exact invocation and a correlated zero-execution result.',
    decisionPrompt:
      'What remains protected when Cognito, Gateway, Policy, or telemetry is unavailable?',
    primaryAction: {
      label: 'Open policy and write path',
      to: '/observatory/write-path',
    },
    supportingActions: [
      {
        label: 'Inspect policy checkpoint',
        to: '/observatory/proof-board#runtime-gateway-policy',
      },
      {
        label: 'Open production patterns',
        to: '/observatory/production-patterns',
      },
    ],
  },
  {
    id: 'governed-evidence-bundle',
    number: '05',
    title: 'Governed Evidence Bundle and Failure Drill',
    shortTitle: 'Evidence bundle',
    summary:
      'Reconcile ALLOW, DENY, degraded execution, Aurora state, export delivery, and reset proof into one scoped bundle.',
    image: '/products/landing-approach-atelier-960.avif',
    imageWidth: 960,
    imageHeight: 540,
    proofCardIds: [],
    objective:
      'Export an immutable, participant-scoped evidence bundle only after every cross-layer identity and state link is reconciled.',
    participantTodo:
      'Add a scoped bundle endpoint and verifier before enabling export or claiming this exercise complete.',
    command:
      '# No scoped evidence-bundle endpoint exists yet.\n# Use the current Proof Board only to inspect individual checkpoints.',
    measurements: {
      before: {
        label: 'Current state',
        value: 'Individual global checkpoints exist, but no scoped immutable bundle can be exported or reconciled.',
      },
      after: {
        label: 'Acceptance target',
        value: 'ALLOW, DENY, and degraded drills produce a complete timeline with lag, duplicates, contradictions, and reset proof.',
      },
    },
    evidenceAssertion:
      'The bundle preserves source boundaries and fails closed when identity, invocation, policy, execution, transaction, outbox, export, or reset evidence is missing.',
    decisionPrompt:
      'Which missing link makes the entire bundle unknown rather than partially verified?',
    supportingActions: [
      {
        label: 'Inspect current proof board',
        to: '/observatory/proof-board',
      },
      {
        label: 'Open references',
        to: '/observatory/references',
      },
    ],
    unavailableReason:
      'Bundle export remains unavailable until a participant-scoped endpoint and verifier exist.',
  },
] as const;

const LAB_BY_ID = new Map(LAB_EXERCISES.map((exercise) => [exercise.id, exercise]));

export function findLabExercise(id: string | undefined): LabExercise | undefined {
  return id ? LAB_BY_ID.get(id as LabExerciseId) : undefined;
}
