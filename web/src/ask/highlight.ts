export interface HighlightPart {
  text: string
  marked: boolean
}

const ENTITIES: Readonly<Record<string, string>> = {
  '&amp;': '&',
  '&lt;': '<',
  '&gt;': '>',
  '&quot;': '"',
  '&#39;': "'",
  '&#x27;': "'",
}

function decode(escaped: string): string {
  return escaped.replace(/&(?:amp|lt|gt|quot|#39|#x27);/g, (entity) => ENTITIES[entity] ?? entity)
}

/**
 * The search API returns `highlight` as escaped text with <mark> around the matches. This
 * turns it into plain parts that React renders as text, so no HTML from the server is ever
 * injected into the page. Anything that is not a <mark> tag stays visible as literal text.
 */
export function parseHighlight(highlight: string): HighlightPart[] {
  const parts: HighlightPart[] = []
  let marked = false
  for (const piece of highlight.split(/(<mark>|<\/mark>)/)) {
    if (piece === '<mark>') marked = true
    else if (piece === '</mark>') marked = false
    else if (piece !== '') parts.push({ text: decode(piece), marked })
  }
  return parts
}

/** "just now", "4 min ago", "2 h ago": how long ago a moment was spoken. */
export function timeAgo(spokenAt: number, now: number): string {
  const minutes = Math.floor(Math.max(0, now - spokenAt) / 60_000)
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes} min ago`
  const hours = Math.floor(minutes / 60)
  return hours < 24 ? `${hours} h ago` : `${Math.floor(hours / 24)} d ago`
}
