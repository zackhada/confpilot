import { describe, expect, it } from 'vitest'
import { assignSeats, EMPTY_SEATS, sameSeats, type Seats } from './seats'

const clayton = { user_id: 'u-clayton', name: 'Clayton' }
const zack = { user_id: 'u-zack', name: 'Zack' }
const ana = { user_id: 'u-ana', name: 'Ana' }

describe('assignSeats', () => {
  it('seats speakers in the order they join', () => {
    const one = assignSeats(EMPTY_SEATS, [clayton])
    expect(one).toEqual([clayton, null])
    expect(assignSeats(one, [clayton, zack])).toEqual([clayton, zack])
  })

  it('keeps both sides when a phone reconnects and comes back last in the list', () => {
    const seats: Seats = [clayton, zack]
    expect(assignSeats(seats, [zack, clayton])).toEqual([clayton, zack])
  })

  it('holds the seat of a speaker who dropped, so they return to the same side', () => {
    const seats: Seats = [clayton, zack]
    const dropped = assignSeats(seats, [zack])
    expect(dropped).toEqual([clayton, zack])
    expect(assignSeats(dropped, [zack, clayton])).toEqual([clayton, zack])
  })

  it('gives a departed speaker’s seat to a newcomer who has nowhere to sit', () => {
    const seats: Seats = [clayton, zack]
    expect(assignSeats(seats, [zack, ana])).toEqual([ana, zack])
  })

  it('leaves a third speaker unseated while both seats are taken', () => {
    const seats: Seats = [clayton, zack]
    expect(assignSeats(seats, [clayton, zack, ana])).toEqual([clayton, zack])
  })

  it('picks up a changed display name', () => {
    const renamed = { ...clayton, name: 'Clay' }
    expect(assignSeats([clayton, zack], [renamed, zack])[0]).toEqual(renamed)
  })
})

describe('sameSeats', () => {
  it('compares by person and name', () => {
    expect(sameSeats([clayton, zack], [clayton, zack])).toBe(true)
    expect(sameSeats([clayton, zack], [zack, clayton])).toBe(false)
    expect(sameSeats([clayton, null], [clayton, zack])).toBe(false)
  })
})
