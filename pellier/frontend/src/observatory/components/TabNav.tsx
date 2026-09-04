/**
 * TabNav — Instrument Sans tab links with burgundy underline on active.
 *
 * Used for session detail tab navigation (Chat, Telemetry, Brief)
 * and other tabbed interfaces.
 *
 * Requirements: 15.7
 */

import React, { useRef } from 'react';

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
  const tabRefs = useRef(new Map<string, HTMLButtonElement>());

  /**
   * WAI-ARIA tabs, automatic activation: arrow keys move focus and select,
   * Home and End jump to the ends, and the list is one tab stop. Without this
   * a keyboard user paid one Tab press per tab to cross the strip.
   */
  const handleKeyDown = (event: React.KeyboardEvent, index: number) => {
    const lastIndex = tabs.length - 1;
    let nextIndex: number | null = null;
    if (event.key === 'ArrowRight') nextIndex = index === lastIndex ? 0 : index + 1;
    else if (event.key === 'ArrowLeft') nextIndex = index === 0 ? lastIndex : index - 1;
    else if (event.key === 'Home') nextIndex = 0;
    else if (event.key === 'End') nextIndex = lastIndex;
    if (nextIndex === null) return;

    event.preventDefault();
    const nextTab = tabs[nextIndex];
    if (!nextTab) return;
    tabRefs.current.get(nextTab.id)?.focus();
    onTabChange?.(nextTab.id);
  };

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
      {tabs.map((tab, index) => {
        const isActive = tab.id === activeTab;

        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            tabIndex={isActive ? 0 : -1}
            ref={(node) => {
              if (node) tabRefs.current.set(tab.id, node);
              else tabRefs.current.delete(tab.id);
            }}
            onKeyDown={(event) => handleKeyDown(event, index)}
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
