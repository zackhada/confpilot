import type { Glossary, Term } from '@contracts'
import { readStoredJson, writeStored } from '@/shared/storage'

const CACHE_KEY = 'confpilot.glossary'

function isTerm(value: unknown): value is Term {
  if (typeof value !== 'object' || value === null) return false
  const v = value as Record<string, unknown>
  return (
    typeof v.id === 'string' &&
    typeof v.term === 'string' &&
    typeof v.simple_def === 'string' &&
    (typeof v.say === 'string' || v.say === null) &&
    typeof v.category === 'string' &&
    Array.isArray(v.aliases) &&
    Array.isArray(v.prereqs)
  )
}

export function isGlossary(value: unknown): value is Glossary {
  if (typeof value !== 'object' || value === null) return false
  const v = value as Record<string, unknown>
  return typeof v.version === 'string' && Array.isArray(v.terms) && v.terms.every(isTerm)
}

/** The glossary saved on this phone from an earlier visit, if any. */
export function cachedGlossary(): Glossary | null {
  return readStoredJson(CACHE_KEY, isGlossary)
}

/**
 * Fetch the glossary and keep a copy on the phone, so lookups need no network. When the
 * request fails, the saved copy is used; with no saved copy the error is thrown.
 */
export async function loadGlossary(fetchImpl: typeof fetch = fetch): Promise<Glossary> {
  try {
    const response = await fetchImpl('/api/glossary')
    if (!response.ok) throw new Error(`The glossary request failed (${response.status}).`)
    const body: unknown = await response.json()
    if (!isGlossary(body)) throw new Error('The glossary response had an unexpected shape.')
    if (cachedGlossary()?.version !== body.version) writeStored(CACHE_KEY, JSON.stringify(body))
    return body
  } catch (error) {
    const cached = cachedGlossary()
    if (cached) return cached
    throw error instanceof Error ? error : new Error('The glossary could not be loaded.')
  }
}

export function indexTerms(terms: readonly Term[]): Record<string, Term> {
  return Object.fromEntries(terms.map((term) => [term.id, term]))
}
