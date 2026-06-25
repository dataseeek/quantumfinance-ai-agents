import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { api } from '../api'
import type { Agent } from '../api'

type FormState = {
  name: string
  role: string
  goal: string
  backstory: string
  tool_names: string[]
  max_iter: number
}

const emptyForm: FormState = { name: '', role: '', goal: '', backstory: '', tool_names: [], max_iter: 4 }

export default function Agents() {
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form, setForm] = useState<FormState>(emptyForm)
  const [testOutput, setTestOutput] = useState<{ agentName: string; output: string } | null>(null)

  const agents = useQuery({
    queryKey: ['agents'],
    queryFn: async () => (await api.get<Agent[]>('/agents')).data,
  })
  const tools = useQuery({
    queryKey: ['tools'],
    queryFn: async () => (await api.get<string[]>('/agents/tools')).data,
  })

  const reset = () => { setShowForm(false); setEditingId(null); setForm(emptyForm) }

  const create = useMutation({
    mutationFn: async () => (await api.post('/agents', form)).data,
    onSuccess: () => { reset(); agents.refetch() },
  })
  const update = useMutation({
    mutationFn: async () => (await api.put(`/agents/${editingId}`, form)).data,
    onSuccess: () => { reset(); agents.refetch() },
  })
  const remove = useMutation({
    mutationFn: async (id: number) => (await api.delete(`/agents/${id}`)).data,
    onSuccess: () => agents.refetch(),
  })
  const testAgent = useMutation({
    mutationFn: async ({ id, ticker }: { id: number; ticker: string }) =>
      (await api.post<{ agent: string; output?: string; error?: string }>(`/agents/${id}/test`, { ticker })).data,
    onSuccess: (data) => setTestOutput({ agentName: data.agent, output: data.output || data.error || '(no output)' }),
  })

  const startEdit = (a: Agent) => {
    setEditingId(a.id)
    setForm({
      name: a.name, role: a.role, goal: a.goal, backstory: a.backstory,
      tool_names: a.tool_names, max_iter: a.max_iter,
    })
    setShowForm(true)
  }

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
        <h1 style={{ fontSize: 22 }}>Agentes</h1>
        <button onClick={() => { reset(); setShowForm(s => !s) }} className="btn-primary">
          {showForm && !editingId ? 'Cancelar' : '+ Novo agente'}
        </button>
      </div>

      {showForm && (
        <div className="card" style={{ marginBottom: 16 }}>
          <h3 style={{ marginBottom: 12, fontSize: 14 }}>{editingId ? `Editar agente #${editingId}` : 'Novo agente custom'}</h3>
          <div style={{ display: 'grid', gap: 10 }}>
            <input placeholder="name (slug, ex: macro_analyst)" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} disabled={!!editingId} />
            <input placeholder="role (ex: Analista de Macroeconomia)" value={form.role} onChange={e => setForm({ ...form, role: e.target.value })} />
            <textarea placeholder="goal (use {ticker} para parametrizar)" value={form.goal} onChange={e => setForm({ ...form, goal: e.target.value })} rows={2} />
            <textarea placeholder="backstory (background do agente)" value={form.backstory} onChange={e => setForm({ ...form, backstory: e.target.value })} rows={3} />
            <div>
              <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>Tools:</p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {tools.data?.map(t => (
                  <label key={t} style={{ fontSize: 12, display: 'flex', gap: 4, alignItems: 'center', cursor: 'pointer' }}>
                    <input type="checkbox" checked={form.tool_names.includes(t)} onChange={e => {
                      setForm(f => ({
                        ...f,
                        tool_names: e.target.checked ? [...f.tool_names, t] : f.tool_names.filter(x => x !== t),
                      }))
                    }} />
                    {t}
                  </label>
                ))}
              </div>
            </div>
            <input type="number" min={1} max={10} value={form.max_iter} onChange={e => setForm({ ...form, max_iter: parseInt(e.target.value) })} placeholder="max_iter" />
            <div style={{ display: 'flex', gap: 8 }}>
              {editingId
                ? <button onClick={() => update.mutate()} className="btn-primary">{update.isPending ? 'Salvando…' : 'Salvar alterações'}</button>
                : <button onClick={() => create.mutate()} className="btn-primary">{create.isPending ? 'Criando…' : 'Criar agente'}</button>}
              <button onClick={reset} className="btn-secondary">Cancelar</button>
            </div>
            {(create.isError || update.isError) && <p style={{ color: 'var(--red)', fontSize: 12 }}>{((create.error || update.error) as any)?.response?.data?.detail || 'Erro'}</p>}
          </div>
        </div>
      )}

      {testOutput && (
        <div className="card" style={{ marginBottom: 16, borderLeft: '4px solid var(--blue)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
            <h3 style={{ fontSize: 14 }}>Test output · {testOutput.agentName}</h3>
            <button onClick={() => setTestOutput(null)} className="btn-secondary" style={{ fontSize: 12 }}>Fechar</button>
          </div>
          <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', fontSize: 12, margin: 0, color: 'var(--text-muted)' }}>
            {testOutput.output}
          </pre>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 12 }}>
        {agents.data?.map(a => (
          <div key={a.id} className="card" style={{ borderLeft: `3px solid ${a.is_system ? 'var(--pink)' : 'var(--blue)'}` }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 4 }}>
              <h3 style={{ fontSize: 14 }}>{a.name}</h3>
              {a.is_system
                ? <span className="pill" style={{ background: 'rgba(233,30,99,0.18)', color: 'var(--pink)' }}>system</span>
                : <span className="pill" style={{ background: 'rgba(66,165,245,0.18)', color: 'var(--blue)' }}>custom</span>}
            </div>
            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>{a.role}</p>
            <p style={{ fontSize: 12, marginBottom: 8 }}>{a.goal}</p>
            <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8 }}>tools: {a.tool_names.join(', ') || '—'}</p>
            <div style={{ display: 'flex', gap: 6 }}>
              <button onClick={() => testAgent.mutate({ id: a.id, ticker: 'PETR4' })} className="btn-secondary" style={{ fontSize: 12 }}>
                {testAgent.isPending && testAgent.variables?.id === a.id ? 'Testando…' : 'Test'}
              </button>
              {!a.is_system && (
                <>
                  <button onClick={() => startEdit(a)} className="btn-secondary" style={{ fontSize: 12 }}>Editar</button>
                  <button onClick={() => remove.mutate(a.id)} className="btn-secondary" style={{ fontSize: 12 }}>Deletar</button>
                </>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
