/**
 * Pellier Labs Observatory — Skill type
 *
 * Represents one of the 5 skills loaded by the SkillRouter
 * per turn. Mirrors the YAML + Markdown structure of the live
 * `/skills/<name>/SKILL.md` files.
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
  /** Specialist agents that load this skill. */
  loadedBy: string[];
  /** Markdown body preview — the guidance the model receives. */
  body: string;
  /** Signal keywords the SkillRouter watches for. */
  signals: string[];
  /** Live (loaded) vs stubbed (not yet wired). All 5 skills are live in the workshop default. */
  status: 'live' | 'stub';
}
