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
        description: 'Run a shopper request and inspect its evidence.',
        icon: PanelLeft,
      },
      {
        label: 'Persona journeys',
        path: '/pellier-labs/persona-journeys',
        description: 'Compare the canonical turns for Marco, Anna, and Theo.',
        icon: Workflow,
      },
      {
        label: 'Sessions',
        path: '/pellier-labs/sessions',
        description: 'Replay recorded storefront conversations.',
        icon: ListChecks,
      },
    ],
  },
  {
    label: 'Inspect',
    views: [
      {
        label: 'Agents',
        path: '/pellier-labs/agents',
        description: 'Specialist responsibilities and model handoffs.',
        icon: Bot,
      },
      {
        label: 'Tools',
        path: '/pellier-labs/tools',
        description: 'Catalog, retrieval, and Aurora operations.',
        icon: Wrench,
      },
      {
        label: 'Skills',
        path: '/pellier-labs/skills',
        description: 'Prompt overlays selected for each turn.',
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
        description: 'Intent classification and orchestration patterns.',
        icon: GitBranch,
      },
      {
        label: 'Memory',
        path: '/pellier-labs/memory',
        description: 'Profile, session, and operational records.',
        icon: MemoryStick,
      },
      {
        label: 'Write path',
        path: '/pellier-labs/write-path',
        description: 'Policy-gated inventory operations.',
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
        description: 'Latency, storage, and retrieval behavior.',
        icon: Gauge,
      },
      {
        label: 'Evaluations',
        path: '/pellier-labs/evaluations',
        description: 'Grounding, accuracy, and response checks.',
        icon: ClipboardCheck,
      },
      {
        label: 'Production patterns',
        path: '/pellier-labs/production-patterns',
        description: 'Identity, tenancy, guardrails, and tool boundaries.',
        icon: Network,
      },
    ],
  },
];

const LABS_VIEWS = LABS_VIEW_GROUPS.flatMap((group) => group.views);

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
              {LABS_VIEW_GROUPS.map((group) => (
                <div className="pellier-labs-view-menu-section" key={group.label}>
                  <DropdownMenuLabel className="pellier-labs-view-menu-label">
                    {group.label}
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
