import { act, render, screen, within } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import { initialKnowledge } from '@/lib/sm2'
import { fetchRecap } from '@/room/api'
import { INITIAL_ROOM_DATA, useRoom } from '@/room/store'
import { Recap } from './Recap'

vi.mock('@/room/api', () => ({ fetchRecap: vi.fn() }))

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
