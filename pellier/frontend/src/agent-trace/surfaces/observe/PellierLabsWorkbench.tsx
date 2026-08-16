import { useEffect, useRef, useState } from 'react';
import {
  Activity,
  Bot,
  Brain,
  CheckCircle2,
  Database,
  Eye,
  Loader2,
  Play,
  ShoppingBag,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Timer,
  Users,
  Workflow,
  Wrench,
} from 'lucide-react';
import { usePersona } from '../../../contexts/PersonaContext';
import {
  sendChatMessageStreaming,
  type ChatProduct,
  type ChatResponse,
  type ResponseMode,
} from '../../../services/chat';
import { imageSrc } from '../../../utils/assetPath';
import { PellierLabsMasthead } from './PellierLabsMasthead';
import './PellierLabsWorkbench.css';

type RunStatus = 'idle' | 'running' | 'complete' | 'error';
type StepKind = 'routing' | 'memory' | 'guardrail' | 'agent' | 'tool' | 'sql';

const QUERY_SUGGESTIONS: Record<string, string[]> = {
  anonymous: [
    'Find a resort-ready linen shirt under $200',
    'Show me a thoughtful housewarming gift under $100',
    'Is the Italian Linen Camp Shirt available in Brooklyn?',
  ],
  marco: [
    'Build a resort edit around the linen pieces I already own',
    'Which travel-ready shirt best fits my preferences under $250?',
    'Is the Italian Linen Camp Shirt available in Brooklyn?',
  ],
  anna: [
    'Find a housewarming gift under $100 that feels special',
    'What would pair well with gifts I have bought before?',
    'Show me ready-to-give pieces under $150',
  ],
  theo: [
    'Recommend durable ceramics that fit my slow-craft preferences',
    'How should I care for the stoneware I bought?',
    'What is the return policy for a damaged Wabi-Sabi Bowl?',
  ],
};

interface DbQuery {
  op?: string;
  table?: string;
  sql?: string;
  duration_ms?: number;
}

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

