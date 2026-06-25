import { useEffect, useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { api } from '../api'
import type { Ticker, ChartData, Recommendation, SwingPlan } from '../api'
import CandlestickChart from '../components/CandlestickChart'
import RecPill from '../components/RecPill'
import { useToast, errorMessage } from '../components/Toast'

const REASONING_COLLAPSED_LEN = 280

export default function Dashboard() {
  const toast = useToast()
  const [selected, setSelected] = useState<string>('VALE3')
  const [reasoningExpanded, setReasoningExpanded] = useState(false)

  const tickers = useQuery({
    queryKey: ['tickers'],
    queryFn: async () => (await api.get<Ticker[]>('/tickers')).data,
    refetchInterval: 60_000,
  })

  const chart = useQuery({
    queryKey: ['chart', selected],
    queryFn: async () => (await api.get<ChartData>(`/chart/${selected}`)).data,
  })

  const latestRec = useQuery({
    queryKey: ['rec', selected],
    queryFn: async () => (await api.get<Recommendation | null>(`/recommendations/${selected}/latest`)).data,
  })
  useEffect(() => { setReasoningExpanded(false) }, [selected])

  const swing = useQuery({
    queryKey: ['swing', selected],
    queryFn: async () => (await api.get<SwingPlan>(`/recommendations/${selected}/swing-plan`)).data,
  })

  const runCrew = useMutation({
    mutationFn: async () => (await api.post('/recommendations/run', { ticker: selected })).data,
    onSuccess: (data: any) => {
      latestRec.refetch(); swing.refetch()
      toast.push('success', `${selected}: ${data?.recommendation ?? 'rec atualizada'}`)
    },
    onError: (e) => toast.push('error', `Crew falhou para ${selected}: ${errorMessage(e)}`),
  })

  return (
    <div>
      <h1 style={{ fontSize: 22, marginBottom: 16 }}>Dashboard</h1>
      <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr 320px', gap: 16 }}>
        {/* Watchlist */}
        <div className="card">
          <h3 style={{ marginBottom: 12, fontSize: 14 }}>Watchlist</h3>
          {tickers.isLoading && <p style={{ color: 'var(--text-muted)' }}>Loading...</p>}
          {tickers.data?.map(t => (
            <div
              key={t.symbol}
              onClick={() => setSelected(t.symbol)}
              style={{
                display: 'grid', gridTemplateColumns: '1fr auto auto', gap: 8,
                padding: '10px 8px', borderRadius: 6, cursor: 'pointer',
                background: selected === t.symbol ? 'rgba(233,30,99,0.1)' : 'transparent',
                borderBottom: '1px solid var(--border)',
                alignItems: 'center',
              }}
            >
              <div>
                <div style={{ fontWeight: 600, fontFamily: 'monospace' }}>{t.symbol}</div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{t.name}</div>
              </div>
              <div style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
                R$ {t.last?.toFixed(2) ?? '—'}
              </div>
              <div
                style={{
                  textAlign: 'right', fontSize: 12,
                  color: (t.change_pct ?? 0) >= 0 ? 'var(--green)' : 'var(--red)',
                  fontVariantNumeric: 'tabular-nums',
                }}
              >
                {t.change_pct != null ? `${t.change_pct >= 0 ? '+' : ''}${t.change_pct.toFixed(2)}%` : '—'}
              </div>
            </div>
          ))}
        </div>

        {/* Chart */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <h2 style={{ fontSize: 18 }}>{selected}</h2>
            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              RSI {chart.data?.indicators.rsi.toFixed(1)} · MACD {chart.data?.indicators.macd.toFixed(3)} · SMA20 {chart.data?.indicators.sma20.toFixed(2)}
            </div>
          </div>
          <CandlestickChart data={chart.data} />
        </div>

        {/* Recs + Swing */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div className="card">
            <h3 style={{ marginBottom: 12, fontSize: 14 }}>Última recomendação</h3>
            {latestRec.data ? (
              <>
                <div style={{ marginBottom: 8 }}>
                  <RecPill rec={latestRec.data.recommendation} />
                  <span style={{ marginLeft: 8, fontSize: 11, color: 'var(--text-muted)' }}>
                    {latestRec.data.date.split('T')[0]}
                  </span>
                </div>
                {(() => {
                  const full = latestRec.data.reasoning ?? ''
                  const needsToggle = full.length > REASONING_COLLAPSED_LEN
                  const shown = reasoningExpanded || !needsToggle
                    ? full
                    : full.slice(0, REASONING_COLLAPSED_LEN) + '…'
                  return (
                    <>
                      <p
                        style={{
                          fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.5,
                          whiteSpace: 'pre-wrap',
                          maxHeight: reasoningExpanded ? 320 : undefined,
                          overflowY: reasoningExpanded ? 'auto' : undefined,
                        }}
                      >
                        {shown}
                      </p>
                      {needsToggle && (
                        <button
                          onClick={() => setReasoningExpanded(v => !v)}
                          style={{
                            background: 'transparent', border: 0, padding: '4px 0',
                            color: 'var(--pink)', cursor: 'pointer', fontSize: 12,
                            fontWeight: 600,
                          }}
                          aria-expanded={reasoningExpanded}
                        >
                          {reasoningExpanded ? '↑ Ler menos' : '↓ Ler mais'}
                        </button>
                      )}
                    </>
                  )
                })()}
              </>
            ) : (
              <p style={{ color: 'var(--text-muted)', fontSize: 12 }}>Nenhuma rec ainda.</p>
            )}
            <button
              onClick={() => runCrew.mutate()}
              disabled={runCrew.isPending}
              className="btn-primary"
              style={{ marginTop: 12, width: '100%' }}
            >
              {runCrew.isPending ? 'Rodando crew…' : 'Rodar crew agora'}
            </button>
          </div>

          {swing.data && swing.data.support && (
            <div className="card">
              <h3 style={{ marginBottom: 12, fontSize: 14 }}>Swing Trade Plan</h3>
              <table>
                <tbody>
                  <tr><td>Preço</td><td style={{ textAlign: 'right', fontFamily: 'monospace' }}>R$ {swing.data.price.toFixed(2)}</td></tr>
                  <tr><td>Suporte (Fib)</td><td style={{ textAlign: 'right', fontFamily: 'monospace' }}>{swing.data.support.label} R$ {swing.data.support.value?.toFixed(2)}</td></tr>
                  <tr><td>Resistência (Fib)</td><td style={{ textAlign: 'right', fontFamily: 'monospace' }}>{swing.data.resistance.label} R$ {swing.data.resistance.value?.toFixed(2)}</td></tr>
                  <tr><td>ATR%</td><td style={{ textAlign: 'right' }}>{swing.data.atr_pct.toFixed(2)}%</td></tr>
                  <tr><td>Holding</td><td style={{ textAlign: 'right' }}>{swing.data.holding}</td></tr>
                  <tr><td>Sinais (B/S)</td><td style={{ textAlign: 'right' }}>{swing.data.signals.buy}/{swing.data.signals.sell}</td></tr>
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
