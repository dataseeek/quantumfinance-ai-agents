import { test, expect } from '@playwright/test'

const TICKERS = ['VALE3', 'PETR4', 'BBAS3', 'ITUB4']

test.describe('QuantumFinance AI Agent Home Broker — E2E', () => {

  test('1 · Dashboard loads with watchlist + chart + recs sidebar', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
    // Watchlist: 4 tickers
    for (const t of TICKERS) {
      await expect(page.locator('aside, main').getByText(t, { exact: false }).first()).toBeVisible()
    }
    // Chart heading shows selected ticker
    await expect(page.getByRole('heading', { name: 'VALE3' })).toBeVisible()
    // Sidebar recs card present
    await expect(page.getByText('Última recomendação')).toBeVisible()
    // Rodar crew button visible
    await expect(page.getByRole('button', { name: /Rodar crew agora|Rodando crew/ })).toBeVisible()
  })

  test('2 · Watchlist click changes selection', async ({ page }) => {
    await page.goto('/')
    await page.getByText('PETR4').first().click()
    await expect(page.getByRole('heading', { name: 'PETR4' })).toBeVisible()
  })

  test('3 · News page loads + ingest works', async ({ page }) => {
    await page.goto('/news')
    await expect(page.getByRole('heading', { name: 'Notícias' })).toBeVisible()
    await page.getByRole('button', { name: 'Ingerir agora' }).click()
    // Wait for either result or "no news" message — just confirms no crash
    await page.waitForTimeout(8000)
    const card = page.locator('.card').first()
    await expect(card).toBeVisible()
  })

  test('4 · CVM page loads (without refresh, just cached list)', async ({ page }) => {
    await page.goto('/cvm')
    await expect(page.getByRole('heading', { name: /CVM/ })).toBeVisible()
    // List or empty message must render
    const card = page.locator('.card').first()
    await expect(card).toBeVisible()
  })

  test('5 · Chat: WS connects + crew message returns', async ({ page }) => {
    await page.goto('/chat')
    await expect(page.getByText('● conectado')).toBeVisible({ timeout: 10000 })
    // Switch to a specific agent (faster, no full crew run)
    await page.getByRole('combobox').first().selectOption('investment_strategist')
    const input = page.locator('input[placeholder*="Pergunte"]')
    await input.fill('Responda apenas: OK')
    await page.getByRole('button', { name: 'Enviar' }).click()
    // Wait for at least one assistant message to appear
    await expect(page.getByText('investment_strategist').first()).toBeVisible({ timeout: 60000 })
  })

  test('6 · Portfolio: shows default + place order', async ({ page }) => {
    await page.goto('/portfolio')
    await expect(page.getByRole('heading', { name: /Portfolio/ })).toBeVisible()
    // KPIs visible
    await expect(page.getByText('Cash').first()).toBeVisible()
    await expect(page.getByText('Equity').first()).toBeVisible()
    // Place order
    await page.locator('select').first().selectOption('PETR4')
    await page.locator('select').nth(1).selectOption('BUY')
    await page.locator('input[type="number"]').fill('10')
    const submit = page.getByRole('button', { name: /Comprar|Vender/ })
    await submit.click()
    // Wait for either success text or error
    const successOrError = page.getByText(/Ordem executada|Insufficient|Erro/)
    await expect(successOrError).toBeVisible({ timeout: 15000 })
  })

  test('7 · Agents page shows 4 system + tools registry', async ({ page }) => {
    await page.goto('/agents')
    await expect(page.getByRole('heading', { name: 'Agentes' })).toBeVisible()
    // 4 system agents must appear
    await expect(page.getByText('news_analyst')).toBeVisible()
    await expect(page.getByText('technical_analyst')).toBeVisible()
    await expect(page.getByText('investment_strategist')).toBeVisible()
    await expect(page.getByText('cvm_ri_analyst')).toBeVisible()
    // Open create form
    await page.getByRole('button', { name: '+ Novo agente' }).click()
    // Tools must be listed as checkboxes (use checkbox role to disambiguate from text in agent cards)
    await expect(page.getByRole('checkbox', { name: 'search_news' })).toBeVisible()
    await expect(page.getByRole('checkbox', { name: 'get_cvm_filings' })).toBeVisible()
  })

  test('8 · Agents: create custom + delete', async ({ page }) => {
    await page.goto('/agents')
    await page.getByRole('button', { name: '+ Novo agente' }).click()
    const uniq = 'test_agent_' + Date.now()
    await page.locator('input[placeholder*="name"]').fill(uniq)
    await page.locator('input[placeholder*="role"]').fill('Agente de teste E2E')
    await page.locator('textarea[placeholder*="goal"]').fill('Testar a UI')
    await page.locator('textarea[placeholder*="backstory"]').fill('Sou um agente de teste')
    await page.getByRole('checkbox', { name: 'search_news' }).check()
    await page.getByRole('button', { name: 'Criar agente' }).click()
    // The new agent should appear in the list
    await expect(page.getByText(uniq)).toBeVisible({ timeout: 10000 })
    // Delete it
    const card = page.locator('.card').filter({ hasText: uniq })
    await card.getByRole('button', { name: 'Deletar' }).click()
    await expect(page.getByText(uniq)).toHaveCount(0, { timeout: 10000 })
  })

  test('9 · Settings: shows crons + jobs', async ({ page }) => {
    await page.goto('/settings')
    await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible()
    await expect(page.getByText('news_ingest_cron')).toBeVisible()
    await expect(page.getByText('crew_run_cron')).toBeVisible()
    await expect(page.getByText('cvm_ingest_cron')).toBeVisible()
    // Active jobs table
    await expect(page.getByText('news').first()).toBeVisible()
    await expect(page.getByText('cvm').first()).toBeVisible()
  })

  test('10 · Rodar crew (slow, ~30s)', async ({ page }) => {
    test.setTimeout(120_000)
    await page.goto('/')
    // Switch to PETR4 to vary
    await page.getByText('PETR4').first().click()
    await page.getByRole('button', { name: /Rodar crew agora/ }).click()
    // Button text changes to "Rodando crew…"
    await expect(page.getByRole('button', { name: /Rodando crew/ })).toBeVisible()
    // Wait for recommendation pill to populate
    const pill = page.locator('.pill-buy, .pill-sell, .pill-hold').first()
    await expect(pill).toBeVisible({ timeout: 90_000 })
  })

})
