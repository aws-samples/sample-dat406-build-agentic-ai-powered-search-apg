import { describe, expect, it } from 'vitest'
import {
  catalogTurnFollowUps,
  productQuickActions,
} from './catalogFollowUps'

describe('catalog follow-ups', () => {
  it('never invents a colorway for a named catalog product', () => {
    const actions = productQuickActions({
      name: 'Italian Linen Camp Shirt',
      category: 'Apparel',
      price: 228,
    })

    expect(actions.map(action => action.label)).toEqual([
      'Build around it',
      'Similar pieces',
      'Check stock',
    ])
    expect(actions.map(action => action.prompt).join(' ')).not.toMatch(
      /another (?:size|color)|colorway/i,
    )
  })

  it('steers archive variants back to named workshop products', () => {
    const actions = productQuickActions({
      name: 'Pellier Archive Garment 138 - Gift Edit in Oat',
      category: 'Apparel',
      price: 71.23,
    })
    const prompts = actions.map(action => action.prompt).join(' ')

    expect(prompts).toContain('non-archive apparel pieces')
    expect(prompts).toContain('named workshop products')
    expect(prompts).not.toMatch(/another (?:size|color)|colorway/i)
  })

  it('builds turn follow-ups from products actually returned', () => {
    const prompts = catalogTurnFollowUps(
      [
        { name: 'Hadley Linen Shirt', price: 248 },
        { name: 'Oat Linen Drawstring Trousers', price: 178 },
      ],
      ['Static fallback'],
    )

    expect(prompts[0]).toBe(
      'Compare Hadley Linen Shirt and Oat Linen Drawstring Trousers.',
    )
    expect(prompts.join(' ')).not.toContain('Static fallback')
  })
})
