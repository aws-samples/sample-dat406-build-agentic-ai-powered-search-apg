import { render, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import AtelierFrame from './AtelierFrame';

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

vi.mock('./AtelierContextBanner', () => ({
  default: () => null,
}));

describe('AtelierFrame', () => {
  it('owns the global chat shortcut while an Atelier route is active', async () => {
    render(
      <MemoryRouter initialEntries={['/atelier/proof-board']}>
        <Routes>
          <Route path="/atelier" element={<AtelierFrame />}>
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
