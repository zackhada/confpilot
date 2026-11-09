import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import { askRoom } from '@/room/api'
import { INITIAL_ROOM_DATA, useRoom } from '@/room/store'
import { Ask } from './Ask'

vi.mock('@/room/api', () => ({ askRoom: vi.fn() }))

it('answers arbitrary questions, keeps eight source moments, and suggests only the RAG question', async () => {
  const me = { user_id: 'demo-zack', name: 'Zack' }
  useRoom.setState({ ...INITIAL_ROOM_DATA, me, room: 'slc1', status: 'open', members: [{ ...me, role: 'speaker' }] })
  vi.mocked(askRoom).mockImplementation(async (_name, body, onEvent) => {
    onEvent({
      type: 'moments',
      hits: Array.from({ length: 8 }, (_, i) => ({
        utterance_id: String(i), speaker: me, spoken_at: 1000,
        text: `Source moment ${i}`, highlight: '', term_ids: [],
      })),
    })
    onEvent({ type: 'answer', answer: `Grounded answer to ${body.question}` })
  })

  render(<Ask />)
  expect(screen.queryByRole('button', { name: /rank results|¿Qué/ })).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'What did Zack say about RAG?' }))
  expect(await screen.findByText('Grounded answer to What did Zack say about RAG?')).toBeInTheDocument()
  expect(screen.getByText('8 moments')).toBeInTheDocument()
  fireEvent.change(screen.getByRole('searchbox', { name: 'Your question' }), { target: { value: 'What is hybrid search?' } })
  fireEvent.click(screen.getByRole('button', { name: 'Ask the agent' }))
  await waitFor(() => expect(screen.getByText('Grounded answer to What is hybrid search?')).toBeInTheDocument())
  expect(askRoom).toHaveBeenCalledTimes(2)
})
