import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'
import { TabBar } from './TabBar'

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <TabBar />
    </MemoryRouter>,
  )
}

describe('TabBar', () => {
  it('names all four tabs inside a labelled navigation landmark', () => {
    renderAt('/')
    const nav = screen.getByRole('navigation', { name: 'Main' })
    expect(nav).toBeInTheDocument()
    for (const name of ['Live', 'Recap', 'Cards', 'Agent']) {
      expect(screen.getByRole('link', { name })).toBeInTheDocument()
    }
  })

  it('marks only the current tab with aria-current', () => {
    renderAt('/cards')
    expect(screen.getByRole('link', { name: 'Cards' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('link', { name: 'Live' })).not.toHaveAttribute('aria-current')
  })

  it('keeps the room code when moving between tabs', () => {
    renderAt('/?room=slc1')
    expect(screen.getByRole('link', { name: 'Recap' })).toHaveAttribute('href', '/recap?room=slc1')
  })
})
