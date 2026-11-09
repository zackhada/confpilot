import type { Term } from '@contracts'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { TermCard, type TermCardProps } from './TermCard'

const keyword: Term = {
  id: 'keyword-search',
  term: 'keyword search',
  aliases: [],
  say: null,
  category: 'data',
  level: 3,
  simple_def: 'Finding documents that contain the exact words you typed.',
  prereqs: [],
  source: 'seed',
}
const bm25: Term = {
  id: 'bm25',
  term: 'BM25',
  aliases: [],
  say: 'bee-em-twenty-FIVE',
  category: 'data',
  level: 4,
  simple_def: 'A formula that scores how well a document matches your words.',
  prereqs: ['keyword-search'],
  translations: { es: 'Fórmula que puntúa cuánto coincide un documento con tus palabras.' },
  source: 'seed',
}

function renderCard(overrides: Partial<TermCardProps> = {}) {
  const props: TermCardProps = {
    card: { card_id: 'utt-1:bm25', term_id: 'bm25', tier: 1 },
    latencyMs: 312,
    term: bm25,
    lit: true,
    lang: 'es',
    terms: { bm25, 'keyword-search': keyword },
    knowledge: {},
    onOpen: vi.fn(),
    onKnow: vi.fn(),
    onSave: vi.fn(),
    ...overrides,
  }
  render(<TermCard {...props} />)
  return props
}

describe('TermCard (lit)', () => {
  it('shows the term, definition, pronunciation, native line and latency', () => {
    renderCard()
    expect(screen.getByRole('heading', { name: 'BM25' })).toBeInTheDocument()
    expect(screen.getByText(bm25.simple_def)).toBeInTheDocument()
    expect(screen.getByText('bee-em-twenty-FIVE')).toBeInTheDocument()
    expect(screen.getByText(/Fórmula que puntúa/)).toHaveAttribute('lang', 'es')
    expect(screen.getByText('Shown 312 milliseconds after the word was spoken')).toBeInTheDocument()
  })

  it('hides the pronunciation row when the glossary has none', () => {
    renderCard({ term: { ...bm25, say: null } })
    expect(screen.queryByText(/^say/)).not.toBeInTheDocument()
  })

  it('hides the native line when there is no translation for the chosen language', () => {
    renderCard({ term: { ...bm25, translations: {} } })
    expect(screen.queryByText(/Fórmula/)).not.toBeInTheDocument()
  })

  it('says in words whether a prerequisite is known, not only by colour', () => {
    renderCard({ knowledge: { 'keyword-search': 'known' } })
    expect(screen.getByText(', which you know')).toBeInTheDocument()
  })

  it('calls back for I know this and Save', async () => {
    const user = userEvent.setup()
    const props = renderCard()
    await user.click(screen.getByRole('button', { name: 'I know this' }))
    await user.click(screen.getByRole('button', { name: 'Save' }))
    expect(props.onKnow).toHaveBeenCalledOnce()
    expect(props.onSave).toHaveBeenCalledOnce()
  })

  it('marks a slow card in words', () => {
    renderCard({ latencyMs: 1240 })
    expect(screen.getByText(/slower than the target/)).toBeInTheDocument()
  })
})

describe('TermCard (settled)', () => {
  it('keeps named controls and opens on tap', async () => {
    const user = userEvent.setup()
    const props = renderCard({ lit: false })
    expect(screen.getByRole('button', { name: 'I know BM25' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Save BM25' })).toHaveAttribute('aria-pressed', 'false')
    await user.click(screen.getByRole('button', { name: 'Open the BM25 card' }))
    expect(props.onOpen).toHaveBeenCalledOnce()
  })

  it('is read-only on the stage view', () => {
    renderCard({ lit: false, onKnow: undefined, onSave: undefined, onOpen: undefined })
    expect(screen.queryByRole('button', { name: 'I know BM25' })).not.toBeInTheDocument()
  })
})
