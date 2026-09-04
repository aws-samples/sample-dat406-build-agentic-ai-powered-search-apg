/**
 * The micro-eval card puts two rerank pools side by side.
 *
 * Two properties matter beyond the layout. Every caption has to describe what
 * the backend actually computes, because a caption is the only thing that
 * tells a participant how to read the number next to it. And the run has to
 * be asked for: one visit executes two pools times the repetition count of
 * live retrieval plus a Cohere Rerank call each, so a card that fires on
 * mount bills every participant who scrolls past it.
 */
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import MicroEvalCard from './MicroEvalCard';

const PAYLOAD = {
  query: 'A housewarming gift under $100 that is currently in stock.',
  limit: 5,
  repetitions: 3,
  variants: [
    {
      pool_k: 20,
      candidate_coverage: 0.94,
      context_precision: 0.8,
      mrr: 1.0,
      hard_constraint_violations: 0,
      short_result_rate: 0.0,
      citation_coverage: 1.0,
      latency_ms_p50: 812,
      latency_ms_p95: 963,
    },
    {
      pool_k: 3,
      candidate_coverage: 0.41,
      context_precision: 0.6,
      mrr: 0.5,
      hard_constraint_violations: 2,
      short_result_rate: 1.0,
      citation_coverage: 0.7,
      latency_ms_p50: 512,
      latency_ms_p95: 604,
    },
  ],
};

function stubFetch(response: () => Response) {
  const fetchMock = vi.fn(async () => response());
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

async function runCard() {
  const user = userEvent.setup();
  render(<MicroEvalCard />);
  await user.click(screen.getByRole('button', { name: /run both pools/i }));
  return user;
}

function row(table: HTMLElement, name: RegExp) {
  return within(table).getByRole('row', { name });
}

describe('MicroEvalCard', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('runs nothing until the participant asks for it', () => {
    const fetchMock = stubFetch(
      () => new Response(JSON.stringify(PAYLOAD), { status: 200 }),
    );
    render(<MicroEvalCard />);

    expect(fetchMock).not.toHaveBeenCalled();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /run both pools/i }),
    ).toBeEnabled();
  });

  it('renders both pools side by side with the same metrics', async () => {
    stubFetch(() => new Response(JSON.stringify(PAYLOAD), { status: 200 }));
    await runCard();

    const table = await screen.findByRole('table', {
      name: /rerank pool comparison/i,
    });
    const headers = within(table)
      .getAllByRole('columnheader')
      .map((cell) => cell.textContent);
    expect(headers).toEqual(['Metric', 'pool_k 20', 'pool_k 3']);

    const coverage = row(table, /candidate coverage/i).querySelectorAll('td');
    expect(coverage[0]).toHaveTextContent('94%');
    expect(coverage[1]).toHaveTextContent('41%');

    const violations = row(
      table,
      /hard-constraint violations/i,
    ).querySelectorAll('td');
    expect(violations[0]).toHaveTextContent('0');
    expect(violations[1]).toHaveTextContent('2');
  });

  it('states the canonical query and the repetition count the run reported', async () => {
    stubFetch(() => new Response(JSON.stringify(PAYLOAD), { status: 200 }));
    await runCard();

    expect(
      await screen.findByText(
        /A housewarming gift under \$100 that is currently in stock\./,
      ),
    ).toBeInTheDocument();
    // Read off the response, never assumed: the endpoint owns the count.
    expect(screen.getByText(/3 repetitions/i)).toBeInTheDocument();
  });

  it('describes candidate coverage as reach into the rerank pool', async () => {
    stubFetch(() => new Response(JSON.stringify(PAYLOAD), { status: 200 }));
    await runCard();

    const table = await screen.findByRole('table', {
      name: /rerank pool comparison/i,
    });
    const caption = row(table, /candidate coverage/i).textContent ?? '';
    expect(caption).toMatch(/rerank pool/i);
    // The backend divides golden ids found in the pool by golden ids. It
    // never counts eligible catalog rows.
    expect(caption).not.toMatch(/catalog/i);
  });

  it('names only the constraints the backend checks', async () => {
    stubFetch(() => new Response(JSON.stringify(PAYLOAD), { status: 200 }));
    await runCard();

    const table = await screen.findByRole('table', {
      name: /rerank pool comparison/i,
    });
    const caption = row(table, /hard-constraint violations/i).textContent ?? '';
    expect(caption).toMatch(/price/i);
    expect(caption).toMatch(/stock/i);
    // `_breaks_price_or_stock` reads the price ceiling and the stock flag.
    // Category is a retrieval filter, not one of these violations.
    expect(caption).not.toMatch(/category/i);
  });

  it('renders MRR as a reciprocal rank, not a rate', async () => {
    stubFetch(() => new Response(JSON.stringify(PAYLOAD), { status: 200 }));
    await runCard();

    const table = await screen.findByRole('table', {
      name: /rerank pool comparison/i,
    });
    const cells = row(table, /reciprocal rank/i).querySelectorAll('td');
    // 1.0 is "first position", 0.50 is "second". Neither is a percentage.
    expect(cells[0]).toHaveTextContent('1.00');
    expect(cells[1]).toHaveTextContent('0.50');
    expect(cells[0]).not.toHaveTextContent('%');
    expect(cells[1]).not.toHaveTextContent('%');
  });

  it('renders the short-result observation as the yes/no it is', async () => {
    stubFetch(() => new Response(JSON.stringify(PAYLOAD), { status: 200 }));
    await runCard();

    const table = await screen.findByRole('table', {
      name: /rerank pool comparison/i,
    });
    // One deterministic pass per pool: `float(len(returned) < limit)`. A
    // percentage over a single observation invites a frequency reading.
    const cells = row(table, /short result/i).querySelectorAll('td');
    expect(cells[0]).toHaveTextContent('No');
    expect(cells[1]).toHaveTextContent('Yes');
  });

  it('reads out what the smaller pool costs in one line', async () => {
    stubFetch(() => new Response(JSON.stringify(PAYLOAD), { status: 200 }));
    await runCard();

    expect(await screen.findByTestId('micro-eval-reading')).toHaveTextContent(
      /53 points of candidate coverage/,
    );
  });

  it('names the endpoint as unavailable rather than drawing an empty table', async () => {
    stubFetch(() => new Response('', { status: 404 }));
    await runCard();

    await waitFor(() =>
      expect(screen.getByTestId('micro-eval-unavailable')).toBeInTheDocument(),
    );
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });
});
