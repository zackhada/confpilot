import { LoaderCircle } from 'lucide-react'
import { MotionConfig } from 'motion/react'
import { useMemo, useState } from 'react'
import { nextProbeTerm, type ProbeAnswer, type ProbeAnswers } from '@/lib/frontier'
import { probe } from '@/room/api'
import { recordStatuses } from '@/room/knowledge'
import { useRoom } from '@/room/store'
import { TermSheet } from '@/shared/TermSheet'
import { ThemeToggle } from '@/shell/ThemeToggle'
import { CheckStep } from './CheckStep'
import { MapStep } from './MapStep'
import { probeCandidates, PROBE_QUESTIONS, probeStatuses } from './probeLogic'
import { TalkStep } from './TalkStep'

type Step = 'talk' | 'check' | 'map'

interface ProbeFlowProps {
  /** Called when the person finishes the map or skips; either way Live opens next. */
  onDone: () => void
}

/** "Tune it to me": say what you do, answer a short adaptive check, see your map. */
export function ProbeFlow({ onDone }: ProbeFlowProps) {
  const me = useRoom((s) => s.me)
  const termsById = useRoom((s) => s.terms)
  const knowledge = useRoom((s) => s.knowledge)
  const terms = useMemo(() => Object.values(termsById), [termsById])
  const [step, setStep] = useState<Step>('talk')
  const [busy, setBusy] = useState(false)
  const [note, setNote] = useState<string | null>(null)
  const [used, setUsed] = useState<string[]>([])
  const [answers, setAnswers] = useState<ProbeAnswers>({})

  const candidates = useMemo(() => probeCandidates(terms, used), [terms, used])
  const nextId = step === 'check' ? nextProbeTerm(candidates, answers, PROBE_QUESTIONS) : null
  const nextTerm = nextId ? termsById[nextId] : undefined

  const finishCheck = (finalAnswers: ProbeAnswers): void => {
    recordStatuses(probeStatuses(terms, used, finalAnswers), 'probe')
    setStep('map')
  }

  const readTalk = async (text: string): Promise<void> => {
    if (!text || !me) return setStep('check')
    setBusy(true)
    try {
      const result = await probe(me.name, me.user_id, text)
      setUsed(result.known_term_ids)
    } catch {
      // The LLM is a bonus; the check that follows works without it.
      setNote('Could not read that just now. The quick check still tunes your cards.')
    } finally {
      setBusy(false)
      setStep('check')
    }
  }

  const answer = (termId: string, value: ProbeAnswer): void => {
    const next = { ...answers, [termId]: value }
    setAnswers(next)
    if (nextProbeTerm(candidates, next, PROBE_QUESTIONS) === null) finishCheck(next)
  }

  return (
    <MotionConfig reducedMotion="user">
      <div className="pt-safe mx-auto flex h-dvh w-full max-w-xl flex-col bg-hall">
        <header className="flex min-h-13 items-center justify-between pr-1.5 pl-4">
          <p className="font-display text-lg">Tune it to me</p>
          <ThemeToggle />
        </header>
        <main className="flex min-h-0 flex-1 flex-col">
          {terms.length === 0 ? (
            <output className="px-safe flex items-center gap-2.5 pt-6 text-(length:--text-lead) text-ink-soft">
              <LoaderCircle className="size-5 animate-spin" aria-hidden="true" />
              Loading the glossary
            </output>
          ) : step === 'talk' ? (
            <TalkStep busy={busy} note={note} onContinue={(text) => void readTalk(text)} onSkip={onDone} />
          ) : step === 'check' && nextTerm ? (
            <CheckStep
              term={nextTerm}
              answered={Object.keys(answers).length}
              onAnswer={(value) => answer(nextTerm.id, value)}
              onSkip={onDone}
            />
          ) : (
            <MapStep terms={terms} knowledge={knowledge} onDone={onDone} />
          )}
        </main>
        <TermSheet />
      </div>
    </MotionConfig>
  )
}
