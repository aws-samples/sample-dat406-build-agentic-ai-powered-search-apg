/**
 * Markdown Message Renderer - Formats agent responses with markdown
 */

import { Children, cloneElement, isValidElement } from 'react'
import '../styles/editorial-streaming.css'

interface Props {
  content: string
  streaming?: boolean
}

const STREAMING_CARET = (
  <span
    key="editorial-streaming-caret"
    className="editorial-streaming-caret"
    data-testid="editorial-streaming-caret"
    aria-hidden="true"
  />
)

const appendStreamingCaret = (elements: JSX.Element[]) => {
  if (elements.length === 0) return elements

  const next = [...elements]
  const lastIndex = next.length - 1
  const last = next[lastIndex]

  if (last.type === 'ul') {
    const items = Children.toArray(last.props.children)
    const finalItemIndex = items.length - 1
    const finalItem = items[finalItemIndex]
    if (isValidElement(finalItem)) {
      items[finalItemIndex] = cloneElement(
        finalItem,
        {},
        finalItem.props.children,
        STREAMING_CARET,
      )
      next[lastIndex] = cloneElement(last, {}, items)
      return next
    }
  }

  next[lastIndex] = cloneElement(
    last,
    {},
    last.props.children,
    STREAMING_CARET,
  )
  return next
}

function stabilizeStreamingMarkdown(raw: string): string {
  return raw
    .split(/(```(?:\w+)?\s*\n?[\s\S]*?```)/g)
    .map((segment) => {
      if (segment.startsWith('```')) return segment
      const delimiterCount = segment.match(/\*\*/g)?.length ?? 0
      if (delimiterCount % 2 === 0) return segment
      const unmatchedIndex = segment.lastIndexOf('**')
      return (
        segment.slice(0, unmatchedIndex) +
        segment.slice(unmatchedIndex + 2)
      )
    })
    .join('')
}

const MarkdownMessage = ({ content, streaming = false }: Props) => {

  const formatText = (text: string) => {
    // Replace stars with gold colored stars
    const parts = text.split(/(\d+\.\d+★)/)
    return parts.map((part, i) => {
      if (part.match(/\d+\.\d+★/)) {
        return <span key={i} className="text-yellow-500 font-semibold">{part}</span>
      }
      // Handle inline bold
      const boldParts = part.split(/(\*\*.*?\*\*)/)
      return boldParts.map((bp, j) => {
        if (bp.startsWith('**') && bp.endsWith('**')) {
          return <strong key={`${i}-${j}`}>{bp.slice(2, -2)}</strong>
        }
        return <span key={`${i}-${j}`}>{bp}</span>
      })
    })
  }

  const renderContent = (raw: string) => {
    // Pre-clean: strip artifacts the backend should have removed
    const text = (streaming ? stabilizeStreamingMarkdown(raw) : raw)
      // Remove markdown table rows (| col | col |)
      .replace(/^\|.*$/gm, '')
      // Remove horizontal rules (---, ***, ___)
      .replace(/^[-*_]{3,}\s*$/gm, '')
      // Remove "Products:" / "Suggestions:" labels
      .replace(/^(?:Products?|Suggestions?):?\s*$/gim, '')
      // Collapse blank lines
      .replace(/\n{3,}/g, '\n\n')
      .trim()

    // Split on code fences, preserving the blocks
    const segments = text.split(/(```(?:\w+)?\s*\n?[\s\S]*?```)/g)
    const elements: JSX.Element[] = []
    let segKey = 0

    segments.forEach((segment) => {
      const fenceMatch = segment.match(/^```(?:\w+)?\s*\n?([\s\S]*?)```$/)
      if (fenceMatch) {
        const code = fenceMatch[1].trim()
        // If it's valid JSON, skip it (products are rendered separately via ProductCardCompact)
        try {
          JSON.parse(code)
          return // pure JSON block — products rendered as cards, not text
        } catch {
          // Not JSON — render as a styled code block
          elements.push(
            <pre key={`code-${segKey++}`} className="dl-code-block" style={{ margin: '12px 0' }}>
              {code}
            </pre>
          )
        }
      } else {
        // Regular text — parse lines
        const lines = segment.split('\n')
        let currentList: string[] = []
        let listKey = 0

        const flushList = () => {
          if (currentList.length > 0) {
            elements.push(
              <ul key={`list-${segKey}-${listKey++}`} className="list-disc list-inside space-y-1 my-2 ml-4">
                {currentList.map((item, idx) => (
                  <li key={idx} className="text-text-primary">{formatText(item)}</li>
                ))}
              </ul>
            )
            currentList = []
          }
        }

        lines.forEach((line, idx) => {
          // Bold text with emoji
          if (line.match(/^\*\*.*\*\*/)) {
            flushList()
            elements.push(
              <p key={`${segKey}-${idx}`} className="font-semibold text-text-primary my-2">
                {formatText(line)}
              </p>
            )
          }
          // List items (- or •)
          else if (line.match(/^[-•]\s/)) {
            const text = line.replace(/^[-•]\s*/, '')
            currentList.push(text)
          }
          // Regular paragraphs (skip empty/whitespace-only)
          else if (line.trim()) {
            flushList()
            elements.push(
              <p key={`${segKey}-${idx}`} className="text-text-primary my-2">
                {formatText(line)}
              </p>
            )
          }
          // Empty lines
          else {
            flushList()
          }
        })

        flushList()
        segKey++
      }
    })
    return streaming ? appendStreamingCaret(elements) : elements
  }

  return (
    <div
      className={`space-y-1 ${streaming ? 'editorial-streaming' : ''}`}
      aria-busy={streaming}
    >
      {renderContent(content)}
    </div>
  )
}

export default MarkdownMessage
