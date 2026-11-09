import { render, screen, within } from '@testing-library/react'
import type { Knowledge, Term } from '@contracts'
import { describe, expect, it } from 'vitest'
import { INITIAL_ROOM_DATA, useRoom } from '@/room/store'
import { Recap } from './Recap'

const term = (id: string, display: string): Term => ({
  id,
  term: display,
  aliases: [],
  say: null,
  category: 'data',
  level: 3,
  simple_def: 'x',
  prereqs: [],
  source: 'seed',
})

const learnedRecord: Knowledge = {
  user_id: 'user-1',
  term_id: 'learned',
  status: 'learning',
  source: 'srs',
  encounters: 3,
  ease: 2.5,
  interval_days: 7,
  reps: 3,
  due_at: null,
  learned: true,
}

const terms = [
  term('known', 'Known term'),
  term('learned', 'Learned term'),
  term('learning', 'Learning term'),
  term('unknown', 'Unknown term'),
]

describe('Recap', () => {
  it('shows heard terms that are neither known nor already learned', () => {
    useRoom.setState({
      ...INITIAL_ROOM_DATA,
      heard: { known: 5, learned: 4, learning: 3, unknown: 2 },
      terms: Object.fromEntries(terms.map((item) => [item.id, item])),
      knowledge: { known: 'known', learning: 'learning' },
      records: { learned: learnedRecord, learning: { ...learnedRecord, term_id: 'learning', learned: false } },
    })

    render(<Recap />)

    expect(screen.getByText('2')).toBeInTheDocument()
    expect(screen.getByText('new terms')).toBeInTheDocument()
    const list = screen.getByRole('list', { name: 'New terms' })
    expect(within(list).getAllByRole('button').map((button) => button.textContent)).toEqual([
      'Learning term',
      'Unknown term',
    ])
    expect(within(list).queryByText('Known term')).not.toBeInTheDocument()
    expect(within(list).queryByText('Learned term')).not.toBeInTheDocument()
  })
})
