import { ArrowUpRight } from 'lucide-react';
import { Link } from 'react-router-dom';

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

interface WorkbenchResourcesProps {
  compact?: boolean;
}

export default function WorkbenchResources({
  compact = false,
}: WorkbenchResourcesProps) {
  return (
    <section
      id="resources"
      className="workbench-resources"
      data-compact={compact ? 'true' : undefined}
      aria-labelledby="workbench-resources-title"
    >
      <header className="workbench-resources-heading">
        <div>
          <span>Reference views</span>
          <h2 id="workbench-resources-title" className="font-display">
            Telemetry from the running system
          </h2>
        </div>
        <div className="workbench-resources-canonical">
          <p>
            Every view below reads the same Aurora tables and managed-service
            responses the agents just used. Nothing here is required to finish
            a lab: <code>psql</code> and the AgentCore CLI are the canonical
            proof, and these views only make the same rows easier to correlate.
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
            <table className="workbench-resource-table">
              <thead>
                <tr>
                  <th scope="col">View</th>
                  <th scope="col">What it shows</th>
                  <th scope="col">Reads from</th>
                </tr>
              </thead>
              <tbody>
                {group.links.map((item) => (
                  <tr key={item.path}>
                    <th scope="row">
                      <Link to={item.path}>{item.label}</Link>
                      <code>{item.path.replace('/observatory', '')}</code>
                    </th>
                    <td>{item.description}</td>
                    <td>
                      <code>{item.source}</code>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        ))}
      </div>
    </section>
  );
}
