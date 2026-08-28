/**
 * Offline fallback for the three switchable hero personas.
 *
 * `membership` mirrors what scripts/migrations/018_client_book.sql writes to
 * pellier.customers, and pellier/backend/personas-config.json serves. The
 * three deliberately span all three rungs so the storefront on its own
 * demonstrates the whole ladder. A test asserts all three stay in agreement.
 */
export const LOCAL_PERSONAS = [
  {
    id: 'marco',
    display_name: 'Marco',
    role_tag: 'Returning',
    blurb:
      'Brooklyn-based, partial to natural fibers. Last visit, three weeks ago. Bought the oat Maren tunic.',
    avatar_color: '#5a3528',
    avatar_initial: 'M',
    customer_id: 'CUST-MARCO',
    membership: 'maison',
    stats: { visits: 11, orders: 7, last_seen_days: 21 },
  },
  {
    id: 'anna',
    display_name: 'Anna',
    role_tag: 'Gift-giver',
    blurb:
      'Buys for others - partner, mother, friends. Never for herself. Recent searches lean milestone.',
    avatar_color: '#6b3d2a',
    avatar_initial: 'A',
    customer_id: 'CUST-ANNA',
    membership: 'circle',
    stats: { visits: 6, orders: 5, last_seen_days: 9 },
  },
  {
    id: 'theo',
    display_name: 'Theo',
    role_tag: 'Home + slow craft',
    blurb:
      'Keeps a short list of quiet pieces - ceramics, linen throws, stoneware. Finishes what he buys, slowly.',
    avatar_color: '#5a4535',
    avatar_initial: 'T',
    customer_id: 'CUST-THEO',
    membership: 'registered',
    stats: { visits: 8, orders: 4, last_seen_days: 14 },
  },
] as const

