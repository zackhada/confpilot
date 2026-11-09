// Takes the design-review screenshots: `pnpm screens` (needs `pnpm mock` and `pnpm dev`
// running). Phone shots are 375x812, the stage is 1440x900. Output: docs/screens/.
import { mkdir } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { chromium, type Browser, type Page } from 'playwright'

const BASE = process.env.SCREENS_BASE ?? 'http://localhost:5173'
const API = process.env.SCREENS_API ?? 'http://localhost:8000'
const OUT = fileURLToPath(new URL('../docs/screens/', import.meta.url))
const PHONE = { width: 375, height: 812 }
const STAGE = { width: 1440, height: 900 }
const ONLY = process.argv[2] ?? 'all'

type Theme = 'dark' | 'light'

interface PhoneOptions {
  room: string
  persona: 'Clayton' | 'Zack' | 'Ana'
  theme?: Theme
  lang?: string
}

async function openPhone(browser: Browser, options: PhoneOptions): Promise<Page> {
  const context = await browser.newContext({ viewport: PHONE, deviceScaleFactor: 2, hasTouch: true, isMobile: true })
  const page = await context.newPage()
  if (options.theme === 'light') {
    await page.addInitScript("window.localStorage.setItem('confpilot.theme', 'light')")
  }
  await page.goto(`${BASE}/?room=${options.room}`)
  await page.getByRole('radio', { name: new RegExp(options.persona) }).click()
  if (options.lang) await page.getByLabel('Add a line in your language').selectOption(options.lang)
  return page
}

async function shot(page: Page, name: string): Promise<void> {
  await page.screenshot({ path: `${OUT}${name}.png` })
  process.stdout.write(`saved ${name}.png\n`)
}

async function restartReplay(room: string): Promise<void> {
  await fetch(`${API}/api/mock/replay?room=${room}`, { method: 'POST' })
}

async function join(page: Page): Promise<void> {
  await page.getByRole('button', { name: 'Join the room' }).click()
  await page.getByRole('navigation', { name: 'Main' }).waitFor()
}

/** Wait until a card for `term` is on screen, then let its spring settle. */
async function waitForCard(page: Page, term: string, timeout = 70_000): Promise<void> {
  await page.getByRole('article', { name: term, exact: true }).first().waitFor({ timeout })
  await page.waitForTimeout(700)
}

/** Recap, flashcards (front and answer) and search, once a conversation has happened. */
async function afterTalkShots(page: Page): Promise<void> {
  const tab = (name: string) => page.getByRole('link', { name, exact: true }).click()
  await tab('Recap')
  await page.getByRole('list', { name: 'New terms' }).waitFor()
  await shot(page, 'recap-375-dark')
  await page.getByRole('list', { name: 'New terms' }).getByRole('button').first().click()
  await page.waitForTimeout(500)
  await shot(page, 'recap-375-dark-term')
  await page.getByRole('button', { name: 'Close' }).click()

  await tab('Cards')
  await shot(page, 'cards-375-dark-start')
  await page.getByRole('button', { name: 'Start reviewing' }).click()
  await page.waitForTimeout(300)
  await shot(page, 'cards-375-dark')
  await page.getByRole('button', { name: 'Show the answer', exact: true }).click()
  await page.waitForTimeout(600)
  await shot(page, 'cards-375-dark-answer')

  await tab('Ask')
  await shot(page, 'ask-375-dark-empty')
  await page.getByRole('button', { name: 'What did Zack say about RAG?' }).click()
  await page.getByText(/\d moments?$/).waitFor()
  await shot(page, 'ask-375-dark')
}

/** The optional "Tune it to me" flow: talk, adaptive check, map. */
async function probeShots(browser: Browser): Promise<void> {
  const page = await openPhone(browser, { room: 'shots-probe', persona: 'Clayton' })
  await page.getByRole('button', { name: 'Tune it to me first' }).click()
  await page.getByRole('textbox').fill(
    'I work at Radar on the platform team. We run Kubernetes clusters for customers, I am an SRE and I am on call most weeks.',
  )
  await shot(page, 'probe-375-dark-talk')
  await page.getByRole('button', { name: 'Continue' }).click()
  await page.getByText('Question 1 of 9').waitFor({ timeout: 15_000 })
  await shot(page, 'probe-375-dark-check')
  const answers = ['I could explain it', 'I’ve heard it', 'New to me', 'I could explain it']
  for (let i = 0; i < 12; i += 1) {
    if (await page.getByRole('heading', { name: 'Your map' }).isVisible()) break
    await page.getByRole('button', { name: answers[i % answers.length] }).click()
    await page.waitForTimeout(120)
  }
  await page.getByRole('heading', { name: 'Your map' }).waitFor()
  await page.waitForTimeout(1500)
  await shot(page, 'probe-375-dark-map')
  await page.context().close()
}

async function phoneShots(browser: Browser): Promise<void> {
  const joinPage = await openPhone(browser, { room: 'shots-join', persona: 'Clayton' })
  await shot(joinPage, 'join-375-dark')
  await joinPage.context().close()

  const dark = await openPhone(browser, { room: 'shots-dark', persona: 'Clayton', lang: 'es' })
  const light = await openPhone(browser, { room: 'shots-light', persona: 'Ana', theme: 'light', lang: 'es' })
  await join(dark)
  await shot(dark, 'live-375-dark-empty')
  await join(light)
  await Promise.all([waitForCard(dark, 'RAG'), waitForCard(light, 'cluster')])
  await shot(dark, 'live-375-dark-first-cards')
  await shot(light, 'live-375-light')
  await waitForCard(dark, 'RRF')
  await shot(dark, 'live-375-dark')
  await dark.getByRole('button', { name: 'Save', exact: true }).click()
  await afterTalkShots(dark)
  await dark.context().close()
  await light.context().close()
}

async function stageShots(browser: Browser): Promise<void> {
  const room = 'shots-stage'
  const context = await browser.newContext({ viewport: STAGE, deviceScaleFactor: 1 })
  const stage = await context.newPage()
  await stage.goto(`${BASE}/stage?room=${room}`)
  await stage.waitForTimeout(800)
  await shot(stage, 'stage-1440-waiting')
  const clayton = await openPhone(browser, { room, persona: 'Clayton' })
  const zack = await openPhone(browser, { room, persona: 'Zack' })
  await join(clayton)
  await join(zack)
  await restartReplay(room)
  await waitForCard(clayton, 'RRF')
  await shot(stage, 'stage-1440-dark')
  await Promise.all([context.close(), clayton.context().close(), zack.context().close()])
}

await mkdir(OUT, { recursive: true })
const browser = await chromium.launch()
try {
  if (ONLY === 'all' || ONLY === 'phone') await phoneShots(browser)
  if (ONLY === 'all' || ONLY === 'probe') await probeShots(browser)
  if (ONLY === 'all' || ONLY === 'stage') await stageShots(browser)
} finally {
  await browser.close()
}
