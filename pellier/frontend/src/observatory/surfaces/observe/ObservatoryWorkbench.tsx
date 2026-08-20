import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import {
  Activity,
  Bot,
  Boxes,
  Brain,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronsDownUp,
  ChevronsUpDown,
  Copy,
  Database,
  Eye,
  Link2,
  PackagePlus,
  RotateCcw,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Wrench,
} from 'lucide-react';
import { usePersona } from '../../../contexts/PersonaContext';
import {
  Badge,
  Switch,
  ToggleGroup,
  ToggleGroupItem,
} from '../../../components/ui';
import ResponsiveImage from '../../../components/ResponsiveImage';
import {
  sendChatMessageStreaming,
  type ChatProduct,
  type ChatResponse,
  type OrchestrationPattern,
  type ResponseMode,
} from '../../../services/chat';
import ObservatoryCuratedTurns from './ObservatoryCuratedTurns';
import {
  OPERATOR_TURNS,
} from '../../../data/personaCurations';
import './ObservatoryIndex.css';
import './ObservatoryWorkbench.css';

export type RunStatus = 'idle' | 'running' | 'complete' | 'error';

type StepKind =
  | 'routing'
  | 'memory'
  | 'guardrail'
  | 'agent'
  | 'tool'
  | 'sql';

interface JourneyStep {
  id: string;
  kind: StepKind;
  title: string;
  detail: string;
  status: string;
  source?: string;
  meta?: string;
  sql?: string;
}

/**
 * Step kinds in the order a turn normally emits them. Used only for the empty
 * and pending skeleton, never presented as evidence that anything ran.
 */
const TRACE_SKELETON: StepKind[] = [
  'routing',
  'memory',
  'guardrail',
  'agent',
  'tool',
  'sql',
];

const TRACE_LINE_TOP = 28;

interface DbQuery {
  op?: string;
  table?: string;
  sql?: string;
  duration_ms?: number;
}

interface StreamEvent {
  type: string;
  content?: string;
  delta?: string;
  agent?: string;
  action?: string;
  status?: string;
  tool?: string;
  product?: unknown;
  queries?: DbQuery[];
  error?: string;
  message?: string;
  intent?: string;
  classifier?: string;
  response_mode?: ResponseMode;
  model_family?: 'opus' | 'sonnet';
  model_id?: string;
  routing?: {
    loaded_skills?: string[];
    considered?: Array<{ name?: string; reason?: string }>;
    elapsed_ms?: number;
  };
  memory?: {
    source?: string;
    customer_id?: string;
    facts_loaded?: number;
    orders_loaded?: number;
    applied?: boolean;
    turns_loaded?: number;
    turns_persisted?: number;
    namespace_scope?: string;
    read_status?: string;
    write_status?: string;
    action_status?: string;
    retry_recommended?: boolean;
    error_code?: string;
  };
  profile?: {
    source?: string;
    customer_id?: string | null;
    facts_available?: number;
    orders_available?: number;
    available?: boolean;
  };
  guardrail?: {
    allowed?: boolean;
    action?: string;
    violations?: number;
    mode?: string;
    enforced?: boolean;
  };
  response?: {
    response?: string;
    products?: unknown[];
    rail?: string;
    orchestration?: {
      pattern?: string;
      route?: string;
      router?: string;
    };
  };
}

interface ProfileContextReceipt {
  source?: string;
  customer_id?: string | null;
  facts_available?: number;
  facts_loaded?: number;
  orders_available?: number;
  orders_loaded?: number;
  available?: boolean;
  applied?: boolean;
}

interface IntentSignal {
  intent: string;
  classifier: string;
  responseMode: ResponseMode;
  modelFamily: 'opus' | 'sonnet';
  modelId: string;
}

interface VerifiedClaim {
  id: string;
  title: string;
  detail: string;
  /**
   * Ledger event this claim rests on. Present only when an emitted step
   * actually backs the claim, so a claim never advertises evidence that
   * cannot be opened.
   */
  stepId?: string;
}

function reconcileAgentResponse(current: string, candidate?: string): string {
  if (!candidate) return current;
  if (current && candidate.length < current.length * 0.5) return current;
  return candidate;
}

function mapProduct(value: unknown): ChatProduct {
  const product = (value ?? {}) as Record<string, any>;
  return {
    id: product.id ?? product.productId ?? 0,
    name: product.name ?? product.product_description ?? 'Catalog product',
    price: Number(product.price ?? 0),
    image:
      product.image ??
      product.imgUrl ??
      product.imgurl ??
      product.image_url ??
      '',
    category: product.category ?? product.category_name ?? '',
    rating: product.stars ?? product.rating,
    reviews: product.reviews,
    url: product.url ?? product.producturl,
    similarityScore:
      product.similarityScore ??
      product.similarity_score ??
      product.similarity ??
      product.relevance_score,
  };
}

function mergeProducts(current: ChatProduct[], incoming: unknown[]): ChatProduct[] {
  const next = [...current];
  incoming.map(mapProduct).forEach((product) => {
    const existingIndex = next.findIndex(
      (item) =>
        (product.id > 0 && item.id === product.id) ||
        (product.name && item.name === product.name),
    );
    if (existingIndex >= 0) next[existingIndex] = product;
    else next.push(product);
  });
  return next;
}

function productsForResponse(
  products: ChatProduct[],
  response: string,
): ChatProduct[] {
  const normalizedResponse = response.toLocaleLowerCase();
  const ranked = products.map((product, index) => ({
    product,
    index,
    mentionIndex: product.name
      ? normalizedResponse.indexOf(product.name.toLocaleLowerCase())
      : -1,
  }));
  const mentioned = ranked
    .filter((item) => item.mentionIndex >= 0)
    .sort((a, b) =>
      a.mentionIndex === b.mentionIndex
        ? a.index - b.index
        : a.mentionIndex - b.mentionIndex,
    )
    .map((item) => item.product);

  if (!mentioned.length) return products;

  const mentionedKeys = new Set(
    mentioned.map((product) => `${product.id}::${product.name}`),
  );
  return [
    ...mentioned,
    ...products.filter(
      (product) => !mentionedKeys.has(`${product.id}::${product.name}`),
    ),
  ];
}

function LabsProductCard({
  product,
  role,
}: {
  product: ChatProduct;
  role: 'best-match' | 'pairing';
}) {
  return (
    <article className="observatory-product" data-product-role={role}>
      <div className="observatory-product-media">
        {product.image ? (
          <ResponsiveImage
            src={product.image}
            alt={product.name}
            loading="lazy"
            decoding="async"
            sizes={
              role === 'best-match'
                ? '(max-width: 560px) 112px, (max-width: 959px) 44vw, 220px'
                : '(max-width: 560px) 90vw, (max-width: 959px) 44vw, 190px'
            }
          />
        ) : (
          <span aria-hidden="true">
            {product.name.charAt(0).toUpperCase()}
          </span>
        )}
      </div>
      <div className="observatory-product-copy">
        <small>{product.category || 'Catalog result'}</small>
        <h4>{product.name}</h4>
        <strong className="observatory-product-price">
          ${product.price.toFixed(2)}
        </strong>
        <dl className="observatory-product-evidence">
          {product.similarityScore !== undefined ? (
            <div>
              <dt>Similarity</dt>
              <dd>{product.similarityScore.toFixed(3)}</dd>
            </div>
          ) : null}
          {product.rating ? (
            <div>
              <dt>Rating</dt>
              <dd>
                {product.rating.toFixed(1)}
                {product.reviews ? ` (${product.reviews})` : ''}
              </dd>
            </div>
          ) : null}
        </dl>
      </div>
    </article>
  );
}

