import { act, render, screen, within } from '@testing-library/react'
import type { Knowledge, Term } from '@contracts'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { initialKnowledge } from '@/lib/sm2'
import { fetchRecap } from '@/room/api'
import { INITIAL_ROOM_DATA, useRoom } from '@/room/store'
import { Recap } from './Recap'

vi.mock('@/room/api', () => ({ fetchRecap: vi.fn() }))

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

beforeEach(() => {
  vi.mocked(fetchRecap).mockReset()
  useRoom.setState({ ...INITIAL_ROOM_DATA })
})

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

  it('waits for membership, lists all unfamiliar terms, and clears them for another room', async () => {
    const me = { user_id: 'zack', name: 'Zack' }
    const ids = Array.from({ length: 12 }, (_, i) => `term-${i}`)
    vi.mocked(fetchRecap).mockResolvedValue({
      room: 'slc1',
      new_term_count: 14,
      learn_next: ids.slice(0, 10),
      heard: [...ids, 'rag', 'rrf'].map((term_id) => ({ term_id, count: 1 })),
    })
    useRoom.setState({
      ...INITIAL_ROOM_DATA,
      room: 'slc1',
      status: 'open',
      me,
      knowledge: { rag: 'known' },
      records: { rrf: { ...initialKnowledge('zack', 'rrf'), learned: true } },
    })
    render(<Recap />)
    expect(fetchRecap).not.toHaveBeenCalled()
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('You heard0new terms')
    expect(screen.queryByText(/nothing to recap/i)).not.toBeInTheDocument()

    act(() => useRoom.setState({ members: [{ ...me, role: 'speaker' }] }))
    const list = await screen.findByRole('list', { name: 'New terms' })
    expect(within(list).getAllByRole('button').map((button) => button.textContent)).toEqual(ids)
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('You heard12new terms')

    act(() => useRoom.setState({ room: 'another', members: [] }))
    expect(screen.queryByRole('list', { name: 'New terms' })).not.toBeInTheDocument()
  })
})
