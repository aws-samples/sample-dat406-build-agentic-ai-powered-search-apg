/**
 * Agent Trace Observatory — Memory types
 *
 * The Memory architecture lens has four substrates, each with its
 * own storage, lifetime, and write contract:
 *
 *   working    — AgentCore Memory session turns
 *   semantic   — AgentCore Memory records extracted by a USER_PREFERENCE strategy
 *   episodic   — Aurora customer_episodic_seed / orders / returns
 *   procedural — Aurora tool_audit aggregate patterns
 *
 * Each substrate carries an explicit ``source`` so the UI can show
 * provenance honestly. The governed workshop memory surface does not use
 * static memory data; semantic memory can be in a settling state while
 * AgentCore USER_PREFERENCE extraction has not produced records yet.
 */

export type MemorySubstrate = 'working' | 'semantic' | 'episodic' | 'procedural';

/**
 * Provenance of the items in a substrate panel.
 *
 *   live     - read from the real source on this request
 *   settling - read succeeded, but async extraction has not produced records
 */
export type MemorySource = 'live' | 'settling';

export interface MemoryItem {
  id: string;
  content: string;
  substrate: MemorySubstrate;
  /** ISO timestamp for working-memory turns; absent for the others. */
  timestamp?: string;
  /** Cosine similarity 0..1 when the item came from a vector recall. */
  similarity?: number;
  /** Days into the past for episodic seed rows (negative or zero). */
  tsOffsetDays?: number;
}

export interface MemorySubstratePanel {
  /** Display label (e.g. "Working · AgentCore Memory"). */
  label: string;
  /** Backing store name shown as a small caption. */
  store: string;
  /** Where these items came from on this request. */
  source: MemorySource;
  /** Items to render. May be empty (cold start, fresh persona, etc.). */
  items: MemoryItem[];
/** Optional one-line caption shown when a live source is empty or warming. */
  caveat?: string;
}

export interface MemoryState {
  persona: string;
  working: MemorySubstratePanel;
  semantic: MemorySubstratePanel;
  episodic: MemorySubstratePanel;
  procedural: MemorySubstratePanel;
}
