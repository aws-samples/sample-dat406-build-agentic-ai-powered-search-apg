import { render, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import AgentTraceFrame from './AgentTraceFrame';

const mocks = vi.hoisted(() => ({
  setChatSurface: vi.fn(),
}));

vi.mock('../../contexts/UIContext', () => ({
  useUI: () => ({ setChatSurface: mocks.setChatSurface }),
}));

vi.mock('./Sidebar', () => ({
  default: () => <aside>Sidebar</aside>,
}));

vi.mock('./TopBar', () => ({
  default: () => <header>Top bar</header>,
}));

vi.mock('./AgentTraceContextBanner', () => ({
  default: () => null,
}));

describe('AgentTraceFrame', () => {
  it('owns the global chat shortcut while an Agent Trace route is active', async () => {
    render(
      <MemoryRouter initialEntries={['/agent-trace/proof-board']}>
        <Routes>
          <Route path="/agent-trace" element={<AgentTraceFrame />}>
            <Route path="proof-board" element={<div>Proof board</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(mocks.setChatSurface).toHaveBeenCalledWith('concierge');
    });
  });
});
