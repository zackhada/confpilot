import { describe, expect, it } from 'vitest'
import { parseHighlight, timeAgo } from './highlight'

describe('parseHighlight', () => {
  it('splits the text into marked and unmarked parts', () => {
    expect(parseHighlight('It uses <mark>BM25</mark> for keyword matches')).toEqual([
      { text: 'It uses ', marked: false },
      { text: 'BM25', marked: true },
      { text: ' for keyword matches', marked: false },
    ])
  })

  it('decodes escaped characters into text, never into markup', () => {
    const parts = parseHighlight('the user&#x27;s &lt;script&gt;alert(1)&lt;/script&gt; &amp; <mark>query</mark>')
    expect(parts[0]?.text).toBe("the user's <script>alert(1)</script> & ")
    expect(parts[1]).toEqual({ text: 'query', marked: true })
  })

  it('keeps any other tag as literal text', () => {
    expect(parseHighlight('<b>bold</b>')).toEqual([{ text: '<b>bold</b>', marked: false }])
  })

  it('handles text with no highlight and an empty string', () => {
    expect(parseHighlight('plain')).toEqual([{ text: 'plain', marked: false }])
    expect(parseHighlight('')).toEqual([])
  })
})

describe('timeAgo', () => {
  const now = 10_000_000
  it.each([
    [now - 20_000, 'just now'],
    [now - 4 * 60_000, '4 min ago'],
    [now - 2 * 3_600_000, '2 h ago'],
    [now - 50 * 3_600_000, '2 d ago'],
    [now + 5000, 'just now'],
  ])('formats %d as %s', (spokenAt, label) => {
    expect(timeAgo(spokenAt, now)).toBe(label)
  })
})
