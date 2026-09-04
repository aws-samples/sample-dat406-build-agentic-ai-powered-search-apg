/**
 * TabNav keyboard contract (WAI-ARIA tabs pattern, automatic activation).
 *
 * One tab stop for the whole list: the active tab is tabbable, the rest are
 * reached with the arrow keys, Home and End jump to the ends, and moving
 * focus selects. Without this, every tab was its own stop and a keyboard
 * user crossed the list one tab at a time.
 */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { TabNav } from './TabNav';

const TABS = [
  { id: 'chat', label: 'Chat' },
  { id: 'telemetry', label: 'Telemetry' },
  { id: 'brief', label: 'Brief' },
];

describe('TabNav keyboard navigation', () => {
  it('uses a roving tabindex so the list is one tab stop', () => {
    render(<TabNav tabs={TABS} activeTab="telemetry" onTabChange={vi.fn()} />);

    expect(screen.getByRole('tab', { name: 'Chat' })).toHaveAttribute('tabindex', '-1');
    expect(screen.getByRole('tab', { name: 'Telemetry' })).toHaveAttribute('tabindex', '0');
    expect(screen.getByRole('tab', { name: 'Brief' })).toHaveAttribute('tabindex', '-1');
  });

  it('moves with ArrowRight and ArrowLeft, wrapping at the ends', async () => {
    const user = userEvent.setup();
    const onTabChange = vi.fn();
    render(<TabNav tabs={TABS} activeTab="brief" onTabChange={onTabChange} />);

    screen.getByRole('tab', { name: 'Brief' }).focus();
    await user.keyboard('{ArrowRight}');
    expect(screen.getByRole('tab', { name: 'Chat' })).toHaveFocus();
    expect(onTabChange).toHaveBeenLastCalledWith('chat');

    await user.keyboard('{ArrowLeft}');
    expect(screen.getByRole('tab', { name: 'Brief' })).toHaveFocus();
    expect(onTabChange).toHaveBeenLastCalledWith('brief');
  });

  it('jumps to the first and last tab with Home and End', async () => {
    const user = userEvent.setup();
    const onTabChange = vi.fn();
    render(<TabNav tabs={TABS} activeTab="telemetry" onTabChange={onTabChange} />);

    screen.getByRole('tab', { name: 'Telemetry' }).focus();
    await user.keyboard('{End}');
    expect(screen.getByRole('tab', { name: 'Brief' })).toHaveFocus();
    expect(onTabChange).toHaveBeenLastCalledWith('brief');

    await user.keyboard('{Home}');
    expect(screen.getByRole('tab', { name: 'Chat' })).toHaveFocus();
    expect(onTabChange).toHaveBeenLastCalledWith('chat');
  });
});
