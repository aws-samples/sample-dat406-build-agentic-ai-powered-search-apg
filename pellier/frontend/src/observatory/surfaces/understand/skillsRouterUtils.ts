/** SkillRouter query presets for the live demonstration. */
import type { Skill } from '../../types';

export function routerQueryForSkill(skill: Skill): string {
  const presets: Record<string, string> = {
    'the-packing-list': 'what would go with the Hadley shirt for Goa',
    'the-gift-table': 'wrap-ready gifts with no extra effort',
    'the-makers-shelf': 'hand-thrown ceramics for a slower morning',
    'the-care-card': 'the bowl arrived damaged, what now?',
    'the-proof-counter': 'how do you know this fits my taste?',
  };
  return presets[skill.name] ?? skill.signals[0] ?? skill.description;
}
