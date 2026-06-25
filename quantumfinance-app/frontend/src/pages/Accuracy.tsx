import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api'

type Detail = {
  id: number
  ticker: string
  rec_date: string
  entry_date: string
  exit_date: string
  recommendation: string
  entry_price: number
  exit_price: number
  move_pct: number
  result: 'hit' | 'miss'
}

type HitRate = {
  horizon_days: number
  total_recommendations: number
  total_evaluated: number
  pending: number
  skipped: number
  hits: number
  misses: number
  hit_rate_pct: number
  by_ticker: Record<string, { total: number; hits: number; misses: number; hit_rate_pct: number }>
  by_recommendation: Record<string, { total: number; hits: number; misses: number; hit_rate_pct: number }>
  details: Detail[]
}

const HORIZONS = [1, 3, 5, 10] as const

function pctColor(p: number) {
  if (p >= 60) return 'var(--green)'
  if (p >= 40) return 'var(--text)'
  return 'var(--red)'
}

function moveColor(m: number) {
  if (m > 0.5) return 'var(--green)'
  if (m < -0.5) return 'var(--red)'
  return 'var(--text-muted)'
}

export default function Accuracy() {
  const [horizon, setHorizon] = useState<typeof HORIZONS[number]>(3)

  const q = useQuery({
    queryKey: ['hit-rate', horizon],
    queryFn: async () => (await api.get<HitRate>(`/hit-rate?horizon_days=${horizon}`)).data,
  })

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
        <h1 style={{ fontSize: 22 }}>Acurácia das recomendações</h1>
        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Horizonte D+</span>
        <select value={horizon} onChange={e => setHorizon(Number(e.target.value) as typeof HORIZONS[number])}>
          {HORIZONS.map(h => <option key={h} value={h}>{h} dia{h > 1 ? 's' : ''}</option>)}
        </select>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ fontSize: 14, marginBottom: 12 }}>Regras</h3>
        <ul style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.8, paddingLeft: 18 }}>
          <li><strong>COMPRAR</strong> acerta se o preço subiu mais que <strong>+0.5%</strong> em D+{horizon}</li>
          <li><strong>VENDER</strong> acerta se o preço caiu mais que <strong>-0.5%</strong> em D+{horizon}</li>
          <li><strong>AGUARDAR</strong> acerta se ficou lateral (<strong>|move| &lt; 1.0%</strong>) em D+{horizon}</li>
        </ul>
      </div>

      {q.isLoading && <p style={{ color: 'var(--text-muted)' }}>Carregando…</p>}
      {q.isError && <p style={{ color: 'var(--red)' }}>Falha ao carregar.</p>}

      {q.data && (
        <>
          {/* KPIs */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12, marginBottom: 16 }}>
            <div className="card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 28, fontWeight: 700, color: pctColor(q.data.hit_rate_pct) }}>
                {q.data.hit_rate_pct.toFixed(1)}%
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>HIT RATE D+{horizon}</div>
            </div>
            <div className="card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--text)' }}>{q.data.total_evaluated}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>AVALIADAS</div>
            </div>
            <div className="card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--green)' }}>{q.data.hits}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>HITS</div>
            </div>
            <div className="card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--red)' }}>{q.data.misses}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>MISSES</div>
            </div>
            <div className="card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--text-muted)' }}>{q.data.pending}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>PENDENTES</div>
            </div>
          </div>

          {/* Breakdowns */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
            <div className="card">
              <h3 style={{ fontSize: 14, marginBottom: 12 }}>Por ticker</h3>
              <table>
                <thead>
                  <tr>
                    <th>Ticker</th>
                    <th style={{ textAlign: 'right' }}>Avaliadas</th>
                    <th style={{ textAlign: 'right' }}>Hits</th>
                    <th style={{ textAlign: 'right' }}>Hit rate</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(q.data.by_ticker).sort().map(([t, b]) => (
                    <tr key={t}>
                      <td><strong>{t}</strong></td>
                      <td style={{ textAlign: 'right' }}>{b.total}</td>
                      <td style={{ textAlign: 'right' }}>{b.hits}</td>
                      <td style={{ textAlign: 'right', color: pctColor(b.hit_rate_pct), fontWeight: 600 }}>
                        {b.hit_rate_pct.toFixed(1)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="card">
              <h3 style={{ fontSize: 14, marginBottom: 12 }}>Por tipo de recomendação</h3>
              <table>
                <thead>
                  <tr>
                    <th>Rec</th>
                    <th style={{ textAlign: 'right' }}>Total</th>
                    <th style={{ textAlign: 'right' }}>Hits</th>
                    <th style={{ textAlign: 'right' }}>Hit rate</th>
                  </tr>
                </thead>
                <tbody>
                  {['COMPRAR', 'AGUARDAR', 'VENDER'].map(rec => {
                    const b = q.data!.by_recommendation[rec]
                    if (!b) return null
                    return (
                      <tr key={rec}>
                        <td><strong>{rec}</strong></td>
                        <td style={{ textAlign: 'right' }}>{b.total}</td>
                        <td style={{ textAlign: 'right' }}>{b.hits}</td>
                        <td style={{ textAlign: 'right', color: pctColor(b.hit_rate_pct), fontWeight: 600 }}>
                          {b.hit_rate_pct.toFixed(1)}%
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Detalhes */}
          <div className="card">
            <h3 style={{ fontSize: 14, marginBottom: 12 }}>
              Últimas {q.data.details.length} recomendações avaliadas
            </h3>
            <table>
              <thead>
                <tr>
                  <th>Ticker</th>
                  <th>Entry</th>
                  <th>Exit</th>
                  <th>Rec</th>
                  <th style={{ textAlign: 'right' }}>Preço entry</th>
                  <th style={{ textAlign: 'right' }}>Preço exit</th>
                  <th style={{ textAlign: 'right' }}>Move %</th>
                  <th style={{ textAlign: 'center' }}>Resultado</th>
                </tr>
              </thead>
              <tbody>
                {[...q.data.details].reverse().map(d => (
                  <tr key={d.id}>
                    <td><strong>{d.ticker}</strong></td>
                    <td style={{ fontSize: 11 }}>{d.entry_date}</td>
                    <td style={{ fontSize: 11 }}>{d.exit_date}</td>
                    <td>
                      <span style={{ fontSize: 10, fontWeight: 600 }}>{d.recommendation}</span>
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'monospace', fontSize: 11 }}>R$ {d.entry_price.toFixed(2)}</td>
                    <td style={{ textAlign: 'right', fontFamily: 'monospace', fontSize: 11 }}>R$ {d.exit_price.toFixed(2)}</td>
                    <td style={{ textAlign: 'right', color: moveColor(d.move_pct), fontWeight: 600 }}>
                      {d.move_pct >= 0 ? '+' : ''}{d.move_pct.toFixed(2)}%
                    </td>
                    <td style={{ textAlign: 'center' }}>
                      {d.result === 'hit'
                        ? <span style={{ color: 'var(--green)', fontWeight: 700 }}>✓ HIT</span>
                        : <span style={{ color: 'var(--red)', fontWeight: 700 }}>✗ MISS</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
