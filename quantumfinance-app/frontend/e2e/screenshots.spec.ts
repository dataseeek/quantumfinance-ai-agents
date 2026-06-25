import { test, expect } from '@playwright/test'

const BASE = 'http://localhost:3000'

test.use({
  viewport: { width: 1440, height: 900 },
  baseURL: BASE,
})

const pages = [
  { path: '/',          name: '01-dashboard',  waitFor: 'text=Watchlist' },
  { path: '/news',      name: '02-news',       waitFor: 'select' },
  { path: '/cvm',       name: '03-cvm',        waitFor: 'select' },
  { path: '/chat',      name: '04-chat',       waitFor: 'text=Chat com Agentes' },
  { path: '/portfolio', name: '05-portfolio',  waitFor: 'text=Carteira' },
  { path: '/backtest',  name: '06-backtest',   waitFor: 'text=Backtest' },
  { path: '/agents',    name: '07-agents',     waitFor: 'text=Agentes' },
  { path: '/settings',  name: '08-settings',   waitFor: 'text=Settings' },
]

for (const p of pages) {
  test(`screenshot ${p.name}`, async ({ page }) => {
    await page.goto(p.path)
    // Be lenient about waiting for content; some pages depend on slow first fetch
    try {
      await page.waitForSelector(p.waitFor, { timeout: 5000 })
    } catch { /* keep going even if locator not found — page may still render */ }
    // Give charts a moment to draw
    await page.waitForTimeout(2000)
    await page.screenshot({
      path: `../../docs/screenshots/${p.name}.png`,
      fullPage: true,
    })
  })
}
