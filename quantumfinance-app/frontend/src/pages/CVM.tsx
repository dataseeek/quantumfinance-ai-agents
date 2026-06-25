import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api'
import type { CvmFiling, Ticker } from '../api'

export default function CVM() {
  const [ticker, setTicker] = useState('VALE3')
  const [refresh, setRefresh] = useState(false)

  const tickers = useQuery({
    queryKey: ['tickers'],
    queryFn: async () => (await api.get<Ticker[]>('/tickers')).data,
  })

  const filings = useQuery({
    queryKey: ['cvm', ticker, refresh],
    queryFn: async () => (await api.get<CvmFiling[]>(`/cvm/${ticker}/filings`, { params: { refresh } })).data,
  })

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
        <h1 style={{ fontSize: 22 }}>CVM — Relações com Investidores</h1>
        <select value={ticker} onChange={e => setTicker(e.target.value)}>
          {tickers.data?.map(t => <option key={t.symbol} value={t.symbol}>{t.symbol} · {t.name}</option>)}
        </select>
        <button onClick={() => { setRefresh(true); setTimeout(() => setRefresh(false), 100) }} className="btn-secondary">
          Atualizar via CVM
        </button>
      </div>

      <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 12 }}>
        Fatos relevantes, comunicados ao mercado e avisos oficiais registrados na CVM via portal de Dados Abertos (IPE).
      </p>

      <div className="card">
        {filings.isLoading && <p style={{ color: 'var(--text-muted)' }}>Loading...</p>}
        {filings.data?.length === 0 && (
          <p style={{ color: 'var(--text-muted)' }}>
            Nenhum comunicado cacheado. Clique em "Atualizar via CVM" para baixar o IPE atual.
          </p>
        )}
        <table>
          <thead>
            <tr><th>Data</th><th>Categoria</th><th>Título</th><th></th></tr>
          </thead>
          <tbody>
            {filings.data?.map(f => (
              <tr key={f.id}>
                <td style={{ fontFamily: 'monospace', whiteSpace: 'nowrap' }}>{f.filed_at?.slice(0, 10) ?? '—'}</td>
                <td><span className="pill" style={{ background: 'var(--bg-elevated)', color: 'var(--text)' }}>{f.category}</span></td>
                <td>{f.title}</td>
                <td>{f.link && <a href={f.link} target="_blank" rel="noreferrer">PDF</a>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
