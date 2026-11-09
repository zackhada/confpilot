import type { Term } from '@contracts'
import { Check, Ear, Sparkles } from 'lucide-react'
import type { ComponentType } from 'react'
import { Button } from '@/components/ui/button'
import type { ProbeAnswer } from '@/lib/frontier'
import { PROBE_QUESTIONS } from './probeLogic'

const ANSWERS: { answer: ProbeAnswer; label: string; Icon: ComponentType<{ className?: string; 'aria-hidden'?: 'true' }>; tone: string }[] = [
  { answer: 'explain', label: 'I could explain it', Icon: Check, tone: 'text-known' },
  { answer: 'heard', label: 'I’ve heard it', Icon: Ear, tone: 'text-beyond' },
  { answer: 'new', label: 'New to me', Icon: Sparkles, tone: 'text-fresh' },
]

interface CheckStepProps {
  term: Term
  /** How many questions were answered before this one. */
  answered: number
  onAnswer: (answer: ProbeAnswer) => void
  onSkip: () => void
}

/** Step two: a short adaptive check. Each answer picks a harder or an easier next term. */
export function CheckStep({ term, answered, onAnswer, onSkip }: CheckStepProps) {
  return (
    <div className="px-safe flex min-h-0 flex-1 flex-col pb-5">
      <h1 className="sr-only">Quick check</h1>
      <p className="tabular pt-2 text-(length:--text-note) font-semibold text-ink-soft">
        Question {answered + 1} of {PROBE_QUESTIONS}
      </p>
      <progress className="sr-only" aria-label="Quick check progress" max={PROBE_QUESTIONS} value={answered} />
      <div aria-hidden="true" className="mt-2 h-1.5 overflow-hidden rounded-full bg-hall-raised">
        <div
          className="h-full origin-left rounded-full bg-fresh transition-transform duration-200"
          style={{ transform: `scaleX(${answered / PROBE_QUESTIONS})` }}
        />
      </div>

      <div
        key={term.id}
        aria-live="polite"
        className="on-lit mt-5 flex min-h-0 flex-1 flex-col justify-center rounded-(--radius-card) bg-lit px-5 text-lit-ink shadow-lift"
      >
        <p className="text-(length:--text-note) text-lit-soft">Do you know this one?</p>
        <p className="pt-2 font-display text-[2.75rem] leading-[1.05] break-words">{term.term}</p>
        {term.say && (
          <p className="pt-2 text-lit-soft">
            say <span className="font-bold text-lit-ink">{term.say}</span>
          </p>
        )}
      </div>

      <div className="flex flex-col gap-2 pt-5">
        {ANSWERS.map(({ answer, label, Icon, tone }) => (
          <Button key={answer} size="lg" className="w-full justify-start gap-3" onClick={() => onAnswer(answer)}>
            <Icon className={tone} aria-hidden="true" />
            {label}
          </Button>
        ))}
        <Button variant="ghost" className="w-full" onClick={onSkip}>
          Skip, use a persona
        </Button>
      </div>
    </div>
  )
}
