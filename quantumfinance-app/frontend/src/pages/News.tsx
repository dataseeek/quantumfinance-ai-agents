import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { api } from '../api'
import type { NewsItem, Ticker } from '../api'
import { useToast, errorMessage } from '../components/Toast'

export default function News() {
  const toast = useToast()
  const [ticker, setTicker] = useState('VALE3')

  const tickers = useQuery({
    queryKey: ['tickers'],
    queryFn: async () => (await api.get<Ticker[]>('/tickers')).data,
  })

  const news = useQuery({
    queryKey: ['news', ticker],
    queryFn: async () => (await api.get<NewsItem[]>(`/news/${ticker}`)).data,
  })

  const ingest = useMutation({
    mutationFn: async () => (await api.post(`/news/${ticker}/ingest`)).data,
    onSuccess: (data: any) => {
      news.refetch()
      toast.push('success', `${ticker}: ${data?.total_in_db ?? 0} notícias no DB.`)
    },
    onError: (e) => toast.push('error', `Ingestão de notícias falhou: ${errorMessage(e)}`),
  })

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
        <h1 style={{ fontSize: 22 }}>Notícias</h1>
        <select value={ticker} onChange={e => setTicker(e.target.value)}>
          {tickers.data?.map(t => <option key={t.symbol} value={t.symbol}>{t.symbol} · {t.name}</option>)}
        </select>
        <button onClick={() => ingest.mutate()} disabled={ingest.isPending} className="btn-secondary">
          {ingest.isPending ? 'Ingerindo…' : 'Ingerir agora'}
        </button>
      </div>

      <div className="card">
        {news.isLoading && <p style={{ color: 'var(--text-muted)' }}>Loading...</p>}
        {news.data?.length === 0 && <p style={{ color: 'var(--text-muted)' }}>Nenhuma notícia. Clique em "Ingerir agora".</p>}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {news.data?.map(n => (
            <div key={n.id} style={{ paddingBottom: 12, borderBottom: '1px solid var(--border)' }}>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>
                <span style={{ background: 'var(--bg-elevated)', padding: '2px 8px', borderRadius: 4 }}>{n.source}</span>
                {' · '}{n.published_at?.slice(0, 10) ?? '—'}
              </div>
              <a href={n.url} target="_blank" rel="noreferrer" style={{ fontSize: 14 }}>{n.title}</a>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
