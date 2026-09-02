/**
 * Pellier Observatory — Skill type
 *
 * Represents one of the 5 skills loaded by the SkillRouter
 * per turn. Mirrors the YAML + Markdown structure of the live
 * `/skills/<name>/SKILL.md` files.
 */

/**
 * Fields marked optional are NOT owned by the live registry.
 * `GET /api/observatory/skills` reads SKILL.md frontmatter, which carries
 * `name`, `display_name`, `description`, `version` and `persona` — nothing
 * else. `loadedBy`, `signals` and `status` are curated presentation fields
 * that only exist in the bundled fixture. They were typed as required, so
 * every consumer assumed them present and `signals.map` threw against live
 * data. Treat an absent value as "not known", never as empty.
 */
export interface Skill {
  /** kebab-case slug from SKILL.md frontmatter `name`. */
  name: string;
  /** Human-readable title for the card. */
  displayName: string;
  /** Persona id or shared overlay that triggers this skill. */
  persona: 'marco' | 'anna' | 'theo' | 'shared';
  /** Display name of the persona/scope (for the card chip). */
  personaDisplayName: string;
  /** One-line description from SKILL.md frontmatter. */
  description: string;
  /** Semver-lite from SKILL.md frontmatter. */
  version: string;
  /** Markdown body preview — the guidance the model receives. */
  body: string;
  /** Specialist agents that load this skill. Fixture-only. */
  loadedBy?: string[];
  /** Signal keywords the SkillRouter watches for. Fixture-only. */
  signals?: string[];
  /** Live (loaded) vs stubbed. Fixture-only. */
  status?: 'live' | 'stub';
}

/** Raw shape of one item from `GET /api/observatory/skills`. */
export interface SkillApiRow {
  name: string;
  display_name?: string;
  description?: string;
  version?: string;
  persona?: string;
  token_estimate?: number;
  body?: string;
  path?: string;
  /** Present only when the response came from the bundled fixture. */
  loadedBy?: string[];
  signals?: string[];
  status?: 'live' | 'stub';
  displayName?: string;
  personaDisplayName?: string;
}

const PERSONA_LABEL: Record<string, string> = {
  marco: 'Marco',
  anna: 'Anna',
  theo: 'Theo',
  shared: 'Shared',
};

/**
 * Normalize the registry's snake_case payload onto the camelCase `Skill` the
 * surfaces consume. Without this every card read `undefined` for its title and
 * every persona filter matched nothing, because the API and the type had
 * diverged with no adapter between them.
 */
export function toSkill(row: SkillApiRow): Skill {
  const persona = (row.persona ?? 'shared') as Skill['persona'];
  return {
    name: row.name,
    displayName: row.displayName ?? row.display_name ?? row.name,
    persona,
    personaDisplayName:
      row.personaDisplayName ?? PERSONA_LABEL[persona] ?? 'Shared',
    description: row.description ?? '',
    version: row.version ?? '',
    body: row.body ?? '',
    loadedBy: row.loadedBy,
    signals: row.signals,
    status: row.status,
  };
}
