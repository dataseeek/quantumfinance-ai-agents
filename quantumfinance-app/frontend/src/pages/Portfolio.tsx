import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { api } from '../api'
import type { Portfolio as PT } from '../api'

export default function Portfolio() {
  const portfolios = useQuery({
    queryKey: ['portfolios'],
    queryFn: async () => (await api.get<PT[]>('/portfolios')).data,
    refetchInterval: 30_000,
  })

  const p = portfolios.data?.[0]
  const [ticker, setTicker] = useState('VALE3')
  const [side, setSide] = useState<'BUY'|'SELL'>('BUY')
  const [qty, setQty] = useState(100)

  const place = useMutation({
    mutationFn: async () => (await api.post(`/portfolios/${p!.id}/orders`, { ticker, side, quantity: qty })).data,
    onSuccess: () => portfolios.refetch(),
  })

  return (
    <div>
      <h1 style={{ fontSize: 22, marginBottom: 16 }}>Portfolio (Paper Trading)</h1>
      {!p ? <p>Loading...</p> : (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 16 }}>
          <div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 16 }}>
              <div className="card">
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>Cash</div>
                <div style={{ fontSize: 20, fontWeight: 700 }}>R$ {p.cash.toLocaleString('pt-BR', { maximumFractionDigits: 2 })}</div>
              </div>
              <div className="card">
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>Equity</div>
                <div style={{ fontSize: 20, fontWeight: 700 }}>R$ {p.equity.toLocaleString('pt-BR', { maximumFractionDigits: 2 })}</div>
              </div>
              <div className="card">
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>P&L</div>
                <div style={{ fontSize: 20, fontWeight: 700, color: p.total_pnl >= 0 ? 'var(--green)' : 'var(--red)' }}>
                  R$ {p.total_pnl.toLocaleString('pt-BR', { maximumFractionDigits: 2 })}
                </div>
              </div>
              <div className="card">
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>P&L %</div>
                <div style={{ fontSize: 20, fontWeight: 700, color: p.total_pnl_pct >= 0 ? 'var(--green)' : 'var(--red)' }}>
                  {p.total_pnl_pct.toFixed(2)}%
                </div>
              </div>
            </div>

            <div className="card">
              <h3 style={{ fontSize: 14, marginBottom: 12 }}>Posições</h3>
              {p.positions.length === 0 && <p style={{ color: 'var(--text-muted)', fontSize: 12 }}>Sem posições. Compre algo!</p>}
              {p.positions.length > 0 && (
                <table>
                  <thead><tr><th>Ticker</th><th>Qty</th><th>Avg</th><th>Last</th><th>MV</th><th>P&L</th><th>%</th></tr></thead>
                  <tbody>
                    {p.positions.map(pos => (
                      <tr key={pos.ticker}>
                        <td style={{ fontFamily: 'monospace', fontWeight: 600 }}>{pos.ticker}</td>
                        <td>{pos.quantity}</td>
                        <td>R$ {pos.avg_price.toFixed(2)}</td>
                        <td>R$ {pos.last_price.toFixed(2)}</td>
                        <td>R$ {pos.market_value.toLocaleString('pt-BR', { maximumFractionDigits: 2 })}</td>
                        <td style={{ color: pos.pnl >= 0 ? 'var(--green)' : 'var(--red)' }}>R$ {pos.pnl.toFixed(2)}</td>
                        <td style={{ color: pos.pnl_pct >= 0 ? 'var(--green)' : 'var(--red)' }}>{pos.pnl_pct.toFixed(2)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>

          <div className="card">
            <h3 style={{ fontSize: 14, marginBottom: 12 }}>Nova ordem</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <select value={ticker} onChange={e => setTicker(e.target.value)}>
                {['VALE3','PETR4','BBAS3','ITUB4'].map(t => <option key={t}>{t}</option>)}
              </select>
              <select value={side} onChange={e => setSide(e.target.value as 'BUY'|'SELL')}>
                <option value="BUY">COMPRAR</option>
                <option value="SELL">VENDER</option>
              </select>
              <input type="number" min={1} value={qty} onChange={e => setQty(parseInt(e.target.value) || 0)} placeholder="Quantidade" />
              <button onClick={() => place.mutate()} disabled={place.isPending} className="btn-primary">
                {place.isPending ? 'Enviando…' : `${side === 'BUY' ? 'Comprar' : 'Vender'} ${qty} ${ticker}`}
              </button>
              {place.isError && <p style={{ color: 'var(--red)', fontSize: 12 }}>{(place.error as any)?.response?.data?.detail || 'Erro'}</p>}
              {place.isSuccess && <p style={{ color: 'var(--green)', fontSize: 12 }}>Ordem executada!</p>}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
