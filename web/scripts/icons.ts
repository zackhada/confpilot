// Renders the PWA icons from public/favicon.svg. Run once with `node scripts/icons.ts`
// whenever the mark changes; the PNGs are committed.
import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'

const publicDir = fileURLToPath(new URL('../public/', import.meta.url))
const ICONS: { file: string; size: number }[] = [
  { file: 'icon-192.png', size: 192 },
  { file: 'icon-512.png', size: 512 },
  { file: 'apple-touch-icon.png', size: 180 },
]

const svg = await readFile(`${publicDir}favicon.svg`, 'utf8')
// Full-bleed square so the maskable icon has no transparent corners.
const squared = svg.replace('rx="14" fill="#0c1326"', 'fill="#0c1326"')
const browser = await chromium.launch()
try {
  for (const { file, size } of ICONS) {
    const page = await browser.newPage({ viewport: { width: size, height: size } })
    await page.setContent(
      `<style>html,body{margin:0}svg{display:block;width:${size}px;height:${size}px}</style>${squared}`,
    )
    await page.screenshot({ path: `${publicDir}${file}` })
    await page.close()
  }
} finally {
  await browser.close()
}
