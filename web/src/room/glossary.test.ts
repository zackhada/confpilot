import { describe, expect, it, vi } from 'vitest'
import realGlossary from '../../../content/glossary.json'
import sampleGlossary from '../../../contracts/fixtures/glossary.sample.json'
import { cachedGlossary, loadGlossary, parseGlossary } from './glossary'

function respond(body: unknown, status = 200): typeof fetch {
  return vi.fn(async () => new Response(JSON.stringify(body), { status })) as unknown as typeof fetch
}

describe('parseGlossary', () => {
  it('accepts the real glossary, whose version is a number and whose say is often null', () => {
    const glossary = parseGlossary(realGlossary)
    expect(glossary?.version).toBe(String(realGlossary.version))
    expect(glossary?.terms).toHaveLength(realGlossary.terms.length)
    expect(glossary?.terms.some((term) => term.say === null)).toBe(true)
  })

  it('accepts the sample fixture', () => {
    expect(parseGlossary(sampleGlossary)?.terms.length).toBe(sampleGlossary.terms.length)
  })

  it.each([null, [], { version: '1' }, { version: '1', terms: [{ id: 'x' }] }])('rejects %j', (value) => {
    expect(parseGlossary(value)).toBeNull()
  })
})

describe('loadGlossary', () => {
  it('saves a copy on the phone and falls back to it when the network fails', async () => {
    const fresh = await loadGlossary(respond(sampleGlossary))
    expect(cachedGlossary()?.version).toBe(fresh.version)
    const offline = await loadGlossary(respond({}, 503))
    expect(offline.terms).toHaveLength(sampleGlossary.terms.length)
  })

  it('throws when the request fails and nothing is saved', async () => {
    await expect(loadGlossary(respond({}, 503))).rejects.toThrow(/glossary request failed \(503\)/)
  })

  it('throws on an unexpected shape rather than trusting it', async () => {
    await expect(loadGlossary(respond({ terms: 'nope' }))).rejects.toThrow(/unexpected shape/)
  })
})
