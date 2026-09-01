interface CatalogPromptProduct {
  name: string
  price: number
  category?: string
}

export interface CatalogPromptAction {
  label: string
  prompt: string
}

export function isArchiveVariant(product: CatalogPromptProduct): boolean {
  return /archive|garment\s+\d+/i.test(product.name)
}

function descriptor(product: CatalogPromptProduct): string {
  const text = `${product.name} ${product.category ?? ''}`.toLowerCase()
  if (text.includes('linen')) return 'linen'
  if (/ceramic|stoneware/.test(text)) return 'ceramic'
  if (text.includes('candle')) return 'candle'
  return (product.category || 'catalog').toLowerCase()
}

export function productQuickActions(
  product: CatalogPromptProduct,
): CatalogPromptAction[] {
  const name = product.name.trim() || 'this piece'
  const price = Math.max(1, Math.round(product.price))

  if (isArchiveVariant(product)) {
    const kind = descriptor(product)
    return [
      {
        label: 'Workshop alternatives',
        prompt: `Show named, non-archive ${kind} pieces from the workshop edit near $${price}.`,
      },
      {
        label: 'Build the edit',
        prompt:
          'Build this edit from named workshop products instead of archive variants.',
      },
      {
        label: 'Compare named pieces',
        prompt:
          'Compare the two strongest named, non-archive matches in the workshop edit.',
      },
    ]
  }

  return [
    {
      label: 'Build around it',
      prompt: `What current-catalog pieces pair well with ${name}?`,
    },
    {
      label: 'Similar pieces',
      prompt: `Show current-catalog alternatives to ${name} near $${price}.`,
    },
  ]
}

export function catalogTurnFollowUps(
  products: CatalogPromptProduct[],
  fallback: string[],
): string[] {
  const named = products.filter(product => !isArchiveVariant(product))

  if (named.length >= 2) {
    const [first, second] = named
    return [
      `Compare ${first.name} and ${second.name}.`,
      `What current-catalog pieces pair well with ${first.name}?`,
    ]
  }

  if (named.length === 1) {
    return productQuickActions(named[0]).map(action => action.prompt)
  }

  if (products.length > 0) {
    return productQuickActions(products[0]).map(action => action.prompt)
  }

  return fallback.slice(0, 3)
}
