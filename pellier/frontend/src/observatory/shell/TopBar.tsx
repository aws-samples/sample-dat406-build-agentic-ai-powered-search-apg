/**
 * Pellier Observatory top bar.
 *
 * The governed workbench is the primary destination. Every deeper surface is
 * intentionally grouped behind one Proof & References index.
 */

import React, { useState } from 'react';
import { BookOpen, LibraryBig, ReceiptText } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import PellierHomeLink from '../../components/PellierHomeLink';
import PersonaModal from '../../components/PersonaModal';
import { usePersona } from '../../contexts/PersonaContext';
import { getPersonaPhoto } from '../../data/personaPhotos';
import { PresencePill } from '../../shared';
import { NAV } from '../../copy';

const OBSERVATORY_TABS = [
  {
    label: 'Lab Collection',
    path: '/observatory',
    icon: LibraryBig,
  },
  {
    label: 'Live Workbench',
    path: '/observatory/workbench',
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
  const isLabCollection =
    pathname === '/observatory' ||
    pathname === '/observatory/' ||
    pathname.startsWith('/observatory/labs/');
  const isWorkbench =
    pathname === '/observatory/workbench' ||
    pathname.startsWith('/observatory/workbench/');

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
          {OBSERVATORY_TABS.map((tab) => {
            const isActive =
              tab.path === '/observatory'
                ? isLabCollection
                : tab.path === '/observatory/workbench'
                  ? isWorkbench
                  : !isLabCollection && !isWorkbench;
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

          <PellierHomeLink testId="back-to-pellier" />
        </div>
      </header>
      <PersonaModal open={personaModalOpen} onClose={() => setPersonaModalOpen(false)} />
    </>
  );
};

export default TopBar;
