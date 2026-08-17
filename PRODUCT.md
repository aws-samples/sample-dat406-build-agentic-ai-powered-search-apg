# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Workshop participants and presenters use Pellier Labs to inspect how a guided
shopper request becomes a grounded storefront answer.

## Product Purpose

Pellier Labs makes one live agent turn legible from input through routing,
memory, tools, SQL, products, and final answer. Success means a participant can
connect each material answer claim to evidence emitted by the real run.

## Positioning

The workbench pairs the shopper-facing result with its live execution lineage
and receipts in one synchronized view.

## Operating Context

The primary experience is a guided demo. A participant selects one of the
canonical storefront turns, watches the live SSE stream, and compares the
evidence ledger with the grounded answer without leaving the first workbench.

## Capabilities and Constraints

- Canonical persona requests are shared with the Pellier storefront.
- Runs use the live `/api/chat/stream` SSE contract.
- The surface must distinguish emitted evidence from pending or unavailable
  layers.
- Response mode, profile context, safety inspection, trace visibility, retry,
  loading, empty, and error states remain functional.
- The primary desktop composition is three persistent panels with internal
  scrolling and minimal page scrolling.
- Main and governed are separate workshop products. This redesign applies to
  `main` only.

## Brand Commitments

Pellier Labs keeps the storefront typography, Pellier name and mark, the
maroon-orange identity, real product photography, and quiet professional
controls. The requested visual reference is the supplied Evidence Ledger and
Editorial Trace Studio imagery: a warm translucent paper workbench with a
photo-led turn library, chronological evidence ledger, and prominent grounded
answer.

## Evidence on Hand

- Canonical turns and preview products in
  `pellier/frontend/src/data/personaCurations.ts`
- Live stream handling in
  `pellier/frontend/src/agent-trace/surfaces/observe/PellierLabsWorkbench.tsx`
- Product assets in `pellier/frontend/public/products/`
- User-provided reference HTML and PNG files on the Desktop

## Product Principles

- Guided demo first.
- Show the answer and its proof together.
- Never present pending or absent data as evidence.
- Keep the primary turn inspectable without page-level scrolling.
- Prefer real controls and real product context over decorative chrome.

## Accessibility & Inclusion

Preserve semantic headings, keyboard-operable controls, visible focus states,
reduced-motion behavior, text alternatives, and readable contrast.
