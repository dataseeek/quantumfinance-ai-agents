import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { api } from '../api'
import { useToast, errorMessage } from '../components/Toast'

type Msg = { role: 'user' | 'assistant' | 'system'; content: string; agent?: string; streaming?: boolean }
type Session = { id: number; started_at: string; preview: string; message_count: number }

const TARGET_HINT = (
  'Quem responde:\n' +
  '• Crew completo — Pipeline multi-agente (notícias + técnico + estrategista) que produz uma recomendação oficial COMPRAR/VENDER/AGUARDAR. Requer um ticker.\n' +
  '• Single-agent (News/Technical/Strategist/CVM RI) — Pergunta direta a um agente, com streaming token-a-token. Cite o ticker na mensagem se quiser falar de uma ação específica.'
)

const TICKER_HINT = (
  'Sobre qual ação o crew vai trabalhar.\n' +
  'Dica: se você esquecer de mudar aqui, o sistema lê sua mensagem e detecta o ticker automaticamente — basta citar VALE3 / Petrobras / Itaú / Banco do Brasil.'
)

function Hint({ text }: { text: string }) {
  return (
    <span
      title={text}
      aria-label={text}
      style={{
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        width: 14, height: 14, borderRadius: '50%',
        border: '1px solid var(--text-muted)', color: 'var(--text-muted)',
        fontSize: 9, fontWeight: 700, cursor: 'help', userSelect: 'none',
        marginLeft: -4,
      }}
    >?</span>
  )
}

