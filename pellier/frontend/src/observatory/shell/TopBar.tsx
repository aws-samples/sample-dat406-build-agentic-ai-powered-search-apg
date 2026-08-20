/**
 * Pellier Observatory top bar.
 *
 * The governed workbench is the primary destination. Every deeper surface is
 * intentionally grouped behind one Proof & References index.
 */

import React, { useState } from 'react';
import { ArrowLeft, BookOpen, ReceiptText } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import PersonaModal from '../../components/PersonaModal';
import { usePersona } from '../../contexts/PersonaContext';
import { getPersonaPhoto } from '../../data/personaPhotos';
import { PresencePill } from '../../shared';
import { NAV } from '../../copy';

const GITHUB_REPOSITORY_URL =
  'https://github.com/aws-samples/sample-pellier-agentic-search-apg';

const OBSERVATORY_TABS = [
  {
    label: 'Live Workbench',
    path: '/observatory',
    icon: ReceiptText,
  },
  {
    label: 'Proof & References',
    path: '/observatory/references',
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
    pathname === '/observatory' || pathname === '/observatory/';

  return (
    <>
      <header className="observatory-topbar" data-testid="observatory-topbar">
        <div className="observatory-topbar-start">
          <Link to="/observatory" className="observatory-wordmark">
            {NAV.OBSERVATORY}
          </Link>
          {/* Stated on the surface, not only at the door. A participant who
              arrives by deep link, screenshot, or the workshop guide never sees
              the storefront badge, and they are the ones most likely to assume
              this is a fifth lab they still owe. */}
          <span
            className="observatory-optional"
            data-testid="observatory-optional-badge"
            title="Explore freely. Finishing the workshop does not depend on this surface."
          >
            {NAV.OBSERVATORY_OPTIONAL}
          </span>
        </div>

        <nav className="observatory-tabs" aria-label="Pellier Observatory views">
          {OBSERVATORY_TABS.map((tab, index) => {
            const isActive = index === 0 ? isWorkbench : !isWorkbench;
            const TabIcon = tab.icon;
            return (
              <Link
                key={tab.path}
                to={tab.path}
                className="observatory-tab"
                data-active={isActive ? 'true' : undefined}
                aria-current={isActive ? 'page' : undefined}
              >
                <TabIcon size={15} strokeWidth={1.8} aria-hidden="true" />
                <span>{tab.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="observatory-topbar-end">
          <div className="observatory-presence">
            <PresencePill surface="observatory" personaId={persona?.id} />
          </div>

          <button
            type="button"
            data-testid="observatory-persona-switcher"
            className="observatory-persona"
            onClick={() => setPersonaModalOpen(true)}
            aria-label={`Switch persona${persona?.display_name ? ` from ${persona.display_name}` : ''}`}
            title="Switch persona"
          >
            {photoUrl ? (
              <img src={photoUrl} alt="" aria-hidden="true" />
            ) : (
              <span
                className="observatory-persona-initial"
                aria-hidden="true"
                style={{ background: avatarColor }}
              >
                {avatarInitial}
              </span>
            )}
            <span className="observatory-persona-copy">
              <small>Persona</small>
              <strong>{personaLabel}</strong>
            </span>
          </button>

          <Link
            to="/"
            data-testid="back-to-pellier"
            aria-label="Back to Pellier"
            className="observatory-back"
          >
            <ArrowLeft size={16} strokeWidth={1.8} aria-hidden="true" />
            <span>Back to Pellier</span>
          </Link>

          <a
            href={GITHUB_REPOSITORY_URL}
            className="observatory-icon-button"
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