function formatElapsed(elapsedMs: number): string {
  if (elapsedMs < 1000) return `${Math.max(0, Math.round(elapsedMs))} ms`;
  return `${(elapsedMs / 1000).toFixed(1)} s`;
}

function statusLabel(status: RunStatus): string {
  if (status === 'running') return 'Running';
  if (status === 'complete') return 'Completed';
  if (status === 'error') return 'Error';
  return 'Ready';
}

function runProofSummary(
  runStatus: RunStatus,
  activeTurn: number | null,
  activeQuery: string | null,
  eventCount: number,
  agentCount: number,
  sqlCount: number,
  productCount: number,
): { label: string; summary: string } {
  const turnLabel = activeTurn === null ? 'This turn' : `Turn ${activeTurn + 1}`;

  if (runStatus === 'running') {
    return {
      label: `Following ${turnLabel.toLowerCase()}`,
      summary: activeQuery ?? 'Waiting for the first emitted event.',
    };
  }
  if (runStatus === 'complete') {
    return {
      label: 'Evidence captured',
      summary: `${eventCount} ${eventCount === 1 ? 'event' : 'events'}. ${agentCount} ${agentCount === 1 ? 'agent' : 'agents'}. ${sqlCount} SQL ${sqlCount === 1 ? 'query' : 'queries'}. ${productCount} ${productCount === 1 ? 'product' : 'products'}.`,
    };
  }
  if (runStatus === 'error') {
    return {
      label: `${turnLabel} needs attention`,
      summary: 'The stream stopped before the evidence trail completed.',
    };
  }
  return {
    label: 'Ready to inspect',
    summary: 'Choose one of five canonical shopper turns.',
  };
}

/** Metrics read "-" before a run so an untouched page shows no false zeroes. */
function metricValue(status: RunStatus, value: number | string): string {
  if (status === 'idle') return '-';
  return String(value);
}

function iconForStep(kind: StepKind) {
  if (kind === 'routing') return <Sparkles size={15} aria-hidden="true" />;
  if (kind === 'memory') return <Brain size={15} aria-hidden="true" />;
  if (kind === 'guardrail') return <ShieldCheck size={15} aria-hidden="true" />;
  if (kind === 'tool') return <Wrench size={15} aria-hidden="true" />;
  if (kind === 'sql') return <Database size={15} aria-hidden="true" />;
  return <Bot size={15} aria-hidden="true" />;
}

function patternLabel(pattern: string): string {
  if (pattern === 'dispatcher') return 'Dispatcher';
  if (pattern === 'agents_as_tools') return 'Agents-as-Tools';
  if (pattern === 'graph') return 'Graph';
  return pattern ? 'Unexpected pattern' : 'Server selected';
}

function errorMessage(error: unknown): string {
  if (error instanceof Error && error.message) return error.message;
  return 'The live agent run failed before completion.';
}