export default function Chat() {
  const toast = useToast()
  const [messages, setMessages] = useState<Msg[]>([])
  const [input, setInput] = useState('')
  const [target, setTarget] = useState<string>('crew')
  const [ticker, setTicker] = useState<string>('PETR4')
  const [connected, setConnected] = useState(false)
  const [thinking, setThinking] = useState(false)
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  const sessions = useQuery({
    queryKey: ['chat-sessions'],
    queryFn: async () => (await api.get<Session[]>('/chat-sessions')).data,
    refetchInterval: 5000,
  })

  const deleteSession = useMutation({
    mutationFn: async (sessionId: number) =>
      (await api.delete<{ ok: boolean; deleted_messages: number }>(`/chat-sessions/${sessionId}`)).data,
    onSuccess: (data, sessionId) => {
      sessions.refetch()
      if (activeSessionId === sessionId) {
        setActiveSessionId(null)
        setMessages([])
      }
      toast.push('success', `Sessão #${sessionId} apagada (${data.deleted_messages} mensagens).`)
    },
    onError: (e) => toast.push('error', `Falha ao apagar sessão: ${errorMessage(e)}`),
  })

  useEffect(() => {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${proto}://${location.host}/api/chat`)
    wsRef.current = ws
    ws.onopen = () => setConnected(true)
    ws.onclose = () => setConnected(false)
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data)
      if (data.type === 'session') {
        setActiveSessionId(data.session_id)
        return
      }
      if (data.type === 'thinking') {
        setThinking(true)
        return
      }
      if (data.type === 'chunk') {
        // Streaming token from single-agent reply: append to (or create) last assistant message.
        setThinking(false)
        setMessages(prev => {
          const last = prev[prev.length - 1]
          if (last && last.role === 'assistant' && last.streaming) {
            const updated = [...prev]
            updated[updated.length - 1] = { ...last, content: last.content + data.delta }
            return updated
          }
          return [...prev, { role: 'assistant', content: data.delta, agent: data.agent, streaming: true }]
        })
        return
      }
      if (data.type === 'done') {
        // End of stream — close the streaming assistant message.
        setMessages(prev => {
          const last = prev[prev.length - 1]
          if (last && last.role === 'assistant' && last.streaming) {
            const updated = [...prev]
            updated[updated.length - 1] = { ...last, streaming: false }
            return updated
          }
          return prev
        })
        return
      }
      if (data.type === 'message') {
        // Crew path: full message arrives in one shot (no token streaming).
        setThinking(false)
        setMessages(prev => [...prev, { role: 'assistant', content: data.content, agent: data.agent }])
        return
      }
      if (data.type === 'auto_ticker') {
        // Backend detected a ticker in the message different from the dropdown.
        // Show a discreet system note and sync the dropdown so the next turn
        // stays on the detected ticker.
        setTicker(data.to)
        setMessages(prev => [...prev, {
          role: 'system',
          content: `🎯 Detectei "${data.to}" na sua mensagem (dropdown estava em ${data.from}). Trocando para ${data.to}.`,
        }])
        return
      }
      if (data.type === 'error') {
        setThinking(false)
        setMessages(prev => [...prev, { role: 'system', content: `Erro: ${data.error}` }])
        return
      }
    }
    return () => ws.close()
  }, [])

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, thinking])

  const send = () => {
    if (!input.trim() || !wsRef.current) return
    const msg = { content: input, target, ticker: target === 'crew' ? ticker : undefined }
    wsRef.current.send(JSON.stringify(msg))
    setMessages(prev => [...prev, { role: 'user', content: input }])
    setInput('')
  }

  const restoreSession = async (sessionId: number) => {
    try {
      const r = await api.get<Array<{ role: string; content: string; agent_name: string | null }>>(`/chat-sessions/${sessionId}/messages`)
      setMessages(r.data.map(m => ({ role: m.role as Msg['role'], content: m.content, agent: m.agent_name || undefined })))
      setActiveSessionId(sessionId)
    } catch (e) { /* ignore */ }
  }

  const quickPrompts = [
    'Por que VALE3 está com AGUARDAR?',
    'Compare PETR4 e BBAS3 do ponto de vista técnico.',
    'Qual o último fato relevante de Vale?',
    'O que dizem as notícias sobre Itaú esta semana?',
  ]

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '240px 1fr', gap: 12, height: 'calc(100vh - 48px)' }}>
      <div className="card" style={{ overflow: 'auto', display: 'flex', flexDirection: 'column' }}>
        <h3 style={{ fontSize: 13, marginBottom: 8 }}>Sessões anteriores</h3>
        {sessions.data?.length === 0 && <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>(nenhuma ainda)</p>}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {sessions.data?.map(s => {
            const pending = deleteSession.isPending && deleteSession.variables === s.id
            return (
              <div
                key={s.id}
                style={{
                  display: 'grid', gridTemplateColumns: '1fr auto', gap: 4, alignItems: 'stretch',
                  background: activeSessionId === s.id ? 'rgba(233,30,99,0.12)' : 'var(--bg-elevated)',
                  borderLeft: activeSessionId === s.id ? '2px solid var(--pink)' : '1px solid var(--border)',
                  borderRadius: 4,
                }}
              >
                <button
                  onClick={() => restoreSession(s.id)}
                  className="btn-secondary"
                  style={{
                    fontSize: 11, textAlign: 'left', padding: '6px 8px',
                    background: 'transparent', border: 0, borderRadius: 0,
                  }}
                >
                  <div style={{ fontWeight: 600, color: 'var(--text)' }}>#{s.id} · {s.message_count} msgs</div>
                  <div style={{ color: 'var(--text-muted)', fontSize: 10 }}>{s.preview}</div>
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    if (confirm(`Apagar sessão #${s.id} (${s.message_count} mensagens)?`)) {
                      deleteSession.mutate(s.id)
                    }
                  }}
                  disabled={pending}
                  title="Apagar sessão"
                  aria-label={`Apagar sessão ${s.id}`}
                  style={{
                    background: 'transparent', border: 0, color: 'var(--text-muted)',
                    cursor: pending ? 'wait' : 'pointer', padding: '0 8px', fontSize: 14,
                  }}
                >
                  {pending ? '…' : '×'}
                </button>
              </div>
            )
          })}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateRows: 'auto 1fr auto', gap: 12, minHeight: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <h1 style={{ fontSize: 22 }}>Chat com Agentes</h1>
          <span style={{ fontSize: 11, color: connected ? 'var(--green)' : 'var(--red)' }}>
            ● {connected ? 'conectado' : 'desconectado'}
          </span>
          <select value={target} onChange={e => setTarget(e.target.value)}>
            <option value="crew">Crew completo</option>
            <option value="news_analyst">News Analyst</option>
            <option value="technical_analyst">Technical Analyst</option>
            <option value="investment_strategist">Investment Strategist</option>
            <option value="cvm_ri_analyst">CVM RI Analyst</option>
          </select>
          <Hint text={TARGET_HINT} />
          {target === 'crew' && (
            <>
              <select value={ticker} onChange={e => setTicker(e.target.value)}>
                {['VALE3','PETR4','BBAS3','ITUB4'].map(t => <option key={t}>{t}</option>)}
              </select>
              <Hint text={TICKER_HINT} />
            </>
          )}
        </div>

        <div className="card" style={{ overflow: 'auto', minHeight: 0 }}>
          {messages.length === 0 && (
            <div>
              <p style={{ color: 'var(--text-muted)', marginBottom: 12 }}>Prompts rápidos:</p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {quickPrompts.map(p => (
                  <button key={p} className="btn-secondary" onClick={() => setInput(p)} style={{ fontSize: 12 }}>{p}</button>
                ))}
              </div>
            </div>
          )}
          {messages.map((m, i) => {
            if (m.role === 'system') {
              return (
                <div key={i} style={{
                  marginBottom: 12, padding: '6px 12px', borderRadius: 6,
                  background: 'rgba(255,193,7,0.10)', borderLeft: '3px solid #ffa726',
                  fontSize: 12, color: 'var(--text-muted)',
                }}>
                  {m.content}
                </div>
              )
            }
            return (
              <div key={i} style={{
                marginBottom: 12, padding: 12, borderRadius: 8,
                background: m.role === 'user' ? 'rgba(66,165,245,0.12)' : 'var(--bg-elevated)',
                borderLeft: `3px solid ${m.role === 'user' ? 'var(--blue)' : 'var(--pink)'}`,
              }}>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>
                  {m.role === 'user' ? 'Você' : (m.agent || 'assistant')}
                  {m.streaming && <span style={{ marginLeft: 6, color: 'var(--pink)' }}>▍</span>}
                </div>
                <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', fontSize: 13, margin: 0 }}>{m.content}</pre>
              </div>
            )
          })}
          {thinking && <p style={{ color: 'var(--text-muted)', fontSize: 12 }}>🧠 pensando…</p>}
          <div ref={bottomRef} />
        </div>

        <div style={{ display: 'flex', gap: 8 }}>
          <input
            value={input} onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && send()}
            placeholder="Pergunte aos agentes…"
            style={{ flex: 1 }}
          />
          <button onClick={send} disabled={!connected || thinking} className="btn-primary">Enviar</button>
        </div>
      </div>
    </div>
  )
}
