import type { KnowledgeStatus, Lang, Term } from '@contracts'

export type PersonaId = 'clayton' | 'zack' | 'ana'

export interface Persona {
  id: PersonaId
  name: string
  /** One line shown on the join screen. */
  knows: string
  /** Glossary categories this persona already knows. */
  knownCategories: readonly string[]
  lang: Lang | null
}

// Categories any working engineer already has: general tech, business talk, idioms.
const EVERYDAY = ['tech', 'business', 'conference', 'idiom'] as const

// Category names cover both content/glossary.json and the older sample fixture.
// Demo personas from the plan. Ana is fictional: a frontend developer at her first KubeCon.
export const PERSONAS: readonly Persona[] = [
  {
    id: 'clayton',
    name: 'Clayton',
    knows: 'Infrastructure. Knows SRE and Kubernetes terms.',
    knownCategories: [...EVERYDAY, 'ops', 'cloud', 'operations', 'cloud-native'],
    lang: null,
  },
  {
    id: 'zack',
    name: 'Zack',
    knows: 'Search. Knows search and AI terms.',
    knownCategories: [...EVERYDAY, 'data', 'ai', 'search'],
    lang: null,
  },
  {
    id: 'ana',
    name: 'Ana',
    knows: 'New here. Every term gets a card.',
    knownCategories: [],
    lang: 'pt',
  },
]

export const LANGUAGES: readonly { code: Lang; label: string }[] = [
  { code: 'es', label: 'Español' },
  { code: 'pt', label: 'Português' },
  { code: 'zh', label: '中文' },
  { code: 'hi', label: 'हिन्दी' },
]

export function personaById(id: PersonaId): Persona {
  return PERSONAS.find((p) => p.id === id) ?? PERSONAS[2]!
}

export function isPersonaId(value: unknown): value is PersonaId {
  return PERSONAS.some((p) => p.id === value)
}

export function isLang(value: unknown): value is Lang {
  return LANGUAGES.some((l) => l.code === value)
}

/** The terms a persona starts out knowing, by glossary category. */
export function seedKnowledge(
  persona: Persona,
  terms: readonly Term[],
): Record<string, KnowledgeStatus> {
  const known = new Set(persona.knownCategories)
  return Object.fromEntries(
    terms.filter((term) => known.has(term.category)).map((term) => [term.id, 'known' as const]),
  )
}
