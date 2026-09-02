import type { LucideIcon } from 'lucide-react';
import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  ClipboardCheck,
  Database,
  FileCheck,
  History,
  Network,
  ShieldCheck,
  Wrench,
} from 'lucide-react';
import { Link } from 'react-router-dom';

import './WorkbenchResources.css';

interface ResourceLink {
  label: string;
  description: string;
  path: string;
  icon: LucideIcon;
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
        icon: Activity,
      },
      {
        label: 'Proof Board',
        description: 'Managed rail, policy, audit, and SQL-backed checkpoints.',
        path: '/observatory/proof-board',
        icon: FileCheck,
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
        icon: ShieldCheck,
      },
      {
        label: 'Tool Registry',
        description: 'Callable schemas and the exact governed Aurora surface.',
        path: '/observatory/tools',
        icon: Wrench,
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
        icon: Database,
      },
      {
        label: 'Retrieval comparison',
        description: 'Observed latency, index behavior, quality, and cost.',
        path: '/observatory/performance',
        icon: History,
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
        icon: Network,
      },
      {
        label: 'Evaluations & production',
        description: 'Golden journeys, tenancy, reliability, and release gates.',
        path: '/observatory/evaluations',
        icon: ClipboardCheck,
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

      <div className="workbench-resources-grid">
        {RESOURCE_QUESTIONS.map((group) => (
          <section
            key={group.question}
            className="workbench-resource-question"
            aria-label={group.question}
          >
            <h3>{group.question}</h3>
            <p>{group.answer}</p>
            <div className="workbench-resource-links">
              {group.links.map((item) => {
                const ItemIcon = item.icon;
                return (
                  <Link key={item.path} to={item.path}>
                    <ItemIcon
                      size={17}
                      strokeWidth={1.8}
                      aria-hidden="true"
                    />
                    <span>
                      <strong>
                        {item.label}
                      </strong>
                      <small>{item.description}</small>
                    </span>
                    <ArrowRight
                      size={15}
                      strokeWidth={1.8}
                      aria-hidden="true"
                    />
                  </Link>
                );
              })}
            </div>
          </section>
        ))}
      </div>
    </section>
  );
}
