import { useEffect, useId, useState } from 'react';
import { ArrowUpRight, ChevronDown } from 'lucide-react';
import { Link } from 'react-router-dom';

import { DataTable, SectionEyebrow } from '../../shared';
import type { DataTableColumn } from '../../shared';

import './WorkbenchResources.css';

interface ResourceLink {
  label: string;
  description: string;
  path: string;
  /** The table, service or artefact the view reads. Never a paraphrase. */
  source: string;
}

interface ResourceQuestion {
  question: string;
  answer: string;
  links: ResourceLink[];
}

const RESOURCE_QUESTIONS: readonly ResourceQuestion[] = [
  {
    question: 'What ran?',
    answer:
      'Replay the turn, then inspect the control and receipt claims tied to it.',
    links: [
      {
        label: 'Sessions & traces',
        description: 'Turn-scoped chat, telemetry, and durable replay.',
        path: '/observatory/sessions',

        source: 'governed_turn_receipts, evidence_ledger_event_refs',
      },
      {
        label: 'Proof Board',
        description: 'Managed rail, policy, audit, and SQL-backed checkpoints.',
        path: '/observatory/proof-board',

        source: 'policy, tool_audit and write receipts per lab',
      },
    ],
  },
  {
    question: 'Why was it allowed?',
    answer:
      'Separate verified identity and policy authorization from tool execution.',
    links: [
      {
        label: 'Gateway & policy',
        description: 'Cognito claims, Cedar decisions, and fail-closed writes.',
        path: '/observatory/write-path',

        source: 'governed_receipts (Cedar), tool_audit',
      },
      {
        label: 'Tool Registry',
        description: 'Callable schemas and the exact governed Aurora surface.',
        path: '/observatory/tools',

        source: 'tool registry, MCP schemas',
      },
    ],
  },
  {
    question: 'What reached PostgreSQL?',
    answer:
      'Inspect eligibility, rank fusion, SQL receipts, and the owning tables.',
    links: [
      {
        label: 'Search pipeline',
        description: 'pgvector, full-text search, RRF, filters, and reranking.',
        path: '/observatory/search',

        source: 'retrieval_receipts, live EXPLAIN',
      },
      {
        label: 'Retrieval comparison',
        description: 'Observed latency, index behavior, quality, and cost.',
        path: '/observatory/performance',

        source: 'measured on Aurora at run time',
      },
    ],
  },
  {
    question: 'How does this operate?',
    answer:
      'Pressure-test ownership, release gates, and production failure modes.',
    links: [
      {
        label: 'Architecture',
        description: 'Runtime boundaries, control planes, and state ownership.',
        path: '/observatory/architecture',

        source: 'source tree, deploy templates',
      },
      {
        label: 'Evaluations & production',
        description: 'Golden journeys, tenancy, reliability, and release gates.',
        path: '/observatory/evaluations',

        source: 'evaluation scorecards, golden journeys',
      },
    ],
  },
];

const GITHUB_REPOSITORY_URL =
  'https://github.com/aws-samples/sample-pellier-agentic-search-apg';

/* A source token is set in mono only when it is something a participant can
   paste: a snake_case relation or a relation with a qualifier, such as
   `governed_receipts (Cedar)`. "measured on Aurora at run time" and "golden
   journeys" describe a source in words and take the prose register, because
   mono on these surfaces means code or measurement and never a technical
   costume. The legend below the index states that contract so the two
   registers read as information rather than inconsistency. */
const IDENTIFIER_TOKEN = /^[a-z][a-z0-9_]*(?: \([A-Za-z][A-Za-z ]*\))?$/;

function sourceTokens(source: string): string[] {
  return source
    .split(',')
    .map((token) => token.trim())
    .filter(Boolean);
}

/** Every named source across the index, deduplicated. Derived, never typed:
 *  the masthead figure cannot drift away from the rows it counts. */
const NAMED_SOURCE_COUNT = new Set(
  RESOURCE_QUESTIONS.flatMap((group) =>
    group.links.flatMap((link) => sourceTokens(link.source)),
  ),
).size;

const VIEW_COUNT = RESOURCE_QUESTIONS.reduce(
  (total, group) => total + group.links.length,
  0,
);

interface MastheadFigure {
  value: number;
  label: string;
}

const MASTHEAD_FIGURES: readonly MastheadFigure[] = [
  { value: VIEW_COUNT, label: 'Reference views' },
  { value: RESOURCE_QUESTIONS.length, label: 'Participant questions' },
  { value: NAMED_SOURCE_COUNT, label: 'Named sources' },
];

/* The three columns this index has always had, expressed against the shared
   table register: the view is the row's own name, its description is prose,
   and the source it reads is an identifier. Widths are explicit and the table
   is fixed-layout, so all four question tables share one column geometry and
   the index reads as a single ledger rather than four differently ruled ones.

   The row is the target. The link stays in the View cell -- one anchor, real
   href, keyboard reachable -- and a stretched pseudo-element carries the hit
   area across the row. The mono tokens sit above that overlay so an
   identifier can still be selected and pasted; prose sits below it and is
   part of the target. */
