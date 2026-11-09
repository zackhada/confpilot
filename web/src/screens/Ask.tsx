import { EmptyState } from './EmptyState'

const EXAMPLES: readonly { text: string; lang: string }[] = [
  { text: 'What did Zack say about RAG?', lang: 'en' },
  { text: 'Where did they explain BM25?', lang: 'en' },
  { text: '¿Qué dijeron sobre la búsqueda híbrida?', lang: 'es' },
]

/** Placeholder for the search slice: shows the kind of question it will answer. */
export function Ask() {
  return (
    <EmptyState
      screen="Ask"
      title="Ask about anything you heard."
      hint="Search opens once the room has a few minutes of conversation saved."
    >
      <p className="pb-3 text-(length:--text-note) font-semibold text-ink-soft">Questions it will answer</p>
      <ul className="border-t border-rule">
        {EXAMPLES.map((example) => (
          <li key={example.text} lang={example.lang} className="border-b border-rule py-3.5 text-(length:--text-lead)">
            {example.text}
          </li>
        ))}
      </ul>
      <p className="max-w-[30ch] pt-4 text-ink-soft">
        Ask in your own language. The answer jumps to the moment it was said.
      </p>
    </EmptyState>
  )
}
