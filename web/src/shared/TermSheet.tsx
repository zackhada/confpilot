import { X } from 'lucide-react'
import { m } from 'motion/react'
import { Dialog } from 'radix-ui'
import { Button } from '@/components/ui/button'
import { TermCard } from '@/live/TermCard'
import { markKnown, toggleSave } from '@/room/session'
import { useRoom } from '@/room/store'
import { useTermSheet } from './useTermSheet'

/** Bottom sheet with one term's card. Mounted once, in the app shell. */
export function TermSheet() {
  const termId = useTermSheet((s) => s.termId)
  const close = useTermSheet((s) => s.close)
  const terms = useRoom((s) => s.terms)
  const knowledge = useRoom((s) => s.knowledge)
  const lang = useRoom((s) => s.lang)
  const saved = useRoom((s) => (termId ? s.saved.includes(termId) : false))
  const term = termId ? terms[termId] : undefined

  return (
    <Dialog.Root open={termId !== null} onOpenChange={(open) => !open && close()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/60" />
        <Dialog.Content
          aria-describedby={undefined}
          className="pb-safe fixed inset-x-0 bottom-0 z-50 mx-auto w-full max-w-xl px-3 outline-none"
        >
          <Dialog.Title className="sr-only">{term?.term ?? 'Term'}</Dialog.Title>
          <m.div
            initial={{ y: 36, opacity: 0.9 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ type: 'spring', stiffness: 520, damping: 40, mass: 0.7 }}
            className="pb-3"
          >
            <div className="flex justify-end pb-2">
              <Dialog.Close asChild>
                <Button size="icon" aria-label="Close">
                  <X aria-hidden="true" />
                </Button>
              </Dialog.Close>
            </div>
            {termId && (
              <TermCard
                card={{ card_id: `sheet-${termId}`, term_id: termId, tier: 1 }}
                latencyMs={null}
                term={term}
                lit
                lang={lang}
                terms={terms}
                knowledge={knowledge}
                saved={saved}
                onKnow={() => {
                  markKnown(termId)
                  close()
                }}
                onSave={() => toggleSave(termId)}
              />
            )}
          </m.div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