const RESOURCE_COLUMNS: DataTableColumn<ResourceLink>[] = [
  {
    key: 'view',
    header: 'View',
    rowHeader: true,
    width: '20%',
    render: (item) => (
      <span className="workbench-resource-view">
        <Link to={item.path}>{item.label}</Link>
        <code>{item.path.replace('/observatory', '')}</code>
      </span>
    ),
  },
  {
    key: 'shows',
    header: 'What it shows',
    width: '42%',
    render: (item) => (
      <span className="workbench-resource-shows">{item.description}</span>
    ),
  },
  {
    key: 'source',
    header: 'Reads from',
    align: 'code',
    width: '38%',
    render: (item) => (
      <span className="workbench-resource-sources">
        {sourceTokens(item.source).map((token) => (
          <span
            key={token}
            className="workbench-resource-source"
            data-register={IDENTIFIER_TOKEN.test(token) ? 'identifier' : 'prose'}
          >
            {IDENTIFIER_TOKEN.test(token) ? <code>{token}</code> : token}
          </span>
        ))}
      </span>
    ),
  },
];

interface WorkbenchResourcesProps {
  compact?: boolean;
  /**
   * The Lab Collection is an orientation surface, while the live workbench is
   * an execution surface. The latter can keep this index available without
   * taking space from the Evidence ledger until a participant asks for it.
   */
  collapsible?: boolean;
  defaultExpanded?: boolean;
}

export default function WorkbenchResources({
  compact = false,
  collapsible = false,
  defaultExpanded = true,
}: WorkbenchResourcesProps) {
  const contentId = useId();
  const [expanded, setExpanded] = useState(
    () =>
      !collapsible ||
      defaultExpanded ||
      (typeof window !== 'undefined' && window.location.hash === '#resources'),
  );

  // Several reference links intentionally target /observatory/workbench#resources.
  // Opening the index before the browser scrolls there keeps that destination
  // useful without making the workbench default to a long reference section.
  useEffect(() => {
    if (!collapsible) return undefined;

    const revealForResourceHash = () => {
      if (window.location.hash === '#resources') {
        setExpanded(true);
      }
    };

    revealForResourceHash();
    window.addEventListener('hashchange', revealForResourceHash);
    return () => window.removeEventListener('hashchange', revealForResourceHash);
  }, [collapsible]);

  const content = (
    <div
      id={contentId}
      className="workbench-resources-content"
      hidden={collapsible && !expanded}
    >
      <header className="workbench-resources-heading">
        <div className="workbench-resources-title">
          <SectionEyebrow>Reference views</SectionEyebrow>
          <h2 id="workbench-resources-title" className="font-display">
            Telemetry from the running system
          </h2>
        </div>
        <div className="workbench-resources-masthead">
          <div className="workbench-resources-figures">
            {MASTHEAD_FIGURES.map((figure) => (
              <div key={figure.label} className="workbench-resource-figure">
                <span className="workbench-resource-figure-value">
                  {figure.value}
                </span>
                <span className="workbench-resource-figure-label">
                  {figure.label}
                </span>
              </div>
            ))}
          </div>
          <div className="workbench-resources-canonical">
            <p>
              Every view below reads the same Aurora tables and managed-service
              responses the agents just used. Nothing here is required to finish
              a lab: <code>psql</code> and the AgentCore CLI are the canonical
              proof, and these views only make the same rows easier to
              correlate.
            </p>
            <a
              href={GITHUB_REPOSITORY_URL}
              target="_blank"
              rel="noopener noreferrer"
            >
              Workshop source
              <ArrowUpRight size={14} strokeWidth={1.8} aria-hidden="true" />
            </a>
          </div>
        </div>
      </header>

      <div className="workbench-resources-index">
        {RESOURCE_QUESTIONS.map((group) => (
          <section
            key={group.question}
            className="workbench-resource-question"
            aria-label={group.question}
          >
            <div className="workbench-resource-question-head">
              <h3>{group.question}</h3>
              <p>{group.answer}</p>
            </div>
            <DataTable
              className="workbench-resource-table"
              columns={RESOURCE_COLUMNS}
              rows={group.links}
              rowKey={(item) => item.path}
            />
          </section>
        ))}
      </div>

      <p className="workbench-resources-legend">
        <span>
          <code>mono</code> names a table, service or artefact you can query
          directly.
        </span>
        <span>Prose names a source that has no single identifier.</span>
      </p>
    </div>
  );

  return (
    <section
      id="resources"
      className="workbench-resources"
      data-compact={compact ? 'true' : undefined}
      data-collapsible={collapsible ? 'true' : undefined}
      aria-label={collapsible ? 'Reference views' : undefined}
      aria-labelledby={collapsible ? undefined : 'workbench-resources-title'}
    >
      {collapsible ? (
        <div className="workbench-resources-disclosure">
          <button
            type="button"
            className="workbench-resources-disclosure-button"
            aria-expanded={expanded}
            aria-controls={contentId}
            onClick={() => setExpanded((current) => !current)}
          >
            <span className="workbench-resources-disclosure-copy">
              <strong>
                {expanded ? 'Hide reference views' : 'Explore reference views'}
              </strong>
              <ChevronDown
                size={14}
                strokeWidth={1.8}
                aria-hidden="true"
                data-expanded={expanded ? 'true' : undefined}
              />
            </span>
          </button>
        </div>
      ) : null}
      {content}
    </section>
  );
}
