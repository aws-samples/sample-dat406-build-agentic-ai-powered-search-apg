/**
 * Pellier Observatory top bar.
 *
 * The governed workbench is the primary destination. Deeper evidence routes
 * are linked from the collection and workbench rather than becoming another
 * first-level navigation surface.
 */

import React from 'react';
import { LibraryBig } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import PellierHomeLink from '../../components/PellierHomeLink';
import { usePersona } from '../../contexts/PersonaContext';
import { PresencePill } from '../../shared';
import { NAV } from '../../copy';

const OBSERVATORY_TABS = [
  {
    label: 'Labs & Workbench',
    path: '/observatory',
    icon: LibraryBig,
  },
] as const;

const TopBar: React.FC = () => {
  const { pathname } = useLocation();
  const { persona } = usePersona();
  const isLabWorkspace = pathname.startsWith('/observatory');

  return (
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
          const isActive = isLabWorkspace;
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

        <PellierHomeLink testId="back-to-pellier" />
      </div>
    </header>
  );
};

export default TopBar;
