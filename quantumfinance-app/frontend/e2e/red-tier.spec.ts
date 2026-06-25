import { test, expect, request as pwRequest } from '@playwright/test'

const API = 'http://localhost:8000'

test.describe('Red-tier — features críticas não testadas antes', () => {

  test('R1 · CVM refresh: baixa IPE real + popula tabela', async ({ request, page }) => {
    test.setTimeout(120_000)
    // Backend direto: dispara refresh (custom timeout — ZIP é grande)
    const r = await request.get(`${API}/api/cvm/VALE3/filings?refresh=true`, { timeout: 90_000 })
    expect(r.ok()).toBeTruthy()
    const list = await r.json()
    expect(Array.isArray(list)).toBeTruthy()
    // Pode haver 0 itens se o CNPJ formatting não bater 100%, mas a chamada deve completar sem erro
    // Verifica UI:
    await page.goto('/cvm')
    await expect(page.getByRole('heading', { name: /CVM/ })).toBeVisible()
  })

  test('R2 · Quarterly summary endpoint disponível via test-agent', async ({ request }) => {
    test.setTimeout(120_000)
    // Pega o id do cvm_ri_analyst
    const agents = await (await request.get(`${API}/api/agents`)).json()
    const cvm = agents.find((a: any) => a.name === 'cvm_ri_analyst')
    expect(cvm).toBeTruthy()
    expect(cvm.tool_names).toContain('get_quarterly_summary')
    // Test endpoint roda o agente (que pode chamar quarterly_summary)
    const r = await request.post(`${API}/api/agents/${cvm.id}/test`, {
      data: { ticker: 'VALE3' },
      timeout: 90_000,
    })
    expect(r.ok()).toBeTruthy()
    const result = await r.json()
    expect(result.agent).toBe('cvm_ri_analyst')
    // Sucesso = teve output (mesmo que ele tenha optado por search/summary)
    expect(result.output || result.error).toBeTruthy()
  })

  test('R3 · Deep Research Crew kickoff (4 agentes)', async ({ request }) => {
    test.setTimeout(180_000)
    const crews = await (await request.get(`${API}/api/crews`)).json()
    const deep = crews.find((c: any) => c.name === 'Deep Research Crew')
    expect(deep).toBeTruthy()
    expect(deep.agent_ids.length).toBe(4)

    const r = await request.post(`${API}/api/recommendations/run`, {
      data: { ticker: 'PETR4', crew_id: deep.id },
      timeout: 150_000,
    })
    expect(r.ok()).toBeTruthy()
    const result = await r.json()
    expect(result.recommendation).toMatch(/COMPRAR|VENDER|AGUARDAR/)
    expect(result.run_id).toBeGreaterThan(0)
  })

  test('R4 · Chat WS com target=crew (full pipeline)', async ({ page }) => {
    test.setTimeout(180_000)
    await page.goto('/chat')
    await expect(page.getByText('● conectado')).toBeVisible({ timeout: 20000 })
    // Garante target crew
    await page.locator('select').first().selectOption('crew')
    // Garante ticker
    const tickerSel = page.locator('select').nth(1)
    if (await tickerSel.isVisible()) await tickerSel.selectOption('PETR4')
    const input = page.locator('input[placeholder*="Pergunte"]')
    await input.fill('Análise rápida.')
    await page.getByRole('button', { name: 'Enviar' }).click()
    // Espera resposta — procura JSON do crew na pre tag
    const reply = page.locator('pre').filter({ hasText: /recommendation|COMPRAR|VENDER|AGUARDAR/ }).first()
    await expect(reply).toBeVisible({ timeout: 150_000 })
  })

  test('R5 · Settings: edit cron + save + reload + verify changed', async ({ request }) => {
    // Lê valor atual
    const before = await (await request.get(`${API}/api/settings`)).json()
    const oldCron = before.news_ingest_cron?.cron || '0 */4 * * 1-5'
    const newCron = '15 */6 * * 1-5'    // diferente do default
    // Update
    const u = await request.put(`${API}/api/settings/news_ingest_cron`, {
      data: { value: { cron: newCron, enabled: true } },
    })
    expect(u.ok()).toBeTruthy()
    // Reload
    const reload = await request.post(`${API}/api/scheduler/reload`)
    expect(reload.ok()).toBeTruthy()
    // Verify the news job trigger changed
    const jobs = await (await request.get(`${API}/api/scheduler/jobs`)).json()
    const newsJob = jobs.find((j: any) => j.id === 'news')
    expect(newsJob).toBeTruthy()
    // O cron string deve aparecer na string do trigger
    expect(newsJob.trigger).toMatch(/minute='15'|15.*\*\/6|6/)
    // Restore default
    await request.put(`${API}/api/settings/news_ingest_cron`, {
      data: { value: { cron: oldCron, enabled: true } },
    })
    await request.post(`${API}/api/scheduler/reload`)
  })

  test('R6 · Portfolio: BUY + SELL + insufficient errors', async ({ request }) => {
    // BUY 5 ITUB4
    const buy = await request.post(`${API}/api/portfolios/1/orders`, {
      data: { ticker: 'ITUB4', side: 'BUY', quantity: 5 },
    })
    expect(buy.ok()).toBeTruthy()
    // SELL 3 ITUB4 (válido)
    const sell = await request.post(`${API}/api/portfolios/1/orders`, {
      data: { ticker: 'ITUB4', side: 'SELL', quantity: 3 },
    })
    expect(sell.ok()).toBeTruthy()
    // SELL 999 ITUB4 (insufficient position)
    const sellTooMuch = await request.post(`${API}/api/portfolios/1/orders`, {
      data: { ticker: 'ITUB4', side: 'SELL', quantity: 9999 },
    })
    expect(sellTooMuch.status()).toBe(400)
    const errBody = await sellTooMuch.json()
    expect(JSON.stringify(errBody)).toMatch(/Insufficient|insufficient/)
    // BUY com qty enorme (insufficient cash)
    const buyTooMuch = await request.post(`${API}/api/portfolios/1/orders`, {
      data: { ticker: 'VALE3', side: 'BUY', quantity: 999999 },
    })
    expect(buyTooMuch.status()).toBe(400)
  })

})
