/**
 * Pellier Labs top bar.
 *
 * The Labs identity is singular and the storefront return is explicit so the
 * inspection canvas remains the primary surface at every viewport width.
 */

import React, { useState } from 'react';
import type { LucideIcon } from 'lucide-react';
import {
  ArrowLeft,
  Bot,
  Brain,
  Check,
  ChevronDown,
  ClipboardCheck,
  Gauge,
  GitBranch,
  ListChecks,
  MemoryStick,
  Network,
  PackageSearch,
  PanelLeft,
  Search,
  Wrench,
  Workflow,
} from 'lucide-react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import PersonaModal from '../../components/PersonaModal';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from '../../components/ui';
import { usePersona } from '../../contexts/PersonaContext';
import { getPersonaPhoto } from '../../data/personaPhotos';
import {
  GROUP_LABELS,
  interactionForPath,
  type LabsInteraction,
} from './labsInteraction';

interface LabsView {
  label: string;
  path: string;
  description: string;
  icon: LucideIcon;
}

interface LabsViewGroup {
  label: string;
  views: LabsView[];
}

const LABS_VIEW_GROUPS: LabsViewGroup[] = [
  {
    label: 'Guided demo',
    views: [
      {
        label: 'Live workbench',
        path: '/pellier-labs',
        description: 'Run a request and inspect emitted evidence.',
        icon: PanelLeft,
      },
      {
        label: 'Persona journeys',
        path: '/pellier-labs/persona-journeys',
        description: 'Compare canonical request and tool paths.',
        icon: Workflow,
      },
      {
        label: 'Sessions',
        path: '/pellier-labs/sessions',
        description: 'Replay a captured request and trace.',
        icon: ListChecks,
      },
    ],
  },
  {
    label: 'Inspect',
    views: [
      {
        label: 'Architecture',
        path: '/pellier-labs/architecture',
        description: 'Live request topology and component boundaries.',
        icon: Network,
      },
      {
        label: 'Agents',
        path: '/pellier-labs/agents',
        description: 'Specialist contracts and handoffs.',
        icon: Bot,
      },
      {
        label: 'Tools',
        path: '/pellier-labs/tools',
        description: 'Callable contracts and Aurora operations.',
        icon: Wrench,
      },
      {
        label: 'Skills',
        path: '/pellier-labs/skills',
        description: 'Prompt overlays selected per request.',
        icon: Brain,
      },
      {
        label: 'Search',
        path: '/pellier-labs/search',
        description: 'Hybrid retrieval, fusion, and reranking.',
        icon: Search,
      },
      {
        label: 'Routing',
        path: '/pellier-labs/routing',
        description: 'Intent classification and dispatch.',
        icon: GitBranch,
      },
      {
        label: 'Memory',
        path: '/pellier-labs/memory',
        description: 'Working state and durable records.',
        icon: MemoryStick,
      },
      {
        label: 'Write path',
        path: '/pellier-labs/write-path',
        description: 'Policy-gated, audited mutations.',
        icon: PackageSearch,
      },
    ],
  },
  {
    label: 'Evaluate',
    views: [
      {
        label: 'Performance',
        path: '/pellier-labs/performance',
        description: 'Turn timing and retrieval budgets.',
        icon: Gauge,
      },
      {
        label: 'Evaluations',
        path: '/pellier-labs/evaluations',
        description: 'Golden journeys and response checks.',
        icon: ClipboardCheck,
      },
      {
        label: 'Production patterns',
        path: '/pellier-labs/production-patterns',
        description: 'Identity, tenancy, and guardrails.',
        icon: Network,
      },
    ],
  },
];

const LABS_VIEWS = LABS_VIEW_GROUPS.flatMap((group) => group.views);

/*
 * The picker used to group by subject (Guided demo / Inspect / Evaluate), which
 * left Live workbench sitting beside two views that run nothing. It now groups
 * by what the participant does, from the shared contract in labsInteraction, so
 * "which of these fifteen do I actually operate" is answerable at a glance.
 * Order inside each group is preserved from the definitions above.
 */
const LABS_INTERACTION_GROUPS: Array<{
  interaction: LabsInteraction;
  label: string;
  views: LabsView[];
}> = (['interactive', 'reference'] as const).map((interaction) => ({
  interaction,
  label: GROUP_LABELS[interaction],
  views: LABS_VIEWS.filter(
    (view) => interactionForPath(view.path) === interaction,
  ),
}));

