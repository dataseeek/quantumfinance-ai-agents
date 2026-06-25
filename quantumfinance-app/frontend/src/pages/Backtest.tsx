import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api'
import EquityChart, { type EquityPoint } from '../components/EquityChart'

type BacktestSummary = {
  ticker: string
  period: string
  initial_cash: number
  start_date: string
  end_date: string
  days: number
  first_price: number
  last_price: number
  agent_return_pct: number
  bh_return_pct: number
  delta_pp: number
  n_buys: number
  n_sells: number
  n_holds: number
  final_position: string
}

type BacktestDetail = BacktestSummary & { curve: (EquityPoint & { price: number; signal: string })[] }

const PERIODS = ['1mo', '3mo', '6mo', '1y', '2y'] as const

function pctColor(v: number): string {
  if (v > 0.5) return 'var(--green)'
  if (v < -0.5) return 'var(--red)'
  return 'var(--text-muted)'
}

export default function Backtest() {
  const [period, setPeriod] = useState<typeof PERIODS[number]>('6mo')
  const [selected, setSelected] = useState<string>('VALE3')

  const all = useQuery({
    queryKey: ['backtest', 'all', period],
    queryFn: async () => (await api.get<BacktestSummary[]>(`/backtest?period=${period}`)).data,
  })

  const detail = useQuery({
    queryKey: ['backtest', selected, period],
    queryFn: async () => (await api.get<BacktestDetail>(`/backtest/${selected}?period=${period}`)).data,
  })

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
        <h1 style={{ fontSize: 22 }}>Backtest · Agente vs Buy &amp; Hold</h1>
        <select value={period} onChange={e => setPeriod(e.target.value as typeof PERIODS[number])}>
          {PERIODS.map(p => <option key={p} value={p}>{p}</option>)}
        </select>
        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
          Capital inicial: R$ 10.000 · Estratégia: MACD-cross + RSI (heurística determinística)
        </span>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ fontSize: 14, marginBottom: 12 }}>Resumo</h3>
        {all.isLoading && <p style={{ color: 'var(--text-muted)' }}>Carregando…</p>}
        {all.isError && <p style={{ color: 'var(--red)' }}>Falha ao carregar backtest.</p>}
        {all.data && (
          <table>
            <thead>
              <tr>
                <th>Ticker</th>
                <th style={{ textAlign: 'right' }}>Período</th>
                <th style={{ textAlign: 'right' }}>Agente</th>
                <th style={{ textAlign: 'right' }}>B&amp;H</th>
                <th style={{ textAlign: 'right' }}>Δ (p.p.)</th>
                <th style={{ textAlign: 'right' }}>Trades (B/S/H)</th>
                <th style={{ textAlign: 'right' }}>Pos. final</th>
              </tr>
            </thead>
            <tbody>
              {all.data.map(r => (
                <tr
                  key={r.ticker}
                  onClick={() => setSelected(r.ticker)}
                  style={{
                    cursor: 'pointer',
                    background: selected === r.ticker ? 'rgba(233,30,99,0.10)' : 'transparent',
                  }}
                >
                  <td><strong>{r.ticker}</strong></td>
                  <td style={{ textAlign: 'right', fontSize: 11, color: 'var(--text-muted)' }}>
                    {r.start_date.slice(5)} → {r.end_date.slice(5)} · {r.days}d
                  </td>
                  <td style={{ textAlign: 'right', color: pctColor(r.agent_return_pct), fontVariantNumeric: 'tabular-nums' }}>
                    {r.agent_return_pct >= 0 ? '+' : ''}{r.agent_return_pct.toFixed(2)}%
                  </td>
                  <td style={{ textAlign: 'right', color: pctColor(r.bh_return_pct), fontVariantNumeric: 'tabular-nums' }}>
                    {r.bh_return_pct >= 0 ? '+' : ''}{r.bh_return_pct.toFixed(2)}%
                  </td>
                  <td style={{ textAlign: 'right', color: pctColor(r.delta_pp), fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>
                    {r.delta_pp >= 0 ? '+' : ''}{r.delta_pp.toFixed(2)}
                  </td>
                  <td style={{ textAlign: 'right', fontSize: 11, color: 'var(--text-muted)' }}>
                    {r.n_buys}/{r.n_sells}/{r.n_holds}
                  </td>
                  <td style={{ textAlign: 'right', fontSize: 11 }}>
                    {r.final_position === 'shares' ? '📈 ações' : '💵 caixa'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="card">
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, marginBottom: 12 }}>
          <h3 style={{ fontSize: 14 }}>Curva de equity · {selected}</h3>
          {detail.data && (
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              {detail.data.start_date} → {detail.data.end_date} ({detail.data.days} dias)
            </span>
          )}
        </div>
        {detail.isLoading && <p style={{ color: 'var(--text-muted)' }}>Carregando curva…</p>}
        {detail.data && !detail.data.curve && (
          <p style={{ color: 'var(--red)' }}>Sem dados de curva. {(detail.data as any).error}</p>
        )}
        {detail.data?.curve && (
          <>
            <EquityChart data={detail.data.curve} height={320} />
            <div style={{ display: 'flex', gap: 16, marginTop: 8, fontSize: 11, color: 'var(--text-muted)' }}>
              <span><span style={{ color: '#e91e63' }}>●</span> Agente · final R$ {detail.data.curve.at(-1)?.agent_equity.toFixed(2)}</span>
              <span><span style={{ color: '#42a5f5' }}>●</span> Buy &amp; Hold · final R$ {detail.data.curve.at(-1)?.bh_equity.toFixed(2)}</span>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
