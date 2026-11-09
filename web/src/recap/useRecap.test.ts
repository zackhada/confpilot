import { act, renderHook } from '@testing-library/react'
import type { Recap } from '@contracts'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fetchRecap } from '@/room/api'
import { INITIAL_ROOM_DATA, useRoom } from '@/room/store'
import { useRecap } from './useRecap'

vi.mock('@/room/api', () => ({ fetchRecap: vi.fn() }))

const me = { user_id: 'user-1', name: 'Clayton' }
const recap: Recap = {
  room: 'slc1',
  new_term_count: 1,
  heard: [{ term_id: 'rag', count: 1 }],
  learn_next: ['rag'],
}

beforeEach(() => {
  vi.mocked(fetchRecap).mockReset()
  useRoom.setState({
    ...INITIAL_ROOM_DATA,
    status: 'open',
    room: 'slc1',
    me,
    members: [{ ...me, role: 'speaker' }],
    heard: { rag: 1 },
  })
})

describe('useRecap', () => {
  it('waits until the current user is a room member before fetching', async () => {
    vi.mocked(fetchRecap).mockResolvedValue(recap)
    useRoom.setState({ members: [] })

    const { result } = renderHook(() => useRecap())
    expect(fetchRecap).not.toHaveBeenCalled()
    expect(result.current.source).toBe('local')

    act(() => useRoom.setState({ members: [{ ...me, role: 'speaker' }] }))

    await vi.waitFor(() => expect(fetchRecap).toHaveBeenCalledWith('Clayton', 'slc1', 'user-1'))
    await vi.waitFor(() => expect(result.current.source).toBe('api'))
  })

  it('refetches when a distinct term is heard, not for another mention of one already heard', async () => {
    vi.mocked(fetchRecap).mockResolvedValue(recap)
    renderHook(() => useRecap())

    await vi.waitFor(() => expect(fetchRecap).toHaveBeenCalledTimes(1))

    act(() => useRoom.setState({ heard: { rag: 2 } }))
    expect(fetchRecap).toHaveBeenCalledTimes(1)

    act(() => useRoom.setState({ heard: { rag: 2, bm25: 1 } }))
    await vi.waitFor(() => expect(fetchRecap).toHaveBeenCalledTimes(2))
  })
})
