import type { LucideIcon } from 'lucide-react';
import {
  ArrowRight,
  BookOpen,
  ClipboardCheck,
  FileCheck,
  Footprints,
  Gauge,
  History,
  IdCard,
  Layers,
  Network,
  ScrollText,
  Search,
  ShieldCheck,
  Signpost,
  Wrench,
} from 'lucide-react';
import { Link } from 'react-router-dom';

interface ReferenceLink {
  label: string;
  description: string;
  path: string;
  icon: LucideIcon;
}

interface ReferenceGroup {
  title: string;
  description: string;
  links: ReferenceLink[];
}

const REFERENCE_GROUPS: ReferenceGroup[] = [
  {
    title: 'Prove and replay',
    description:
      'Review the governed evidence path or replay a canonical shopper request.',
    links: [
      {
        label: 'Proof board',
        description: 'Governed claims, controls, and the evidence behind them.',
        path: '/pellier-labs/proof-board',
        icon: FileCheck,
      },
      {
        label: 'Audit proof',
        description: 'Persisted tool, policy, and transaction receipts.',
        path: '/pellier-labs/audit-proof',
        icon: ScrollText,
      },
      {
        label: 'Persona journeys',
        description: 'Compare canonical shopper paths and specialist handoffs.',
        path: '/pellier-labs/persona-journeys',
        icon: Footprints,
      },
      {
        label: 'Sessions',
        description: 'Replay captured governed turns and their emitted evidence.',
        path: '/pellier-labs/sessions',
        icon: History,
      },
    ],
  },
  {
    title: 'Inspect the control path',
    description:
      'Open a focused technical lens when a lab step or investigation sends you deeper.',
    links: [
      {
        label: 'Architecture',
        description: 'Runtime boundaries, control planes, and component ownership.',
        path: '/pellier-labs/architecture',
        icon: Network,
      },
      {
        label: 'Tools',
        description: 'Callable contracts and governed Aurora operations.',
        path: '/pellier-labs/tools',
        icon: Wrench,
      },
      {
        label: 'Skills',
        description: 'Prompt overlays selected for each governed request.',
        path: '/pellier-labs/skills',
        icon: BookOpen,
      },
      {
        label: 'Search',
        description: 'Hybrid retrieval, rank fusion, filtering, and reranking.',
        path: '/pellier-labs/search',
        icon: Search,
      },
      {
        label: 'Routing',
        description: 'Intent classification and deterministic specialist dispatch.',
        path: '/pellier-labs/routing',
        icon: Signpost,
      },
      {
        label: 'Memory',
        description:
          'AgentCore turns and preferences, separated from Aurora state and audit evidence.',
        path: '/pellier-labs/memory',
        icon: IdCard,
      },
      {
        label: 'Gateway and policy',
        description: 'Policy-gated mutations and their durable audit path.',
        path: '/pellier-labs/write-path',
        icon: ShieldCheck,
      },
    ],
  },
  {
    title: 'Evaluate and productionize',
    description:
      'Use these deeper lenses after the required governed build and proof path.',
    links: [
      {
        label: 'Performance',
        description: 'Retrieval timing, index behavior, and benchmark controls.',
        path: '/pellier-labs/performance',
        icon: Gauge,
      },
      {
        label: 'Evaluations',
        description: 'Golden journeys and response-quality release checks.',
        path: '/pellier-labs/evaluations',
        icon: ClipboardCheck,
      },
      {
        label: 'Production patterns',
        description: 'Identity, tenancy, reliability, and guardrail decisions.',
        path: '/pellier-labs/production-patterns',
        icon: Layers,
      },
    ],
  },
];

export default function ReferencesIndex() {
  return (
    <div className="pellier-labs-references">
      <header className="pellier-labs-references-header">
        <h1>Optional Deep Dives</h1>
        <p>
          Keep the live governed workbench and proof path primary. Open a deep
          dive when a lab step, facilitator, or investigation sends you further.
        </p>
      </header>

      <div className="pellier-labs-reference-groups">
        {REFERENCE_GROUPS.map((group) => {
          const sectionId = `reference-${group.title.toLowerCase().replace(/ /g, '-')}`;
          return (
            <section
              key={group.title}
              className="pellier-labs-reference-group"
              aria-labelledby={sectionId}
            >
              <div className="pellier-labs-reference-group-heading">
                <h2 id={sectionId}>{group.title}</h2>
                <p>{group.description}</p>
              </div>
              <div className="pellier-labs-reference-links">
                {group.links.map((item) => {
                  const ItemIcon = item.icon;
                  return (
                    <Link
                      key={item.path}
                      to={item.path}
                      className="pellier-labs-reference-link"
                    >
                      <span className="pellier-labs-reference-link-icon">
                        <ItemIcon size={19} strokeWidth={1.85} aria-hidden="true" />
                      </span>
                      <span className="pellier-labs-reference-link-copy">
                        <strong>{item.label}</strong>
                        <span>{item.description}</span>
                      </span>
                      <ArrowRight
                        className="pellier-labs-reference-link-arrow"
                        size={17}
                        strokeWidth={1.7}
                        aria-hidden="true"
                      />
                    </Link>
                  );
                })}
              </div>
            </section>
          );
        })}
      </div>
    </div>
  );
}
