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
  GitBranch,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { useBuildState } from '../hooks/useBuildState';

interface ReferenceLink {
  label: string;
  description: string;
  path: string;
  icon: LucideIcon;
  /**
   * Show the live shipped-tool count beside this entry.
   *
   * Only the Tool Registry earns it. It is the one number that changes when a
   * participant finishes the guided exercise (14/15 -> 15/15), so it belongs
   * where they are choosing where to look. Every other count here would be
   * decoration.
   */
  showToolCount?: boolean;
}

interface ReferenceGroup {
  title: string;
  description: string;
  links: ReferenceLink[];
}

const REFERENCE_GROUPS: ReferenceGroup[] = [
  {
    title: 'Proof views',
    description:
      'Verify the governed result and its durable audit trail.',
    links: [
      {
        label: 'Proof Board',
        description: 'Governed claims, controls, and the evidence behind them.',
        path: '/observatory/proof-board',
        icon: FileCheck,
      },
      {
        label: 'Audit Proof',
        description: 'Persisted tool, policy, and transaction receipts.',
        path: '/observatory/audit-proof',
        icon: ScrollText,
      },
      {
        label: 'Operator Lineage',
        description: 'Live shopper handoff, Strands graph, checkpoint, and outcome.',
        path: '/observatory/operator-lineage',
        icon: GitBranch,
      },
    ],
  },
  {
    title: 'Replay a turn',
    description:
      'Compare canonical shopper paths and replay captured sessions.',
    links: [
      {
        label: 'Persona Journeys',
        description: 'Compare canonical shopper paths and specialist handoffs.',
        path: '/observatory/persona-journeys',
        icon: Footprints,
      },
      {
        label: 'Sessions',
        description: 'Replay captured governed turns and their emitted evidence.',
        path: '/observatory/sessions',
        icon: History,
      },
    ],
  },
  {
    title: 'Inspect the build',
    description:
      'A focused technical lens on one part of the system.',
    links: [
      {
        label: 'Architecture',
        description: 'Runtime boundaries, control planes, and component ownership.',
        path: '/observatory/architecture',
        icon: Network,
      },
      {
        label: 'Tool Registry',
        description: 'Callable contracts and governed Aurora operations.',
        path: '/observatory/tools',
        icon: Wrench,
        showToolCount: true,
      },
      {
        label: 'Skills',
        description: 'Prompt overlays selected for each governed request.',
        path: '/observatory/skills',
        icon: BookOpen,
      },
      {
        label: 'Search Pipeline',
        description: 'Hybrid retrieval, rank fusion, filtering, and reranking.',
        path: '/observatory/search',
        icon: Search,
      },
      {
        label: 'Routing',
        description: 'Intent classification and deterministic specialist dispatch.',
        path: '/observatory/routing',
        icon: Signpost,
      },
      {
        label: 'Memory Types',
        description:
          'AgentCore turns and preferences, separated from Aurora state and audit evidence.',
        path: '/observatory/memory',
        icon: IdCard,
      },
      {
        label: 'Gateway & Policy',
        description: 'Policy-gated mutations and their durable audit path.',
        path: '/observatory/write-path',
        icon: ShieldCheck,
      },
    ],
  },
  {
    title: 'Measure',
    description:
      'Timing, quality, and the decisions a production deployment faces.',
    links: [
      {
        label: 'Retrieval Comparison',
        description: 'Retrieval timing, index behavior, and benchmark controls.',
        path: '/observatory/performance',
        icon: Gauge,
      },
      {
        label: 'Evaluations',
        description: 'Golden journeys and response-quality release checks.',
        path: '/observatory/evaluations',
        icon: ClipboardCheck,
      },
      {
        label: 'Production Patterns',
        description: 'Identity, tenancy, reliability, and guardrail decisions.',
        path: '/observatory/production-patterns',
        icon: Layers,
      },
    ],
  },
];

export default function ReferencesIndex() {
  const buildState = useBuildState();
  // No hardcoded fallback. A stale literal reads as a confident "not wired
  // yet", which is indistinguishable from the pre-exercise state on the one
  // number a participant watches. An em dash says "unknown" honestly.
  const toolCount =
    buildState.toolTotal > 0
      ? `${buildState.toolShipped}/${buildState.toolTotal}`
      : '—';

  return (
    <div className="observatory-references">
      <header className="observatory-references-header">
        <h1>Proof &amp; References</h1>
        <p>
          Every view the Observatory offers, in one place. The canonical proof
          is the curl and SQL in your Code Editor; these read the same rows for
          you. Open one when a lab step or your own curiosity points here.
        </p>
      </header>

      <div className="observatory-reference-groups">
        {REFERENCE_GROUPS.map((group) => {
          const sectionId = `reference-${group.title.toLowerCase().replace(/ /g, '-')}`;
          return (
            <section
              key={group.title}
              className="observatory-reference-group"
              aria-labelledby={sectionId}
            >
              <div className="observatory-reference-group-heading">
                <h2 id={sectionId}>{group.title}</h2>
                <p>{group.description}</p>
              </div>
              <div className="observatory-reference-links">
                {group.links.map((item) => {
                  const ItemIcon = item.icon;
                  return (
                    <Link
                      key={item.path}
                      to={item.path}
                      className="observatory-reference-link"
                    >
                      <span className="observatory-reference-link-icon">
                        <ItemIcon size={19} strokeWidth={1.85} aria-hidden="true" />
                      </span>
                      <span className="observatory-reference-link-copy">
                        <strong>
                          {item.label}
                          {item.showToolCount && (
                            <span
                              className="observatory-reference-link-count"
                              data-testid="reference-tool-count"
                            >
                              {toolCount}
                            </span>
                          )}
                        </strong>
                        <span>{item.description}</span>
                      </span>
                      <ArrowRight
                        className="observatory-reference-link-arrow"
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
