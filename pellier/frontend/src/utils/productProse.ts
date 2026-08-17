interface ProductMention {
  name?: string | null
}

interface EmphasisOptions {
  includePrices?: boolean
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

export function emphasizeProductMentions(
  content: string,
  products: readonly ProductMention[],
  options: EmphasisOptions = {},
): string {
  const names = Array.from(
    new Set(
      products
        .map((product) => product.name?.trim())
        .filter((name): name is string => !!name),
    ),
  ).sort((a, b) => b.length - a.length)

  if (names.length === 0) return content

  // Leave existing markdown bold spans and code fences untouched.
  return content
    .split(/(```[\s\S]*?```|\*\*.*?\*\*)/g)
    .map((segment) => {
      if (segment.startsWith('```') || segment.startsWith('**')) return segment
      const emphasized = names.reduce((text, name) => {
        const pattern = new RegExp(`(${escapeRegExp(name)})`, 'gi')
        return text.replace(pattern, '**$1**')
      }, segment)
      return options.includePrices
        ? emphasized.replace(/(\$\d+(?:,\d{3})*(?:\.\d{2})?)/g, '**$1**')
        : emphasized
    })
    .join('')
}
