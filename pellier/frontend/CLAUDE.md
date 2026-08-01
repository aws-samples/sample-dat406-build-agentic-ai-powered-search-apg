# Pellier frontend guidance

This directory owns the React/Vite Boutique and Atelier experiences.
Read the repository `CLAUDE.md` and `VOICE.md` before editing.

## Product boundaries

- Boutique is a fast, editorial shopping experience.
- Atelier is a quiet operator console organized around Core Labs 1-4.
- Code Editor, curl, and SQL remain the canonical proof surfaces.
- Atelier may summarize live evidence but must not invent or replace proof.
- Do not reintroduce the old Act I/II/III navigation.

## Interaction rules

- Preserve real SSE streaming. Do not simulate completion with a spinner or a
  client-only timeout.
- Keep thinking concise and answer quickly. Editorial typewriter treatment
  applies to answer text, not long internal narration.
- Keep catalog follow-ups grounded in returned products and actual variants.
- Use distinct visual states for policy denial, authentication setup,
  backend unavailability, and invalid requests.
- Human handoff is an explicit outcome, not a fallback for an ordinary
  partial catalog match.
- Use the existing icon library and design tokens.
- Keep SQL, code, IDs, and telemetry in JetBrains Mono; use the Atelier
  sans/display typography for labels and prose.
- Keep proof data backend-driven. Browser state is not evidence.

## Responsive and accessibility rules

- Check desktop and workshop-width layouts.
- Prevent overlapping controls, clipped labels, and unexpected layout shifts.
- Give icon-only controls accessible names and tooltips.
- Preserve visible focus states and semantic headings.
- Do not encode status by color alone.

## Frontend validation

From `pellier/frontend`:

```bash
npm test -- --run
npm run type-check
npm run lint
npm run build
npm audit --omit=dev --audit-level=high
```

For user-facing workflow changes, verify the live route in Chrome at both a
desktop viewport and a narrower workshop viewport. Check the console for
errors and confirm the referenced backend evidence is present.
