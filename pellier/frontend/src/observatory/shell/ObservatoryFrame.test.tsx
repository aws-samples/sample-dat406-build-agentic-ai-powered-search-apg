import { render, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import ObservatoryFrame from './ObservatoryFrame';

const mocks = vi.hoisted(() => ({
  setChatSurface: vi.fn(),
}));

vi.mock('../../contexts/UIContext', () => ({
  useUI: () => ({ setChatSurface: mocks.setChatSurface }),
}));

vi.mock('./TopBar', () => ({
  default: () => <header>Top bar</header>,
}));

vi.mock('./ObservatoryContextBanner', () => ({
  default: () => null,
}));

describe('ObservatoryFrame', () => {
  it('owns the global chat shortcut while an Observatory route is active', async () => {
    render(
      <MemoryRouter initialEntries={['/observatory/proof-board']}>
        <Routes>
          <Route path="/observatory" element={<ObservatoryFrame />}>
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