const TopBar: React.FC = () => {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { persona } = usePersona();
  const [personaModalOpen, setPersonaModalOpen] = useState(false);

  const avatarInitial = persona?.avatar_initial ?? '?';
  const avatarColor = persona?.avatar_color ?? '#665f58';
  const personaLabel = persona?.display_name?.split(' ')[0] ?? 'Choose profile';
  const photoUrl = persona ? getPersonaPhoto(persona.id) : undefined;
  const activeLabsView =
    LABS_VIEWS.find(
      (view) =>
        pathname === view.path ||
        (view.path !== '/pellier-labs' &&
          pathname.startsWith(`${view.path}/`)),
    ) ?? LABS_VIEW_GROUPS[0].views[0];
  const ActiveViewIcon = activeLabsView.icon;

  return (
    <>
      <header className="pellier-labs-topbar" data-testid="agent-trace-topbar">
        <div className="pellier-labs-topbar-start">
          <Link to="/pellier-labs" className="pellier-labs-wordmark">
            Pellier Labs
          </Link>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                className="pellier-labs-view-trigger"
                data-testid="pellier-labs-view-switcher"
                aria-label={`Pellier Labs view: ${activeLabsView.label}`}
                title="Open Pellier Labs navigation"
              >
                <ActiveViewIcon
                  className="pellier-labs-view-trigger-icon"
                  size={16}
                  strokeWidth={1.8}
                  aria-hidden="true"
                />
                <span className="pellier-labs-view-trigger-label">
                  {activeLabsView.label}
                </span>
                <ChevronDown
                  className="pellier-labs-view-trigger-chevron"
                  size={15}
                  strokeWidth={1.8}
                  aria-hidden="true"
                />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              className="pellier-labs-view-menu"
              align="start"
              sideOffset={10}
              collisionPadding={12}
            >
              {LABS_INTERACTION_GROUPS.map((group) => (
                <div
                  className="pellier-labs-view-menu-section"
                  data-interaction={group.interaction}
                  key={group.label}
                >
                  <DropdownMenuLabel className="pellier-labs-view-menu-label">
                    {group.label}
                    <span className="pellier-labs-view-menu-count">
                      {group.views.length}
                    </span>
                  </DropdownMenuLabel>
                  <DropdownMenuGroup>
                    {group.views.map((view) => {
                      const isActive = view.path === activeLabsView.path;
                      const ViewIcon = view.icon;
                      return (
                        <DropdownMenuItem
                          key={view.path}
                          className="pellier-labs-view-menu-item"
                          data-active={isActive ? 'true' : undefined}
                          data-interaction={group.interaction}
                          onSelect={() => navigate(view.path)}
                        >
                          <span
                            className="pellier-labs-view-menu-icon"
                            aria-hidden="true"
                          >
                            <ViewIcon size={15} strokeWidth={1.8} />
                          </span>
                          <span className="pellier-labs-view-menu-copy">
                            <strong>{view.label}</strong>
                            <small>{view.description}</small>
                          </span>
                          {isActive ? (
                            <Check
                              className="pellier-labs-view-menu-check"
                              size={15}
                              strokeWidth={2}
                              aria-hidden="true"
                            />
                          ) : null}
                        </DropdownMenuItem>
                      );
                    })}
                  </DropdownMenuGroup>
                </div>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        <div className="pellier-labs-topbar-end">
          <button
            type="button"
            data-testid="agent-trace-persona-switcher"
            className="pellier-labs-persona"
            onClick={() => setPersonaModalOpen(true)}
            aria-label={`Switch persona${persona?.display_name ? ` from ${persona.display_name}` : ''}`}
            title="Switch persona"
          >
            {photoUrl ? (
              <img src={photoUrl} alt="" aria-hidden="true" />
            ) : (
              <span
                className="pellier-labs-persona-initial"
                aria-hidden="true"
                style={{ background: avatarColor }}
              >
                {avatarInitial}
              </span>
            )}
            <span className="pellier-labs-persona-copy">
              <small>Persona</small>
              <strong>{personaLabel}</strong>
            </span>
          </button>

          <Link
            to="/"
            data-testid="back-to-pellier"
            aria-label="Back to Pellier"
            className="pellier-labs-back"
          >
            <ArrowLeft size={16} strokeWidth={1.8} aria-hidden="true" />
            <span>Back to Pellier</span>
          </Link>
        </div>
      </header>
      <PersonaModal open={personaModalOpen} onClose={() => setPersonaModalOpen(false)} />
    </>
  );
};

export default TopBar;
