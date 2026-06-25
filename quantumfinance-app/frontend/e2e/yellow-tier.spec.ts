import { test, expect } from '@playwright/test'

const API = 'http://localhost:8000'
const PAGES = [
  { link: 'News', heading: 'Notícias' },
  { link: 'CVM RI', heading: /CVM/ },
  { link: 'Chat', heading: 'Chat com Agentes' },
  { link: 'Portfolio', heading: /Portfolio/ },
  { link: 'Agents', heading: 'Agentes' },
  { link: 'Settings', heading: 'Settings' },
  { link: 'Dashboard', heading: 'Dashboard' },
]

test.describe('Yellow-tier — coverage adicional', () => {

  test('Y1 · Navegação completa via sidebar (7 links)', async ({ page }) => {
    await page.goto('/')
    for (const p of PAGES) {
      await page.getByRole('link', { name: p.link }).click()
      await expect(page.getByRole('heading', { name: p.heading }).first()).toBeVisible()
    }
  })

  test('Y2 · Chart endpoint aceita períodos diferentes', async ({ request }) => {
    for (const period of ['3mo', '6mo', '1y']) {
      const r = await request.get(`${API}/api/chart/VALE3?period=${period}`)
      expect(r.ok()).toBeTruthy()
      const data = await r.json()
      expect(data.period).toBe(period)
      expect(data.ohlc.length).toBeGreaterThan(20)
    }
  })

  test('Y3 · Múltiplas recs para o mesmo ticker se acumulam', async ({ request }) => {
    test.setTimeout(240_000)
    const before = await (await request.get(`${API}/api/recommendations`)).json()
    const valeBefore = before.filter((r: any) => r.ticker === 'VALE3').length
    // Roda crew com 1 retry caso rate-limit OpenRouter
    let run = await request.post(`${API}/api/recommendations/run`, {
      data: { ticker: 'VALE3' }, timeout: 120_000,
    })
    if (!run.ok()) {
      await new Promise(r => setTimeout(r, 30_000))
      run = await request.post(`${API}/api/recommendations/run`, {
        data: { ticker: 'VALE3' }, timeout: 120_000,
      })
    }
    expect(run.ok()).toBeTruthy()
    const after = await (await request.get(`${API}/api/recommendations`)).json()
    const valeAfter = after.filter((r: any) => r.ticker === 'VALE3').length
    expect(valeAfter).toBeGreaterThan(valeBefore)
  })

  test('Y4 · Quick prompts no chat popula input', async ({ page }) => {
    await page.goto('/chat')
    await expect(page.getByText('● conectado')).toBeVisible({ timeout: 25000 })
    const prompt = 'Por que VALE3 está com AGUARDAR?'
    await page.getByRole('button', { name: prompt }).click()
    const input = page.locator('input[placeholder*="Pergunte"]')
    await expect(input).toHaveValue(prompt)
  })

  test('Y5 · POST /api/scheduler/run/{job_id} dispara job', async ({ request }) => {
    // O job "news" é rápido (RSS); rodá-lo manualmente não pode falhar
    const r = await request.post(`${API}/api/scheduler/run/news`, { timeout: 60_000 })
    expect(r.ok()).toBeTruthy()
    const body = await r.json()
    expect(body.ok).toBe(true)
  })

  test('Y6 · PUT /api/agents/{id}: edita custom agent', async ({ request }) => {
    // Cria
    const uniq = 'edit_test_' + Date.now()
    const c = await request.post(`${API}/api/agents`, {
      data: {
        name: uniq, role: 'Test Role', goal: 'Test', backstory: 'Test',
        tool_names: ['search_news'], max_iter: 3,
      },
    })
    expect(c.ok()).toBeTruthy()
    const id = (await c.json()).id
    // Edita
    const u = await request.put(`${API}/api/agents/${id}`, {
      data: {
        name: uniq, role: 'Edited Role', goal: 'Edited goal', backstory: 'Edited',
        tool_names: ['search_news', 'get_cvm_filings'], max_iter: 5,
      },
    })
    expect(u.ok()).toBeTruthy()
    // Verifica
    const list = await (await request.get(`${API}/api/agents`)).json()
    const found = list.find((a: any) => a.id === id)
    expect(found.role).toBe('Edited Role')
    expect(found.tool_names).toContain('get_cvm_filings')
    expect(found.max_iter).toBe(5)
    // Cleanup
    await request.delete(`${API}/api/agents/${id}`)
  })

  test('Y7 · Chat session list endpoint funciona', async ({ request }) => {
    const r = await request.get(`${API}/api/chat-sessions`)
    expect(r.ok()).toBeTruthy()
    const sessions = await r.json()
    expect(Array.isArray(sessions)).toBeTruthy()
    // Não verificamos contagem (depende do estado anterior)
  })

  test('Y8 · Agents UI: edit form abre + tem campos pré-preenchidos', async ({ page, request }) => {
    // Cria via API
    const uniq = 'ui_edit_' + Date.now()
    const c = await request.post(`${API}/api/agents`, {
      data: {
        name: uniq, role: 'UI Edit Role', goal: 'g', backstory: 'b',
        tool_names: ['search_news'], max_iter: 4,
      },
    })
    const id = (await c.json()).id
    await page.goto('/agents')
    // Find the agent card and click Editar
    const card = page.locator('.card').filter({ hasText: uniq })
    await card.getByRole('button', { name: 'Editar' }).click()
    // Heading muda
    await expect(page.getByText(`Editar agente #${id}`)).toBeVisible()
    // Role pré-preenchida
    await expect(page.locator('input[placeholder*="role"]')).toHaveValue('UI Edit Role')
    // Cleanup
    await request.delete(`${API}/api/agents/${id}`)
  })

})
