/**
 * TabNav — Instrument Sans tab links with burgundy underline on active.
 *
 * Used for session detail tab navigation (Chat, Telemetry, Brief)
 * and other tabbed interfaces.
 *
 * Requirements: 15.7
 */

import React from 'react';

export interface Tab {
  id: string;
  label: string;
  href?: string;
}

export interface TabNavProps {
  tabs: Tab[];
  activeTab: string;
  onTabChange?: (tabId: string) => void;
  className?: string;
}

export const TabNav: React.FC<TabNavProps> = ({
  tabs,
  activeTab,
  onTabChange,
  className = '',
}) => {
  return (
    <nav
      role="tablist"
      className={className}
      style={{
        display: 'flex',
        gap: '28px',
        borderBottom: '1px solid var(--obs-rule-1)',
        paddingBottom: '0',
      }}
    >
      {tabs.map((tab) => {
        const isActive = tab.id === activeTab;

        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            onClick={() => onTabChange?.(tab.id)}
            style={{
              fontFamily: 'var(--obs-heading)',
              fontSize: 'var(--obs-tab-size)',
              fontWeight: isActive ? 600 : 500,
              letterSpacing: 0,
              color: isActive ? 'var(--obs-ink-1)' : 'var(--obs-ink-3)',
              background: 'none',
              border: 'none',
              borderBottom: isActive
                ? '2px solid var(--obs-red-1)'
                : '2px solid transparent',
              paddingBottom: '8px',
              paddingTop: '0',
              paddingLeft: '0',
              paddingRight: '0',
              cursor: 'pointer',
              transition: 'color 0.15s ease, border-color 0.15s ease',
              whiteSpace: 'nowrap',
            }}
          >
            {tab.label}
          </button>
        );
      })}
    </nav>
  );
};
