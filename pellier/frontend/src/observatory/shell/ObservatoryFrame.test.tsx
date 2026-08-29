import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import ObservatoryFrame from './ObservatoryFrame';

vi.mock('./TopBar', () => ({
  default: () => <header>Top bar</header>,
}));

vi.mock('./ObservatoryContextBanner', () => ({
  default: () => null,
}));

describe('ObservatoryFrame', () => {
  it('renders its evidence route without taking over a storefront chat surface', () => {
    render(
      <MemoryRouter initialEntries={['/observatory/proof-board']}>
        <Routes>
          <Route path="/observatory" element={<ObservatoryFrame />}>
            <Route path="proof-board" element={<div>Proof board</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText('Proof board')).toBeInTheDocument();
  });
});
