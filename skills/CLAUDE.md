# Pellier runtime skill guidance

Files under this directory are runtime prompt overlays for Pellier's Strands
specialists. They are not Claude Code skills.

Claude Code project skills live under:

```text
.claude/skills/<skill-name>/SKILL.md
```

Pellier runtime skills live under:

```text
skills/<skill-name>/SKILL.md
```

## Runtime skill contract

- `name` is the stable machine identifier.
- `description` is the router activation contract. The routing model decides
  whether to load the skill from this field alone.
- `persona`, `display_name`, and `version` are Pellier-specific metadata.
- The Markdown body is injected into a specialist system prompt only when the
  router selects the skill.

## Editing rules

- Read `../VOICE.md` first.
- Keep the activation description specific enough to avoid over-triggering.
- Make the body concise, imperative, and additive to the base prompt.
- Do not put product facts, prices, inventory, policy decisions, or customer
  history in a skill unless the runtime will retrieve and verify them.
- Label examples as conditional and require the item to be present in tool
  results.
- Never grant a tool or authorization capability through prose.
- Keep care, proof, and handoff claims tied to tool results.
- Avoid copying the same rule into multiple skills. Put shared voice rules in
  `VOICE.md` and shared runtime behavior in the appropriate base prompt.

After editing, restart the backend so the boot-time registry reloads, then
run the skill/router tests and replay the relevant Boutique turn.