interface IntentSignal {
  intent: string;
  classifier: string;
  responseMode: ResponseMode;
  modelFamily: 'opus' | 'sonnet';
  modelId: string;
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

function statusForMasthead(status: RunStatus): string {
  if (status === 'running') return 'Agent running';
  if (status === 'complete') return 'Live run complete';
  if (status === 'error') return 'Run needs attention';
  return 'Live execution ready';
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

export default function PellierLabsWorkbench() {
  const { persona } = usePersona();
  const personaId = persona?.id ?? 'anonymous';
  const [query, setQuery] = useState('');
  const [runStatus, setRunStatus] = useState<RunStatus>('idle');
  const [steps, setSteps] = useState<JourneyStep[]>([]);
  const [products, setProducts] = useState<ChatProduct[]>([]);
  const [agentResponse, setAgentResponse] = useState('');
  const [elapsedMs, setElapsedMs] = useState(0);
  const [runError, setRunError] = useState<string | null>(null);
  const [responseMode, setResponseMode] =
    useState<ResponseMode>('balanced');
  const [profileEnabled, setProfileEnabled] = useState(Boolean(persona));
  const [guardrailsEnabled, setGuardrailsEnabled] = useState(false);
  const [traceVisible, setTraceVisible] = useState(true);
  const [intentSignal, setIntentSignal] = useState<IntentSignal | null>(null);
  const [executionRail, setExecutionRail] = useState('Server selected');
  const [executionPattern, setExecutionPattern] = useState<string | null>(null);
  const [executionRoute, setExecutionRoute] = useState<string | null>(null);
  const startedAtRef = useRef<number | null>(null);
  const eventSequenceRef = useRef(0);

  useEffect(() => {
    setQuery('');
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
  }, [personaId]);

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
          .join(' · '),
      },
    ]);
  };

  const addAuroraProfileStep = (event: StreamEvent) => {
    const memory = event.memory ?? {};
    const facts = memory.facts_loaded ?? 0;
    const orders = memory.orders_loaded ?? 0;
    const live = memory.source === 'aurora';
    setSteps((current) => [
      ...current,
      {
        id: `memory-${eventSequenceRef.current++}`,
        kind: 'memory',
        title: 'Aurora profile context',
        detail: live
          ? `${facts} profile ${facts === 1 ? 'fact' : 'facts'} and ${orders} past ${orders === 1 ? 'order' : 'orders'} loaded`
          : 'No live Aurora profile context was available for this turn',
        status: live && memory.applied ? 'completed' : 'unavailable',
        meta: [memory.source || 'unavailable', memory.customer_id || '']
          .filter(Boolean)
          .join(' · '),
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
        ].join(' · '),
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
          .join(' · ') || 'Database query',
        detail: 'SQL captured during this live turn',
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
    } else if (event.type === 'memory_context') {
      addAuroraProfileStep(event);
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

  const runAgent = async (queryOverride?: string) => {
    const request = (queryOverride ?? query).trim();
    if (!request || runStatus === 'running') return;

    setQuery(request);
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

    try {
      const response: ChatResponse = await sendChatMessageStreaming(
        request,
        [],
        handleStreamEvent,
        undefined,
        guardrailsEnabled,
        profileEnabled ? persona?.customer_id ?? null : null,
        'dispatcher',
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
  const querySuggestions =
    QUERY_SUGGESTIONS[personaId] ?? QUERY_SUGGESTIONS.anonymous;
  const orderedProducts = productsForResponse(products, agentResponse);

  return (
    <div className="pellier-labs-workbench">
      <div className="pellier-labs-workbench-inner">
        <PellierLabsMasthead
          eyebrow="Live inspection"
          title="Pellier Labs"
          deck="Send a request to the live agent, then inspect the tool path, database evidence, and returned catalog result."
          status={statusForMasthead(runStatus)}
        />

        <div className="pellier-labs-workbench-grid">
          <aside
            className="pellier-labs-task-panel"
            aria-label="Live agent task"
          >
            <div className="pellier-labs-panel-heading">
              <span aria-hidden="true">
                <Activity size={17} />
              </span>
              <div>
                <small>Live request</small>
                <h2>Run a turn</h2>
              </div>
            </div>

            <label className="pellier-labs-field-label" htmlFor="labs-query">
              Shopper request
            </label>
            <textarea
              id="labs-query"
              value={query}
              placeholder="Ask Pellier for a product, recommendation, stock check, or support action."
              disabled={runStatus === 'running'}
              onChange={(event) => setQuery(event.target.value)}
              rows={5}
            />

            <div className="pellier-labs-query-prompts">
              <span>Try a live query</span>
              <div>
                {querySuggestions.map((suggestion) => (
                  <button
                    key={suggestion}
                    type="button"
                    disabled={runStatus === 'running'}
                    onClick={() => void runAgent(suggestion)}
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>

            <section
              className="pellier-labs-agent-config"
              aria-labelledby="agent-config-title"
            >
              <div className="pellier-labs-config-heading">
                <SlidersHorizontal size={14} aria-hidden="true" />
                <h3 id="agent-config-title">Agent configuration</h3>
              </div>

              <div className="pellier-labs-fixed-config">
                <span>
                  <Workflow size={13} aria-hidden="true" />
                  Orchestration
                </span>
                <strong>Dispatcher</strong>
              </div>

              <fieldset>
                <legend>Response mode</legend>
                <div className="pellier-labs-segmented" data-columns="3">
                  {(['balanced', 'editorial', 'fast'] as ResponseMode[]).map(
                    (mode) => (
                      <button
                        key={mode}
                        type="button"
                        aria-pressed={responseMode === mode}
                        disabled={runStatus === 'running'}
                        onClick={() => setResponseMode(mode)}
                      >
                        {mode.charAt(0).toUpperCase() + mode.slice(1)}
                      </button>
                    ),
                  )}
                </div>
                <p className="pellier-labs-mode-note">
                  {responseMode === 'balanced'
                    ? 'Opus for editorial specialists; Sonnet for reporting.'
                    : responseMode === 'editorial'
                      ? 'Claude Opus 5 composes the specialist response.'
                      : 'Claude Sonnet 5 composes the specialist response.'}
                </p>
              </fieldset>

              <div className="pellier-labs-switches">
                <label>
                  <input
                    type="checkbox"
                    role="switch"
                    checked={profileEnabled}
                    disabled={!persona || runStatus === 'running'}
                    onChange={(event) => setProfileEnabled(event.target.checked)}
                  />
                  <span className="pellier-labs-switch-track" aria-hidden="true" />
                  <span>
                    <strong>Aurora profile context</strong>
                    <small>
                      {persona
                        ? `Use ${persona.display_name}'s live Aurora profile`
                        : 'Select a persona to enable'}
                    </small>
                  </span>
                </label>
                <label>
                  <input
                    type="checkbox"
                    role="switch"
                    checked={guardrailsEnabled}
                    disabled={runStatus === 'running'}
                    onChange={(event) =>
                      setGuardrailsEnabled(event.target.checked)
                    }
                  />
                  <span className="pellier-labs-switch-track" aria-hidden="true" />
                  <span>
                    <strong>Input safety inspection</strong>
                    <small>Observe the configured pre-run evaluation</small>
                  </span>
                </label>
                <label>
                  <input
                    type="checkbox"
                    role="switch"
                    checked={traceVisible}
                    onChange={(event) => setTraceVisible(event.target.checked)}
                  />
                  <span className="pellier-labs-switch-track" aria-hidden="true" />
                  <span>
                    <strong>Live trace visibility</strong>
                    <small>Show emitted agent, tool, and SQL events</small>
                  </span>
                </label>
              </div>
            </section>

            <dl className="pellier-labs-session-facts">
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
                  {patternLabel(executionPattern ?? 'dispatcher')}
                  {executionRoute ? ` · ${labelIntent(executionRoute)}` : ''}
                </dd>
              </div>
            </dl>

            <button
              type="button"
              className="pellier-labs-run-agent"
              onClick={() => void runAgent()}
              disabled={!query.trim() || runStatus === 'running'}
            >
              {runStatus === 'running' ? (
                <Loader2 className="spin" size={17} aria-hidden="true" />
              ) : (
                <Play size={16} fill="currentColor" aria-hidden="true" />
              )}
              {runStatus === 'running' ? 'Agent running' : 'Run agent'}
            </button>

            <p className="pellier-labs-provenance">
              <Activity size={13} aria-hidden="true" />
              <span>
                Live SSE from <code>/api/chat/stream</code>. Every event below
                comes from this turn.
              </span>
            </p>
          </aside>

          <section
            className="pellier-labs-trace-panel"
            aria-labelledby="live-journey-title"
          >
            <div className="pellier-labs-section-heading">
              <div>
                <span aria-hidden="true">
                  <Bot size={17} />
                </span>
                <div>
                  <small>Execution</small>
                  <h2 id="live-journey-title">Live Agent Journey</h2>
                </div>
              </div>
              <span
                className="pellier-labs-live-state"
                data-status={runStatus}
              >
                <span aria-hidden="true" />
                {statusLabel(runStatus)}
              </span>
            </div>

            {traceVisible && intentSignal ? (
              <div className="pellier-labs-intent-signal" role="status">
                <span aria-hidden="true">
                  <Workflow size={16} />
                </span>
                <div>
                  <small>Intent signal</small>
                  <strong>{labelIntent(intentSignal.intent)}</strong>
                  <em>
                    {intentSignal.classifier} classifier
                    {intentSignal.modelId
                      ? ` · ${intentSignal.modelId}`
                      : ''}
                  </em>
                </div>
                <div>
                  <small>Response</small>
                  <strong>
                    Claude {intentSignal.modelFamily === 'opus' ? 'Opus' : 'Sonnet'} 5
                  </strong>
                  <em>{labelIntent(intentSignal.responseMode)} mode</em>
                </div>
              </div>
            ) : null}

            {runError ? (
              <div className="pellier-labs-error" role="alert">
                <strong>Agent run did not complete</strong>
                <p>{runError}</p>
              </div>
            ) : null}

            {!traceVisible ? (
              <div className="pellier-labs-idle-state">
                <Eye size={24} aria-hidden="true" />
                <strong>Live journey hidden</strong>
                <p>Turn on live trace visibility to inspect emitted events.</p>
              </div>
            ) : steps.length ? (
              <ol className="pellier-labs-trace-list">
                {steps.map((step, index) => (
                  <li
                    key={step.id}
                    className="pellier-labs-trace-step"
                    data-kind={step.kind}
                  >
                    <span className="pellier-labs-trace-index">
                      {String(index + 1).padStart(2, '0')}
                    </span>
                    <div className="pellier-labs-trace-content">
                      <div className="pellier-labs-trace-kicker">
                        <span>
                          {iconForStep(step.kind)}
                          {step.kind}
                        </span>
                        <em>{step.status.replace('_', ' ')}</em>
                      </div>
                      <h3>{step.title}</h3>
                      <p>{step.detail}</p>
                      {step.meta ? <small>{step.meta}</small> : null}
                      {step.sql ? (
                        <pre
                          className="pellier-labs-sql"
                          aria-label="Captured SQL"
                        >
                          <code>{step.sql}</code>
                        </pre>
                      ) : null}
                    </div>
                  </li>
                ))}
              </ol>
            ) : (
              <div className="pellier-labs-idle-state">
                {runStatus === 'running' ? (
                  <Loader2 className="spin" size={24} aria-hidden="true" />
                ) : (
                  <Activity size={24} aria-hidden="true" />
                )}
                <strong>
                  {runStatus === 'running'
                    ? 'Waiting for the first agent event'
                    : 'Ready for a live journey'}
                </strong>
                <p>
                  Run the selected request to inspect events emitted by the
                  active agent path.
                </p>
              </div>
            )}
          </section>

          <aside
            className="pellier-labs-results-panel"
            aria-labelledby="live-result-title"
          >
            <div className="pellier-labs-section-heading">
              <div>
                <span aria-hidden="true">
                  <ShoppingBag size={17} />
                </span>
                <div>
                  <small>Output</small>
                  <h2 id="live-result-title">Live Result</h2>
                </div>
              </div>
            </div>

            <div className="pellier-labs-agent-response">
              <div>
                {products.length ? (
                  <Sparkles size={14} aria-hidden="true" />
                ) : runStatus === 'complete' ? (
                  <CheckCircle2 size={14} aria-hidden="true" />
                ) : (
                  <Bot size={14} aria-hidden="true" />
                )}
                {products.length ? 'Top pick' : 'Agent response'}
              </div>
              <p>
                {agentResponse ||
                  (runStatus === 'running'
                    ? 'The response will appear here as the agent streams.'
                    : 'Run a journey to receive the live agent response.')}
              </p>
            </div>

            {products.length ? (
              <div className="pellier-labs-catalog-edit">
                <div className="pellier-labs-catalog-heading">
                  <div>
                    <small>Live catalog edit</small>
                    <strong>
                      {products.length} {products.length === 1 ? 'piece' : 'pieces'}
                    </strong>
                  </div>
                  <span>From this turn</span>
                </div>
                <div className="pellier-labs-products">
                  {orderedProducts.map((product, index) => {
                    const src = imageSrc(product.image);
                    return (
                      <article
                        className="pellier-labs-product"
                        key={`${product.id || product.name}-${index}`}
                      >
                        <div className="pellier-labs-product-media">
                          {src ? (
                            <img src={src} alt={product.name} />
                          ) : (
                            <span aria-hidden="true">
                              {product.name.charAt(0).toUpperCase()}
                            </span>
                          )}
                        </div>
                        <div className="pellier-labs-product-copy">
                          <small>
                            {String(index + 1).padStart(2, '0')} /{' '}
                            {product.category || 'Catalog result'}
                          </small>
                          <h3>{product.name}</h3>
                          {product.rating ? (
                            <p>
                              {product.rating.toFixed(1)} rating
                              {product.reviews
                                ? ` · ${product.reviews} reviews`
                                : ''}
                            </p>
                          ) : null}
                        </div>
                        <strong className="pellier-labs-product-price">
                          ${product.price.toFixed(2)}
                        </strong>
                      </article>
                    );
                  })}
                </div>
              </div>
            ) : (
              <div
                className="pellier-labs-products-empty"
                data-status={runStatus}
              >
                {runStatus === 'running' ? (
                  <Loader2 className="spin" size={21} aria-hidden="true" />
                ) : (
                  <ShoppingBag size={21} aria-hidden="true" />
                )}
                <div>
                  <strong>
                    {runStatus === 'complete'
                      ? 'No catalog cards attached'
                      : runStatus === 'running'
                        ? 'Retrieving the live edit'
                        : 'Awaiting catalog results'}
                  </strong>
                  <span>
                    {runStatus === 'complete'
                      ? 'This turn completed without a product result.'
                      : 'Grounded products from this turn will appear here.'}
                  </span>
                </div>
              </div>
            )}

            <dl className="pellier-labs-session-metrics">
              <div>
                <Timer size={15} aria-hidden="true" />
                <span>Client elapsed</span>
                <strong>{formatElapsed(elapsedMs)}</strong>
              </div>
              <div>
                <Activity size={15} aria-hidden="true" />
                <span>Journey steps</span>
                <strong>{steps.length}</strong>
              </div>
              <div>
                <Users size={15} aria-hidden="true" />
                <span>Agents</span>
                <strong>{agentCount}</strong>
              </div>
              <div>
                <Database size={15} aria-hidden="true" />
                <span>Captured SQL</span>
                <strong>{sqlCount}</strong>
              </div>
            </dl>
          </aside>
        </div>
      </div>
    </div>
  );
}
