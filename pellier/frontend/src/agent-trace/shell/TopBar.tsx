/**
 * Pellier Labs top bar.
 *
 * The Labs identity is singular and the storefront return is explicit so the
 * inspection canvas remains the primary surface at every viewport width.
 */

import React, { useState } from 'react';
import {
  ArrowLeft,
  BookOpen,
  ReceiptText,
} from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import PersonaModal from '../../components/PersonaModal';
import { usePersona } from '../../contexts/PersonaContext';
import { getPersonaPhoto } from '../../data/personaPhotos';

const GITHUB_REPOSITORY_URL =
  'https://github.com/aws-samples/sample-pellier-agentic-search-apg';

const LABS_TABS = [
  {
    label: 'Live Workbench',
    path: '/pellier-labs',
    icon: ReceiptText,
  },
  {
    label: 'Optional Deep Dives',
    path: '/pellier-labs/references',
    icon: BookOpen,
  },
] as const;

const TopBar: React.FC = () => {
  const { pathname } = useLocation();
  const { persona } = usePersona();
  const [personaModalOpen, setPersonaModalOpen] = useState(false);

  const avatarInitial = persona?.avatar_initial ?? '?';
  const avatarColor = persona?.avatar_color ?? '#665f58';
  const personaLabel = persona?.display_name?.split(' ')[0] ?? 'Choose profile';
  const photoUrl = persona ? getPersonaPhoto(persona.id) : undefined;
  const isWorkbench =
    pathname === '/pellier-labs' || pathname === '/pellier-labs/';

  return (
    <>
      <header className="pellier-labs-topbar" data-testid="agent-trace-topbar">
        <div className="pellier-labs-topbar-start">
          <Link to="/pellier-labs" className="pellier-labs-wordmark">
            Pellier Labs
          </Link>
        </div>

        <nav className="pellier-labs-tabs" aria-label="Pellier Labs views">
          {LABS_TABS.map((tab, index) => {
            const isActive = index === 0 ? isWorkbench : !isWorkbench;
            const TabIcon = tab.icon;
            return (
              <Link
                key={tab.path}
                to={tab.path}
                className="pellier-labs-tab"
                data-active={isActive ? 'true' : undefined}
                aria-current={isActive ? 'page' : undefined}
              >
                <TabIcon size={15} strokeWidth={1.8} aria-hidden="true" />
                <span>{tab.label}</span>
              </Link>
            );
          })}
        </nav>

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

          <a
            href={GITHUB_REPOSITORY_URL}
            className="pellier-labs-icon-button"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="View Pellier repository on GitHub"
            title="View Pellier repository on GitHub"
          >
            <svg
              viewBox="0 0 16 16"
              aria-hidden="true"
              focusable="false"
            >
              <path
                fill="currentColor"
                fillRule="evenodd"
                clipRule="evenodd"
                d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82A7.6 7.6 0 0 1 8.02 3.86c.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.02 8.02 0 0 0 16 8c0-4.42-3.58-8-8-8Z"
              />
            </svg>
          </a>
        </div>
      </header>
      <PersonaModal open={personaModalOpen} onClose={() => setPersonaModalOpen(false)} />
    </>
  );
};

export default TopBar;
