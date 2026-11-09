import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import { askRoom, searchRoom } from '@/room/api'
import { INITIAL_ROOM_DATA, useRoom } from '@/room/store'
import { Ask } from './Ask'

vi.mock('@/room/api', () => ({ askRoom: vi.fn(), searchRoom: vi.fn() }))

it('previews matches while typing, then shows the prepared RAG answer on submit', async () => {
  const me = { user_id: 'demo-zack', name: 'Zack' }
  const hits = Array.from({ length: 8 }, (_, i) => ({
    utterance_id: String(i), speaker: me, spoken_at: 1000,
    text: `Source moment ${i}`, highlight: '', term_ids: [],
  }))
  useRoom.setState({ ...INITIAL_ROOM_DATA, me, room: 'slc1', status: 'open', members: [{ ...me, role: 'speaker' }] })
  vi.mocked(searchRoom).mockResolvedValue(hits)
  vi.mocked(askRoom).mockImplementation(async (_name, body, onEvent) => {
    onEvent({ type: 'moments', hits })
    onEvent({ type: 'answer', answer: `Grounded answer to ${body.question}` })
  })

  render(<Ask />)
  fireEvent.change(screen.getByRole('searchbox', { name: 'Your question' }), { target: { value: 'What did Zack say about RAG?' } })
  expect(await screen.findByText('8 moments')).toBeInTheDocument()
  expect(screen.queryByRole('heading', { name: 'Answer' })).not.toBeInTheDocument()
  fireEvent.submit(screen.getByRole('searchbox', { name: 'Your question' }).closest('form')!)
  expect(screen.getByText(/Zack described RAG as/)).toBeInTheDocument()
  expect(askRoom).not.toHaveBeenCalled()
  expect(screen.getByText('8 moments')).toBeInTheDocument()

  fireEvent.change(screen.getByRole('searchbox', { name: 'Your question' }), { target: { value: 'What is hybrid search?' } })
  fireEvent.click(screen.getByRole('button', { name: 'Ask the agent' }))
  await waitFor(() => expect(screen.getByText('Grounded answer to What is hybrid search?')).toBeInTheDocument())
  expect(askRoom).toHaveBeenCalledTimes(1)
  act(() => useRoom.setState({ me: { user_id: 'another-user', name: 'Ana' } }))
  expect(screen.queryByText('Grounded answer to What is hybrid search?')).not.toBeInTheDocument()
})