function labelIntent(intent: string): string {
  return intent
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function labelRail(rail: string): string {
  if (rail === 'gateway-mcp') return 'Gateway MCP';
  if (rail === 'in-process') return 'In process';
  if (rail === 'runtime') return 'AgentCore Runtime';
  return rail || 'Server selected';
}

function modelDisplayName(
  family: IntentSignal['modelFamily'],
  modelId: string,
): string {
  const familyLabel = family === 'opus' ? 'Opus' : 'Sonnet';
  const version = modelId
    .match(/claude-(?:opus|sonnet)-([0-9]+(?:-[0-9]+)?)/i)?.[1]
    ?.replace('-', '.');
  return `Claude ${familyLabel}${version ? ` ${version}` : ''}`;
}

/** Format only the displayed receipt; the captured SQL remains untouched. */
function formatSqlForDisplay(sql: string): string {
  return sql
    .trim()
    .replace(
      /\s+(FROM|WHERE|GROUP BY|ORDER BY|HAVING|LIMIT|OFFSET|RETURNING)\s+/gi,
      '\n$1 ',
    )
    .replace(/\s+(AND|OR)\s+/gi, '\n  $1 ');
}

function sqlBindingCount(sql: string): number {
  return sql.match(/%s|\$\d+/g)?.length ?? 0;
}

function toggleLabel(on: boolean): string {
  return on ? 'On' : 'Off';
}

/**
 * Assemble the "Why this answer" lines.
 *
 * Every clause restates a value the turn emitted: the routing decision, the
 * tools that ran, the number of Aurora receipts captured, and the rail that
 * served it. Nothing here is the model's own account of its reasoning, which
 * the backend does not expose and which would not be evidence if it did. A
 * clause is omitted rather than guessed when its signal is absent.
 */
interface RationaleInput {
  intentSignal: IntentSignal | null;
  toolNames: string[];
  sqlCount: number;
  executionRail: string;
  executionPattern: string | null;
  executionRoute: string | null;
}

function whyThisAnswer({
  intentSignal,
  toolNames,
  sqlCount,
  executionRail,
  executionPattern,
  executionRoute,
}: RationaleInput): string[] {
  const lines: string[] = [];

  if (intentSignal) {
    lines.push(
      `Classified as a ${labelIntent(intentSignal.intent)} request by the ${intentSignal.classifier} router, then composed by ${modelDisplayName(intentSignal.modelFamily, intentSignal.modelId)}.`,
    );
  }

  if (executionPattern) {
    lines.push(
      executionRoute
        ? `Dispatched through the ${patternLabel(executionPattern)} pattern to ${labelIntent(executionRoute)}.`
        : `Dispatched through the ${patternLabel(executionPattern)} pattern.`,
    );
  }

  if (toolNames.length) {
    lines.push(
      `Grounded by ${toolNames.length === 1 ? 'the tool' : 'the tools'} ${toolNames.join(', ')}.`,
    );
  }

  if (sqlCount) {
    lines.push(
      `Aurora returned ${sqlCount} query ${sqlCount === 1 ? 'receipt' : 'receipts'} on the ${executionRail} rail.`,
    );
  }

  return lines;
}

export default function ObservatoryWorkbench() {
  const { persona } = usePersona();
  const reduceMotion = useReducedMotion();
  const personaId = persona?.id ?? 'fresh';
  const [activeTurn, setActiveTurn] = useState<number | null>(null);
  const [activeOperatorTurn, setActiveOperatorTurn] = useState<number | null>(
    null,
  );
  const [activeQuery, setActiveQuery] = useState<string | null>(null);
  const [runStatus, setRunStatus] = useState<RunStatus>('idle');
  const [steps, setSteps] = useState<JourneyStep[]>([]);
  const [products, setProducts] = useState<ChatProduct[]>([]);
  const [agentResponse, setAgentResponse] = useState('');
  const [elapsedMs, setElapsedMs] = useState(0);
  const [runError, setRunError] = useState<string | null>(null);
  const [responseMode, setResponseMode] =
    useState<ResponseMode>('balanced');
  const [orchestrationPattern, setOrchestrationPattern] =
    useState<OrchestrationPattern>('dispatcher');
  const [profileEnabled, setProfileEnabled] = useState(Boolean(persona));
  const [guardrailsEnabled, setGuardrailsEnabled] = useState(false);
  // Whether the edit disclosure is open. The readout below restates every one
  // of these controls, which is the point when collapsed and pure duplication
  // when open: five facts, twice, adjacent. Tracking the disclosure lets the
  // readout stand down rather than argue with the controls it summarises.
  const [editingControls, setEditingControls] = useState(false);
  const [traceVisible, setTraceVisible] = useState(true);
  const [intentSignal, setIntentSignal] = useState<IntentSignal | null>(null);
  const [executionRail, setExecutionRail] = useState('Server selected');
  const [executionPattern, setExecutionPattern] = useState<string | null>(null);
  const [executionRoute, setExecutionRoute] = useState<string | null>(null);
  const [copiedSqlId, setCopiedSqlId] = useState<string | null>(null);
  /**
   * Per-receipt disclosure. Absent means "use the default", which opens the
   * newest Aurora receipt so a completed run shows its proof without a click.
   * A present value is an explicit participant choice and always wins.
   */
  const [receiptOverrides, setReceiptOverrides] = useState<
    Record<string, boolean>
  >({});
  const [linkedStepId, setLinkedStepId] = useState<string | null>(null);
  const startedAtRef = useRef<number | null>(null);
  const eventSequenceRef = useRef(0);
  const traceListRef = useRef<HTMLOListElement | null>(null);
  const currentTraceStepRef = useRef<HTMLLIElement | null>(null);
  const stepNodesRef = useRef(new Map<string, HTMLLIElement>());
  const linkTimerRef = useRef<number | null>(null);
  const [traceLineHeight, setTraceLineHeight] = useState(0);

  useEffect(() => {
    setActiveTurn(null);
    setActiveOperatorTurn(null);
    setActiveQuery(null);
    setRunStatus('idle');
    setSteps([]);
    setProducts([]);
    setAgentResponse('');
    setElapsedMs(0);
    setRunError(null);
    setProfileEnabled(Boolean(persona));
    setIntentSignal(null);
    setExecutionRail('Server selected');
    setExecutionPattern(null);
    setExecutionRoute(null);
    setCopiedSqlId(null);
    setReceiptOverrides({});
    setLinkedStepId(null);
  }, [personaId]);

  // A highlight timer that outlives its node would fire against a step from a
  // previous run, so it is cancelled on unmount.
  useEffect(
    () => () => {
      if (linkTimerRef.current !== null) {
        window.clearTimeout(linkTimerRef.current);
      }
    },
    [],
  );

  useEffect(() => {
    if (runStatus !== 'running') return undefined;
    const interval = window.setInterval(() => {
      if (startedAtRef.current !== null) {
        setElapsedMs(Date.now() - startedAtRef.current);
      }
    }, 100);
    return () => window.clearInterval(interval);
  }, [runStatus]);

  const updateAgentStep = (event: StreamEvent) => {
    const agent = event.agent || 'Agent';
    setSteps((current) => {
      const existingIndex = current.findIndex(
        (step) => step.kind === 'agent' && step.source === agent,
      );
      const next: JourneyStep = {
        id:
          existingIndex >= 0
            ? current[existingIndex].id
            : `agent-${eventSequenceRef.current++}`,
        kind: 'agent',
        title: agent,
        detail: event.action || 'Agent lifecycle update',
        status: event.status || 'in_progress',
        source: agent,
      };
      if (existingIndex < 0) return [...current, next];
      return current.map((step, index) => (index === existingIndex ? next : step));
    });
  };

  const addToolStep = (event: StreamEvent) => {
    const tool = event.tool || 'Tool';
    setSteps((current) => [
      ...current,
      {
        id: `tool-${eventSequenceRef.current++}`,
        kind: 'tool',
        title: tool,
        detail: 'Tool invocation emitted by the live agent',
        status: event.status || 'executing',
        source: tool,
      },
    ]);
  };

  const addRoutingStep = (event: StreamEvent) => {
    const loaded = event.routing?.loaded_skills ?? [];
    const considered = event.routing?.considered?.length ?? 0;
    setSteps((current) => [
      ...current,
      {
        id: `routing-${eventSequenceRef.current++}`,
        kind: 'routing',
        title: 'Skill routing',
        detail: loaded.length
          ? `Loaded ${loaded.join(', ')}`
          : 'No optional skills loaded for this turn',
        status: 'completed',
        meta: [
          considered ? `${considered} considered` : '',
          event.routing?.elapsed_ms !== undefined
            ? `${Math.round(event.routing.elapsed_ms)} ms`
            : '',
        ]
          .filter(Boolean)
          .join(' / '),
      },
    ]);
  };

  const addAuroraProfileStep = (event: StreamEvent) => {
    const profile: ProfileContextReceipt = event.profile ?? event.memory ?? {};
    const facts = profile.facts_available ?? profile.facts_loaded ?? 0;
    const orders = profile.orders_available ?? profile.orders_loaded ?? 0;
    const live = profile.source === 'aurora';
    const available =
      profile.available ?? (live && profile.applied !== false);
    const legacyMemoryEvent = !event.profile;
    setSteps((current) => [
      ...current,
      {
        id: `memory-${eventSequenceRef.current++}`,
        kind: 'memory',
        title: 'Aurora profile context',
        detail: live && available
          ? `${facts} profile ${facts === 1 ? 'fact' : 'facts'} and ${orders} past ${orders === 1 ? 'order' : 'orders'} ${legacyMemoryEvent ? 'loaded' : 'available'}`
          : 'No live Aurora profile context was available for this turn',
        status: live && available ? 'completed' : 'unavailable',
        meta: [profile.source || 'unavailable', profile.customer_id || '']
          .filter(Boolean)
          .join(' / '),
      },
    ]);
  };

  const addAgentCoreMemoryStep = (event: StreamEvent) => {
    const memory = event.memory ?? {};
    const loaded = memory.turns_loaded ?? 0;
    const persisted = memory.turns_persisted ?? 0;
    const writeFailed = memory.write_status === 'failed';
    setSteps((current) => [
      ...current,
      {
        id: `agentcore-memory-${eventSequenceRef.current++}`,
        kind: 'memory',
        title: 'AgentCore Memory',
        detail: writeFailed
          ? `${loaded} prior ${loaded === 1 ? 'turn' : 'turns'} read; the completed action was not appended`
          : `${loaded} prior ${loaded === 1 ? 'turn' : 'turns'} read; ${persisted} new turns persisted`,
        status:
          memory.source === 'agentcore-memory' && !writeFailed
            ? 'completed'
            : 'unavailable',
        meta: [
          memory.source,
          memory.namespace_scope,
          writeFailed ? 'do not repeat the action' : '',
        ]
          .filter(Boolean)
          .join(' / '),
      },
    ]);
  };

  const addGuardrailStep = (event: StreamEvent) => {
    const guardrail = event.guardrail ?? {};
    const allowed = guardrail.allowed !== false;
    setSteps((current) => [
      ...current,
      {
        id: `guardrail-${eventSequenceRef.current++}`,
        kind: 'guardrail',
        title: 'Input safety inspection',
        detail: allowed
          ? 'Request evaluated before agent execution'
          : 'Request flagged by the input evaluation',
        status: guardrail.action === 'ERROR' ? 'error' : 'completed',
        meta: [
          guardrail.mode || 'configured',
          guardrail.action || 'NONE',
          guardrail.enforced ? 'enforced' : 'inspect only',
        ].join(' / '),
      },
    ]);
  };

  const addSqlSteps = (queries: DbQuery[]) => {
    const captured = queries.filter(
      (queryItem): queryItem is DbQuery & { sql: string } =>
        typeof queryItem.sql === 'string' && queryItem.sql.trim().length > 0,
    );
    if (!captured.length) return;
    setSteps((current) => [
      ...current,
      ...captured.map((queryItem) => ({
        id: `sql-${eventSequenceRef.current++}`,
        kind: 'sql' as const,
        title: [queryItem.op?.toUpperCase(), queryItem.table]
          .filter(Boolean)
          .join(' / ') || 'Database query',
        detail: 'Aurora emitted a query receipt with source and timing metadata',
        status: 'completed',
        meta:
          queryItem.duration_ms !== undefined
            ? `${queryItem.duration_ms} ms`
            : undefined,
        sql: queryItem.sql,
      })),
    ]);
  };

  const handleStreamEvent = (rawEvent: unknown) => {
    const event = rawEvent as StreamEvent;

    if (event.type === 'content_reset') {
      setAgentResponse('');
    } else if (event.type === 'content_delta' && event.delta) {
      setAgentResponse((current) => current + event.delta);
    } else if (event.type === 'content' && event.content !== undefined) {
      setAgentResponse((current) =>
        reconcileAgentResponse(current, event.content),
      );
    } else if (event.type === 'product' && event.product) {
      setProducts((current) => mergeProducts(current, [event.product]));
    } else if (
      event.type === 'intent_signal' &&
      event.intent &&
      event.response_mode &&
      event.model_family
    ) {
      setIntentSignal({
        intent: event.intent,
        classifier: event.classifier || 'deterministic',
        responseMode: event.response_mode,
        modelFamily: event.model_family,
        modelId: event.model_id || '',
      });
    } else if (event.type === 'skill_routing') {
      addRoutingStep(event);
    } else if (
      event.type === 'memory_context' ||
      event.type === 'aurora_profile_context'
    ) {
      addAuroraProfileStep(event);
    } else if (event.type === 'agentcore_memory') {
      addAgentCoreMemoryStep(event);
    } else if (event.type === 'guardrail_decision') {
      addGuardrailStep(event);
    } else if (event.type === 'agent_step') {
      updateAgentStep(event);
    } else if (event.type === 'tool_call') {
      addToolStep(event);
    } else if (event.type === 'db_queries') {
      addSqlSteps(Array.isArray(event.queries) ? event.queries : []);
    } else if (event.type === 'complete') {
      if (event.response?.response) {
        setAgentResponse((current) =>
          reconcileAgentResponse(current, event.response?.response),
        );
      }
      if (event.response?.rail) {
        setExecutionRail(labelRail(event.response.rail));
      }
      if (event.response?.orchestration?.pattern) {
        setExecutionPattern(event.response.orchestration.pattern);
        setExecutionRoute(event.response.orchestration.route || null);
      }
      if (Array.isArray(event.response?.products)) {
        setProducts((current) =>
          mergeProducts(current, event.response?.products ?? []),
        );
      }
    } else if (event.type === 'error') {
      setRunError(
        event.error || event.message || 'The agent reported an execution error.',
      );
    }
  };

  /**
   * Run one curated turn. `request` always comes from personaCurations, so the
   * string the agent receives is the same one the storefront would send.
   */
  const runAgent = async (
    curatedQuery: string,
    turnIndex: number | null,
    operatorTurnIndex: number | null = null,
  ) => {
    const request = curatedQuery.trim();
    if (!request || runStatus === 'running') return;

    setActiveTurn(turnIndex);
    setActiveOperatorTurn(operatorTurnIndex);
    setActiveQuery(request);
    eventSequenceRef.current = 0;
    startedAtRef.current = Date.now();
    setRunStatus('running');
    setRunError(null);
    setSteps([]);
    setProducts([]);
    setAgentResponse('');
    setElapsedMs(0);
    setIntentSignal(null);
    setExecutionRail('Server selected');
    setExecutionPattern(null);
    setExecutionRoute(null);
    setCopiedSqlId(null);
    setReceiptOverrides({});
    setLinkedStepId(null);

    try {
      const response: ChatResponse = await sendChatMessageStreaming(
        request,
        [],
        handleStreamEvent,
        undefined,
        guardrailsEnabled,
        operatorTurnIndex === null && profileEnabled
          ? persona?.customer_id ?? null
          : null,
        orchestrationPattern,
        responseMode,
      );
      if (response.response) {
        setAgentResponse((current) =>
          reconcileAgentResponse(current, response.response),
        );
      }
      if (response.products?.length) {
        setProducts((current) => mergeProducts(current, response.products));
      }
      setSteps((current) =>
        current.map((step) => ({
          ...step,
          status:
            step.status === 'in_progress' || step.status === 'executing'
              ? 'completed'
              : step.status,
        })),
      );
      setRunStatus('complete');
    } catch (error) {
      setRunError(errorMessage(error));
      setRunStatus('error');
    } finally {
      if (startedAtRef.current !== null) {
        setElapsedMs(Date.now() - startedAtRef.current);
      }
      startedAtRef.current = null;
    }
  };

  const agentCount = new Set(
    steps
      .filter((step) => step.kind === 'agent' && step.source)
      .map((step) => step.source),
  ).size;
  const sqlCount = steps.filter((step) => step.kind === 'sql').length;
  const personaLabel = persona?.display_name ?? 'Anonymous';
  const orderedProducts = productsForResponse(products, agentResponse);
  const bestMatch = orderedProducts[0];
  const curatedPairings = orderedProducts.slice(1, 3);
  const displayedProductCount =
    (bestMatch ? 1 : 0) + curatedPairings.length;
  const currentStepId =
    runStatus === 'running' && steps.length
      ? steps[steps.length - 1].id
      : null;

  useEffect(() => {
    const currentStep = currentTraceStepRef.current;
    if (!currentStepId || !currentStep?.scrollIntoView) return;
    currentStep.scrollIntoView({
      block: 'nearest',
      behavior: reduceMotion ? 'auto' : 'smooth',
    });
  }, [currentStepId, reduceMotion]);

  useLayoutEffect(() => {
    const list = traceListRef.current;
    const latestStep = currentTraceStepRef.current;

    if (!steps.length || !list || !latestStep) {
      setTraceLineHeight(0);
      return undefined;
    }

    const measure = () => {
      const listRect = list.getBoundingClientRect();
      const stepRect = latestStep.getBoundingClientRect();
      const nextHeight =
        stepRect.bottom - listRect.top - TRACE_LINE_TOP - 10;
      setTraceLineHeight(Math.max(0, nextHeight));
    };

    measure();

    if (typeof ResizeObserver === 'undefined') return undefined;
    const observer = new ResizeObserver(measure);
    observer.observe(list);
    return () => observer.disconnect();
  }, [currentStepId, steps.length]);

  const verifiedClaims: VerifiedClaim[] = [];
  const latestSqlStep = [...steps]
    .reverse()
    .find((step) => step.kind === 'sql');
  const firstToolStep = steps.find((step) => step.kind === 'tool');
  const routingStep = steps.find((step) => step.kind === 'routing');
  const toolNames = Array.from(
    new Set(
      steps
        .filter((step) => step.kind === 'tool' && step.source)
        .map((step) => step.source as string),
    ),
  );
  if (sqlCount) {
    verifiedClaims.push({
      id: 'sql',
      title: `${sqlCount} database ${sqlCount === 1 ? 'lookup' : 'lookups'} captured`,
      detail: [latestSqlStep?.title, latestSqlStep?.meta]
        .filter(Boolean)
        .join(' / '),
      stepId: latestSqlStep?.id,
    });
  }
  if (bestMatch) {
    const productContext = [
      bestMatch.category,
      bestMatch.price > 0 ? `$${bestMatch.price.toFixed(2)}` : '',
    ]
      .filter(Boolean)
      .join(' / ');
    verifiedClaims.push({
      id: 'products',
      title:
        products.length === 1
          ? `${bestMatch.name} returned by the live turn`
          : `${bestMatch.name} and ${products.length - 1} more returned`,
      detail: productContext || 'Grounded catalog evidence from this turn.',
      // The tool call is the step that produced the products. Absent a tool
      // event the claim stands on its own without a link to open.
      stepId: firstToolStep?.id,
    });
  }
  if (executionPattern) {
    verifiedClaims.push({
      id: 'route',
      title: `${patternLabel(executionPattern)} route`,
      detail: executionRoute
        ? `Completed through ${labelIntent(executionRoute)}.`
        : `Completed through ${executionRail}.`,
      stepId: routingStep?.id,
    });
  }

  const linkedClaimCount = verifiedClaims.filter((claim) =>
    Boolean(claim.stepId),
  ).length;

  const rationale = whyThisAnswer({
    intentSignal,
    toolNames,
    sqlCount,
    executionRail,
    executionPattern,
    executionRoute,
  });

  const receiptSteps = steps.filter((step) => Boolean(step.sql));
  const receiptStepCount = receiptSteps.length;

  /** Explicit choice beats the default, which opens the newest receipt. */
  const isReceiptOpen = (step: JourneyStep): boolean => {
    if (!step.sql) return false;
    const override = receiptOverrides[step.id];
    if (override !== undefined) return override;
    return step.id === latestSqlStep?.id;
  };

  const toggleReceipt = (step: JourneyStep) => {
    const next = !isReceiptOpen(step);
    setReceiptOverrides((current) => ({ ...current, [step.id]: next }));
  };

  const allReceiptsOpen =
    receiptStepCount > 0 && receiptSteps.every(isReceiptOpen);

  /**
   * Bulk disclosure writes an explicit state for every receipt rather than
   * clearing the overrides. Clearing would fall back to the default, which
   * opens the newest receipt, so "Collapse all" would leave one open.
   */
  const toggleAllReceipts = () => {
    const next = !allReceiptsOpen;
    setReceiptOverrides(
      Object.fromEntries(receiptSteps.map((step) => [step.id, next])),
    );
  };

  /**
   * Open a claim's supporting event: scroll it into the ledger's viewport and
   * mark it so the relationship is visible rather than asserted.
   */
  const openLinkedStep = (stepId: string) => {
    const node = stepNodesRef.current.get(stepId);
    setLinkedStepId(stepId);
    const step = steps.find((item) => item.id === stepId);
    if (step?.sql) {
      setReceiptOverrides((current) => ({ ...current, [stepId]: true }));
    }
    node?.scrollIntoView?.({
      block: 'center',
      behavior: reduceMotion ? 'auto' : 'smooth',
    });
    if (linkTimerRef.current !== null) {
      window.clearTimeout(linkTimerRef.current);
    }
    linkTimerRef.current = window.setTimeout(() => {
      setLinkedStepId(null);
      linkTimerRef.current = null;
    }, 2200);
  };

  const proofSummary = runProofSummary(
    runStatus,
    activeTurn,
    activeQuery,
    steps.length,
    agentCount,
    sqlCount,
    products.length,
  );

  const copySql = async (step: JourneyStep) => {
    if (!step.sql || !navigator.clipboard?.writeText) return;
    try {
      await navigator.clipboard.writeText(step.sql);
      setCopiedSqlId(step.id);
    } catch {
      setCopiedSqlId(null);
    }
  };

  return (
    <div className="observatory-workbench labs-index">
      <div className="labs-index-inner">
        <header className="observatory-workbench-intro">
          <div className="observatory-workbench-intro-copy">
            <h1 className="observatory-page-title">Live Workbench</h1>
            <p className="observatory-workbench-purpose">
              Run a governed shopper request and inspect identity, policy
              decisions, transaction state, and durable evidence.
            </p>
          </div>
          <span className="observatory-workbench-presence">
            <span aria-hidden="true" />
            Live governed surface
          </span>
        </header>
        <div className="observatory-workbench-grid" aria-label="Live agent run">
          <motion.aside
            className="observatory-input-panel"
            data-motion-panel="requests"
            aria-label="Guided requests and run settings"
            initial={
              reduceMotion
                ? false
                : {
                    opacity: 0,
                    clipPath: 'inset(0 100% 0 0 round 14px)',
                  }
            }
            animate={{ opacity: 1, clipPath: 'inset(0 0 0 0 round 14px)' }}
            transition={{
              duration: reduceMotion ? 0 : 0.46,
              ease: [0.16, 1, 0.3, 1],
            }}
          >
            <ObservatoryCuratedTurns
              personaId={personaId}
              personaLabel={personaLabel}
              running={runStatus === 'running'}
              activeIndex={activeTurn}
              orchestrationPattern={orchestrationPattern}
              onInspect={(curatedQuery, index) => {
                void runAgent(curatedQuery, index, null);
              }}
            />

            {/* Operator controls, subordinate to the turns above by design:
                the readout is always legible, the editing is behind one
                disclosure. Every row restates a control that exists. */}
            <section
              className="observatory-run-controls"
              aria-label="Run controls"
            >
              {/* No response-mode badge here. It restated the readout row
                  directly beneath it, so the same setting appeared three times
                  in one section: badge, readout, and the control itself. */}
              <header className="observatory-run-controls-heading">
                <span>
                  <SlidersHorizontal size={14} aria-hidden="true" />
                  Run controls
                </span>
              </header>

              {!editingControls && (
              <dl className="observatory-run-readout">
                <div>
                  <dt>Response</dt>
                  <dd>{labelIntent(responseMode)}</dd>
                </div>
                <div>
                  <dt>Orchestration</dt>
                  <dd>{patternLabel(orchestrationPattern)}</dd>
                </div>
                <div>
                  <dt>Aurora profile</dt>
                  <dd>
                    {persona
                      ? toggleLabel(profileEnabled)
                      : 'Select a persona'}
                  </dd>
                </div>
                <div>
                  <dt>Input safety inspection</dt>
                  <dd>{toggleLabel(guardrailsEnabled)}</dd>
                </div>
                <div>
                  <dt>Live trace</dt>
                  <dd>{toggleLabel(traceVisible)}</dd>
                </div>
              </dl>
              )}

              <details
                className="observatory-advanced observatory-edit-controls"
                onToggle={(event) =>
                  setEditingControls(event.currentTarget.open)
                }
              >
                <summary>
                  <span className="observatory-advanced-summary">
                    <strong>{editingControls ? 'Done editing' : 'Edit controls'}</strong>
                  </span>
                  <ChevronDown
                    className="observatory-advanced-chevron"
                    size={15}
                    aria-hidden="true"
                  />
                </summary>

                <div className="observatory-advanced-content">
                <section
                  className="observatory-agent-config"
                  aria-label="Agent configuration"
                >
                  <fieldset>
                    <legend>Orchestration pattern</legend>
                    <ToggleGroup
                      type="single"
                      value={orchestrationPattern}
                      aria-label="Orchestration pattern"
                      className="observatory-segmented"
                      data-columns="3"
                      onValueChange={(value) => {
                        if (value) {
                          setOrchestrationPattern(
                            value as OrchestrationPattern,
                          );
                        }
                      }}
                    >
                      {(
                        [
                          'dispatcher',
                          'graph',
                          'agents_as_tools',
                        ] as OrchestrationPattern[]
                      ).map((pattern) => (
                        <ToggleGroupItem
                          key={pattern}
                          value={pattern}
                          aria-label={patternLabel(pattern)}
                          disabled={runStatus === 'running'}
                        >
                          {patternLabel(pattern)}
                        </ToggleGroupItem>
                      ))}
                    </ToggleGroup>
                    <p className="observatory-mode-note">
                      {orchestrationPattern === 'dispatcher'
                        ? 'Deterministic intent routing to one specialist.'
                        : orchestrationPattern === 'graph'
                          ? 'GraphBuilder routes through a conditional specialist edge.'
                          : 'A Sonnet supervisor invokes specialists as tools.'}
                    </p>
                  </fieldset>

                  <fieldset>
                    <legend>Response mode</legend>
                    <ToggleGroup
                      type="single"
                      value={responseMode}
                      aria-label="Response mode"
                      className="observatory-segmented"
                      data-columns="3"
                      onValueChange={(value) => {
                        if (value) setResponseMode(value as ResponseMode);
                      }}
                    >
                      {(['balanced', 'editorial', 'fast'] as ResponseMode[]).map(
                        (mode) => (
                          <ToggleGroupItem
                            key={mode}
                            value={mode}
                            aria-label={
                              mode.charAt(0).toUpperCase() + mode.slice(1)
                            }
                            disabled={runStatus === 'running'}
                          >
                            {mode.charAt(0).toUpperCase() + mode.slice(1)}
                          </ToggleGroupItem>
                        ),
                      )}
                    </ToggleGroup>
                    <p className="observatory-mode-note">
                      {responseMode === 'balanced'
                        ? 'Opus for editorial specialists; Sonnet for reporting.'
                        : responseMode === 'editorial'
                          ? 'Claude Opus 4.6 composes the specialist response.'
                          : 'Claude Sonnet 4.6 composes the specialist response.'}
                    </p>
                  </fieldset>

                  <div className="observatory-switches">
                    <div>
                      <Switch
                        id="labs-profile-context"
                        checked={profileEnabled}
                        disabled={!persona || runStatus === 'running'}
                        onCheckedChange={setProfileEnabled}
                        aria-label="Aurora profile context"
                      />
                      <label htmlFor="labs-profile-context">
                        <strong>Aurora profile context</strong>
                        <small>
                          {persona
                            ? `Add ${persona.display_name}'s Aurora facts and order history`
                            : 'Select a persona to enable'}
                        </small>
                      </label>
                    </div>
                    <div>
                      <Switch
                        id="labs-safety-inspection"
                        checked={guardrailsEnabled}
                        disabled={runStatus === 'running'}
                        onCheckedChange={setGuardrailsEnabled}
                        aria-label="Input safety inspection"
                      />
                      <label htmlFor="labs-safety-inspection">
                        <strong>Input safety inspection</strong>
                        <small>
                          Run the pre-run evaluation and emit its receipt
                        </small>
                      </label>
                    </div>
                    <div>
                      <Switch
                        id="labs-trace-visibility"
                        checked={traceVisible}
                        onCheckedChange={setTraceVisible}
                        aria-label="Live trace visibility"
                      />
                      <label htmlFor="labs-trace-visibility">
                        <strong>Live trace visibility</strong>
                        <small>
                          View only: show or hide agent, tool, and SQL events
                        </small>
                      </label>
                    </div>
                  </div>

                </section>


                <dl className="observatory-session-facts">
                  <div>
                    <dt>Persona</dt>
                    <dd>{personaLabel}</dd>
                  </div>
                  <div>
                    <dt>Rail</dt>
                    <dd>{executionRail}</dd>
                  </div>
                  <div>
                    <dt>Pattern</dt>
                    <dd>
                      {patternLabel(
                        executionPattern ?? orchestrationPattern,
                      )}
                      {executionRoute ? ` / ${labelIntent(executionRoute)}` : ''}
                    </dd>
                  </div>
                </dl>

                  <p className="observatory-provenance">
                    <Activity size={13} aria-hidden="true" />
                    <span>
                      Live SSE from <code>/api/chat/stream</code>. Every event
                      below comes from this turn.
                    </span>
                  </p>
                </div>
              </details>

              <details className="observatory-advanced observatory-operator-runs">
                <summary>
                  <span className="observatory-advanced-summary">
                    <strong>Operator runs</strong>
                  </span>
                  <ChevronDown
                    className="observatory-advanced-chevron"
                    size={15}
                    aria-hidden="true"
                  />
                </summary>
                <div className="observatory-advanced-content">
                  <p>
                    Inventory operations stay separate from shopper
                    personas. Writes run only through Dispatcher.
                  </p>
                  <div>
                    {OPERATOR_TURNS.map((turn, index) => {
                      const blocked =
                        turn.access === 'write' &&
                        orchestrationPattern !== 'dispatcher';
                      const active = activeOperatorTurn === index;
                      return (
                        <div key={turn.id} className="observatory-operator-cell">
                        <button
                          type="button"
                          className="observatory-operator-run"
                          data-access={turn.access}
                          data-active={active ? 'true' : undefined}
                          disabled={runStatus === 'running'}
                          aria-disabled={blocked || undefined}
                          aria-describedby={
                            blocked ? `operator-blocked-${turn.id}` : undefined
                          }
                          onClick={() => {
                            // aria-disabled keeps the control focusable so the
                            // reason below is reachable; the guard is here.
                            if (blocked || runStatus === 'running') return;
                            void runAgent(turn.query, null, index);
                          }}
                        >
                          <span aria-hidden="true">
                            {turn.access === 'write' ? (
                              <PackagePlus size={15} />
                            ) : (
                              <Boxes size={15} />
                            )}
                          </span>
                          <span>
                            <strong>{turn.label}</strong>
                            <small>{turn.query}</small>
                          </span>
                          <Badge
                            variant={
                              turn.access === 'write'
                                ? 'warning'
                                : 'neutral'
                            }
                          >
                            {turn.access}
                          </Badge>
                        </button>
                        {/* A reason in text, not a `title`. A disabled button
                            is not focusable, so its tooltip never reaches a
                            keyboard or screen-reader user; `aria-disabled`
                            plus this paragraph does. */}
                        {blocked && (
                          <p
                            id={`operator-blocked-${turn.id}`}
                            className="observatory-operator-blocked"
                          >
                            Writes run only through Dispatcher. Switch the
                            orchestration pattern in Edit controls to enable
                            this.
                          </p>
                        )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              </details>
            </section>

          </motion.aside>

          <motion.section
            className="observatory-trace-panel"
            data-motion-panel="trace"
            aria-labelledby="live-journey-title"
            initial={
              reduceMotion
                ? false
                : {
                    opacity: 0,
                    clipPath: 'inset(0 0 100% 0 round 14px)',
                  }
            }
            animate={{ opacity: 1, clipPath: 'inset(0 0 0 0 round 14px)' }}
            transition={{
              duration: reduceMotion ? 0 : 0.46,
              delay: reduceMotion ? 0 : 0.07,
              ease: [0.16, 1, 0.3, 1],
            }}
          >
            <div className="observatory-section-heading">
              <div>
                <h2 id="live-journey-title">Evidence ledger</h2>
                <p>
                  {activeQuery ??
                    'An append-only trail of decisions and proofs.'}
                </p>
              </div>
              {/* Only offered when there is more than one receipt to act on;
                  a control that cannot change anything is not an affordance. */}
              {receiptStepCount > 1 ? (
                <button
                  type="button"
                  className="observatory-ledger-action"
                  aria-pressed={allReceiptsOpen}
                  onClick={toggleAllReceipts}
                >
                  {allReceiptsOpen ? (
                    <ChevronsDownUp size={14} aria-hidden="true" />
                  ) : (
                    <ChevronsUpDown size={14} aria-hidden="true" />
                  )}
                  {allReceiptsOpen ? 'Collapse all' : 'Expand all'}
                </button>
              ) : null}
              <div
                className="observatory-run-summary"
                role="status"
                aria-label="Run proof summary"
                aria-live="polite"
              >
                <span className="observatory-run-summary-copy">
                  {proofSummary.label}. {proofSummary.summary}
                </span>
                <Badge
                  variant={
                    runStatus === 'complete'
                      ? 'success'
                      : runStatus === 'error'
                        ? 'destructive'
                        : runStatus === 'running'
                          ? 'warning'
                          : 'neutral'
                  }
                  className="observatory-live-state"
                  data-status={runStatus}
                >
                  {statusLabel(runStatus)}
                </Badge>
              </div>
            </div>

            <div className="observatory-panel-scroll observatory-ledger-scroll">
              {traceVisible && intentSignal ? (
                <section
                  className="observatory-run-contract"
                  role="status"
                  aria-label="Execution context"
                >
                  <header>
                    <div>
                      <span>Routing decision</span>
                      <strong>
                        {labelIntent(intentSignal.intent)} request
                      </strong>
                    </div>
                    <Badge
                      variant="neutral"
                      className="observatory-run-mode"
                    >
                      {labelIntent(intentSignal.responseMode)} mode
                    </Badge>
                  </header>
                  <dl>
                    <div>
                      <dt>Intent</dt>
                      <dd>{labelIntent(intentSignal.intent)}</dd>
                    </div>
                    <div>
                      <dt>Classifier</dt>
                      <dd>{labelIntent(intentSignal.classifier)}</dd>
                    </div>
                    <div className="observatory-run-contract-model">
                      <dt>Response model</dt>
                      <dd>
                        {modelDisplayName(
                          intentSignal.modelFamily,
                          intentSignal.modelId,
                        )}
                      </dd>
                      <code title={intentSignal.modelId}>
                        {intentSignal.modelId || 'Server default'}
                      </code>
                    </div>
                  </dl>
                </section>
              ) : null}

              {runError ? (
                <div className="observatory-error" role="alert">
                  <strong>Agent run did not complete</strong>
                  <p>{runError}</p>
                  {activeQuery !== null ? (
                    <button
                      type="button"
                      onClick={() => {
                        void runAgent(
                          activeQuery,
                          activeTurn,
                          activeOperatorTurn,
                        );
                      }}
                    >
                      <RotateCcw size={13} aria-hidden="true" />
                      Retry turn
                    </button>
                  ) : null}
                </div>
              ) : null}

              {!traceVisible ? (
                <div className="observatory-idle-state">
                  <Eye size={24} aria-hidden="true" />
                  <strong>Live trace hidden</strong>
                  <p>Turn on live trace visibility to inspect emitted events.</p>
                </div>
              ) : steps.length ? (
                <ol
                  ref={traceListRef}
                  className="observatory-trace-list"
                >
                  <motion.li
                    key={`${steps[steps.length - 1]?.id ?? 'trace'}-${Math.round(traceLineHeight)}`}
                    className="observatory-trace-progress"
                    role="presentation"
                    aria-hidden="true"
                    style={{ height: traceLineHeight }}
                    initial={reduceMotion ? false : {
                      clipPath: 'inset(0 0 100% 0)',
                      opacity: 0.8,
                    }}
                    animate={{
                      clipPath: 'inset(0 0 0% 0)',
                      opacity: traceLineHeight > 0 ? 1 : 0,
                    }}
                    transition={{
                      duration: reduceMotion ? 0 : 0.74,
                      ease: [0.16, 1, 0.3, 1],
                    }}
                  />
                  {steps.map((step, index) => (
                    <motion.li
                      key={step.id}
                      ref={(node) => {
                        if (node) stepNodesRef.current.set(step.id, node);
                        else stepNodesRef.current.delete(step.id);
                        if (index === steps.length - 1) {
                          currentTraceStepRef.current = node;
                        }
                      }}
                      className="observatory-trace-step"
                      data-kind={step.kind}
                      data-status={step.status}
                      data-current={
                        step.id === currentStepId ? 'true' : undefined
                      }
                      data-expanded={isReceiptOpen(step) ? 'true' : undefined}
                      data-linked={
                        step.id === linkedStepId ? 'true' : undefined
                      }
                      initial={
                        reduceMotion
                          ? false
                          : { opacity: 0.72, transform: 'translateY(6px)' }
                      }
                      animate={{ opacity: 1, transform: 'translateY(0)' }}
                      transition={{
                        duration: reduceMotion ? 0 : 0.28,
                        ease: [0.16, 1, 0.3, 1],
                      }}
                    >
                      <span className="observatory-trace-index">
                        {String(index + 1).padStart(2, '0')}
                      </span>
                      <span className="observatory-trace-node" aria-hidden="true">
                        {iconForStep(step.kind)}
                      </span>
                      <div className="observatory-trace-content">
                        <div className="observatory-trace-kicker">
                          <span>{step.kind}</span>
                          <em>{step.status.replace('_', ' ')}</em>
                        </div>
                        <h3>{step.title}</h3>
                        <p>{step.detail}</p>
                        {step.meta ? <small>{step.meta}</small> : null}
                        {/* A disclosure appears only on events that carry a
                            receipt. The other rows have nothing behind them,
                            and a chevron that reveals nothing is a lie. */}
                        {step.sql ? (
                          <button
                            type="button"
                            className="observatory-receipt-toggle"
                            aria-expanded={isReceiptOpen(step)}
                            aria-label={`${isReceiptOpen(step) ? 'Hide' : 'Show'} the Aurora receipt for ${step.title}`}
                            onClick={() => toggleReceipt(step)}
                          >
                            <ChevronDown size={14} aria-hidden="true" />
                          </button>
                        ) : null}
                        {step.sql && isReceiptOpen(step) ? (
                          <div className="observatory-proof-block">
                            <div className="observatory-proof-block-heading">
                              <div>
                                <span>
                                  <Database size={14} aria-hidden="true" />
                                  Aurora SQL receipt
                                </span>
                                <strong>{step.title}</strong>
                              </div>
                              <button
                                type="button"
                                className="observatory-copy-sql"
                                title={
                                  copiedSqlId === step.id
                                    ? 'SQL copied'
                                    : 'Copy captured SQL'
                                }
                                aria-label={
                                  copiedSqlId === step.id
                                    ? 'SQL copied'
                                    : 'Copy captured SQL'
                                }
                                onClick={() => {
                                  void copySql(step);
                                }}
                              >
                                {copiedSqlId === step.id ? (
                                  <Check size={14} aria-hidden="true" />
                                ) : (
                                  <Copy size={14} aria-hidden="true" />
                                )}
                              </button>
                            </div>
                            <pre
                              className="observatory-sql"
                              aria-label="Captured SQL"
                            >
                              <code>{formatSqlForDisplay(step.sql)}</code>
                            </pre>
                            <dl className="observatory-proof-receipt">
                              <div>
                                <dt>Source</dt>
                                <dd>
                                  <code>db_queries</code> event
                                </dd>
                              </div>
                              <div>
                                <dt>Duration</dt>
                                <dd>{step.meta ?? 'Not reported'}</dd>
                              </div>
                              <div>
                                <dt>Bindings</dt>
                                <dd>
                                  {sqlBindingCount(step.sql)
                                    ? `${sqlBindingCount(step.sql)} positional`
                                    : 'None'}
                                </dd>
                              </div>
                              <div>
                                <dt>Status</dt>
                                <dd data-status={step.status}>
                                  <CheckCircle2
                                    size={12}
                                    aria-hidden="true"
                                  />
                                  {labelIntent(step.status)}
                                </dd>
                              </div>
                            </dl>
                          </div>
                        ) : null}
                      </div>
                    </motion.li>
                  ))}
                </ol>
              ) : (
                <div className="observatory-trace-skeleton">
                  <p className="observatory-trace-skeleton-note">
                    {runStatus === 'running'
                      ? 'Waiting for the first emitted event.'
                      : 'Select a guided request to populate the live trace.'}
                  </p>
                  <ol
                    className="observatory-trace-list"
                    data-skeleton="true"
                    aria-hidden="true"
                  >
                    {TRACE_SKELETON.map((kind, index) => (
                      <li
                        key={`${kind}-${index}`}
                        className="observatory-trace-step"
                        data-kind={kind}
                        data-status="pending"
                        data-pending={runStatus === 'running' ? 'true' : undefined}
                      >
                        <span className="observatory-trace-index">
                          {String(index + 1).padStart(2, '0')}
                        </span>
                        <span
                          className="observatory-trace-node"
                          aria-hidden="true"
                        >
                          {iconForStep(kind)}
                        </span>
                        <div className="observatory-trace-content">
                          <div className="observatory-trace-kicker">
                            <span>{kind}</span>
                          </div>
                          <span className="observatory-trace-ghost" />
                        </div>
                      </li>
                    ))}
                  </ol>
                </div>
              )}
            </div>

            <div className="observatory-ledger-footer">
              <dl className="observatory-session-metrics">
                <div>
                  <span>Elapsed</span>
                  <strong>
                    {runStatus === 'idle' ? '-' : formatElapsed(elapsedMs)}
                  </strong>
                </div>
                <div>
                  <span>Steps</span>
                  <strong>{metricValue(runStatus, steps.length)}</strong>
                </div>
                <div>
                  <span>Agents</span>
                  <strong>{metricValue(runStatus, agentCount)}</strong>
                </div>
                <div>
                  <span>SQL</span>
                  <strong>{metricValue(runStatus, sqlCount)}</strong>
                </div>
              </dl>

              {/* Counts come from the events actually held in state. The line
                  is absent before a run rather than reading a hopeful zero. */}
              {steps.length ? (
                <p className="observatory-append-only">
                  Append only. {steps.length}{' '}
                  {steps.length === 1 ? 'event' : 'events'}, {receiptStepCount}{' '}
                  SQL {receiptStepCount === 1 ? 'receipt' : 'receipts'}.
                </p>
              ) : null}
            </div>
          </motion.section>

          <motion.section
            className="observatory-results-panel"
            data-motion-panel="results"
            aria-labelledby="live-result-title"
            initial={
              reduceMotion
                ? false
                : {
                    opacity: 0,
                    clipPath: 'inset(0 0 0 100% round 14px)',
                  }
            }
            animate={{ opacity: 1, clipPath: 'inset(0 0 0 0 round 14px)' }}
            transition={{
              duration: reduceMotion ? 0 : 0.46,
              delay: reduceMotion ? 0 : 0.14,
              ease: [0.16, 1, 0.3, 1],
            }}
          >
            <div className="observatory-section-heading">
              <div>
                <h2 id="live-result-title">Grounded answer</h2>
                <p>The shopper reply and its supporting evidence.</p>
              </div>
              <Badge
                variant={
                  runStatus === 'complete'
                    ? 'success'
                    : runStatus === 'error'
                      ? 'destructive'
                      : runStatus === 'running'
                        ? 'warning'
                        : 'neutral'
                }
                className="observatory-answer-state"
                data-status={runStatus}
              >
                {runStatus === 'complete'
                  ? 'Verified'
                  : runStatus === 'running'
                    ? 'Streaming'
                    : runStatus === 'error'
                      ? 'Incomplete'
                      : 'Awaiting turn'}
              </Badge>
            </div>

            <div className="observatory-panel-scroll observatory-results-scroll">
              <section
                className="observatory-agent-response"
                aria-label={
                  products.length ? 'Recommended result' : 'Shopper answer'
                }
                data-empty={agentResponse ? undefined : 'true'}
              >
                <div>
                  {products.length ? (
                    <Sparkles size={14} aria-hidden="true" />
                  ) : (
                    <Sparkles
                      className="observatory-agent-sparkle"
                      data-testid="shopper-answer-sparkle"
                      size={15}
                      strokeWidth={2.2}
                      aria-hidden="true"
                    />
                  )}
                  {products.length ? 'Recommended result' : 'Shopper answer'}
                </div>
                <p>
                  {agentResponse ||
                    (runStatus === 'running'
                      ? 'The answer will appear here as the agent streams.'
                      : 'Choose a shopper turn to receive the live answer.')}
                </p>
              </section>

              {bestMatch ? (
                <div className="observatory-catalog-edit">
                  <section aria-labelledby="best-match-title">
                    <div className="observatory-catalog-heading">
                      <div>
                        <h3 id="best-match-title">Best match</h3>
                        <span>First recommendation from this turn</span>
                      </div>
                    </div>
                    <div
                      className="observatory-products"
                      data-layout="feature"
                    >
                      <LabsProductCard
                        product={bestMatch}
                        role="best-match"
                      />
                    </div>
                  </section>

                  {curatedPairings.length ? (
                    <section
                      className="observatory-pairings"
                      aria-labelledby="curated-pairings-title"
                    >
                      <div className="observatory-catalog-heading">
                        <div>
                          <h3 id="curated-pairings-title">Curated pairings</h3>
                          <span>
                            {curatedPairings.length}{' '}
                            {curatedPairings.length === 1
                              ? 'supporting piece'
                              : 'supporting pieces'}
                          </span>
                        </div>
                      </div>
                      <div
                        className="observatory-products"
                        data-layout="pairings"
                      >
                        {curatedPairings.map((product, index) => (
                          <LabsProductCard
                            key={`${product.id || product.name}-${index}`}
                            product={product}
                            role="pairing"
                          />
                        ))}
                      </div>
                    </section>
                  ) : null}

                  {orderedProducts.length > displayedProductCount ? (
                    <p className="observatory-products-overflow">
                      Showing the best match and{' '}
                      {curatedPairings.length === 1
                        ? 'one pairing'
                        : `${curatedPairings.length} pairings`}{' '}
                      from {orderedProducts.length} grounded pieces.
                    </p>
                  ) : null}
                </div>
              ) : (
                <p
                  className="observatory-products-empty"
                  data-status={runStatus}
                >
                  {runStatus === 'complete'
                    ? 'This turn completed without a product result.'
                    : runStatus === 'running'
                      ? 'Retrieving grounded catalog matches.'
                      : 'Grounded products from this turn will appear here.'}
                </p>
              )}

              <section
                className="observatory-verified-claims"
                aria-labelledby="verified-claims-title"
              >
                <div className="observatory-results-subheading">
                  <h3 id="verified-claims-title">Verified claims</h3>
                  <span>{verifiedClaims.length || '-'}</span>
                </div>
                {verifiedClaims.length ? (
                  <ul>
                    {verifiedClaims.map((claim) => (
                      <li key={claim.id} data-linkable={claim.stepId ? 'true' : undefined}>
                        <CheckCircle2 size={15} aria-hidden="true" />
                        <span>
                          <strong>{claim.title}</strong>
                          <small>{claim.detail}</small>
                        </span>
                        {/* Only a claim with an emitted event behind it gets
                            an open affordance. */}
                        {claim.stepId ? (
                          <button
                            type="button"
                            className="observatory-claim-link"
                            onClick={() => openLinkedStep(claim.stepId as string)}
                          >
                            <Link2 size={13} aria-hidden="true" />
                            Open event
                          </button>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="observatory-results-placeholder">
                    Claims appear only after supporting evidence is emitted.
                  </p>
                )}
                {linkedClaimCount ? (
                  <p className="observatory-claims-linked">
                    <Link2 size={12} aria-hidden="true" />
                    {linkedClaimCount} of {verifiedClaims.length} linked to a
                    ledger event
                  </p>
                ) : null}
              </section>

              {rationale.length ? (
                <section
                  className="observatory-rationale"
                  aria-labelledby="why-this-answer-title"
                >
                  <div className="observatory-results-subheading">
                    <h3 id="why-this-answer-title">Why this answer</h3>
                  </div>
                  <ul>
                    {rationale.map((line) => (
                      <li key={line}>{line}</li>
                    ))}
                  </ul>
                  {/* Naming the source keeps this from reading as the model's
                      account of its own reasoning, which the runtime does not
                      expose. */}
                  <p className="observatory-rationale-source">
                    Assembled from this turn's emitted events.
                  </p>
                </section>
              ) : null}
            </div>
          </motion.section>
        </div>
      </div>
    </div>
  );
}
