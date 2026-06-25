import { useState, useEffect } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { api } from '../api'
import { useToast, errorMessage } from '../components/Toast'

export default function Settings() {
  const toast = useToast()
  const settings = useQuery({
    queryKey: ['settings'],
    queryFn: async () => (await api.get<Record<string, any>>('/settings')).data,
  })

  const jobs = useQuery({
    queryKey: ['scheduler-jobs'],
    queryFn: async () => (await api.get<any[]>('/scheduler/jobs')).data,
  })

  const [draft, setDraft] = useState<Record<string, any>>({})
  useEffect(() => { if (settings.data) setDraft(settings.data) }, [settings.data])

  const update = useMutation({
    mutationFn: async ({ key, value }: { key: string, value: any }) =>
      (await api.put(`/settings/${key}`, { value })).data,
    onSuccess: (_, vars) => { settings.refetch(); toast.push('success', `${vars.key} salvo.`) },
    onError: (e) => toast.push('error', `Falha ao salvar: ${errorMessage(e)}`),
  })

  const reloadJobs = useMutation({
    mutationFn: async () => (await api.post('/scheduler/reload')).data,
    onSuccess: () => { jobs.refetch(); toast.push('success', 'Schedulers recarregados.') },
    onError: (e) => toast.push('error', `Falha ao recarregar: ${errorMessage(e)}`),
  })

  const runJob = useMutation({
    mutationFn: async (jobId: string) => {
      toast.push('info', `Job "${jobId}" disparado — executando em background…`)
      return (await api.post(`/scheduler/run/${jobId}`)).data
    },
    onSuccess: (_, jobId) => { jobs.refetch(); toast.push('success', `Job "${jobId}" concluído.`) },
    onError: (e, jobId) => toast.push('error', `Job "${jobId}" falhou: ${errorMessage(e)}`),
  })

  return (
    <div>
      <h1 style={{ fontSize: 22, marginBottom: 16 }}>Settings</h1>

      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ fontSize: 14, marginBottom: 12 }}>Schedulers (cron)</h3>
        {['news_ingest_cron', 'crew_run_cron', 'cvm_ingest_cron'].map(key => (
          <div key={key} style={{ display: 'grid', gridTemplateColumns: '180px 1fr auto', gap: 8, marginBottom: 8 }}>
            <label style={{ fontSize: 13, alignSelf: 'center' }}>{key}</label>
            <input
              value={draft[key]?.cron ?? ''}
              onChange={e => setDraft(d => ({ ...d, [key]: { ...d[key], cron: e.target.value } }))}
              placeholder="0 */4 * * 1-5"
            />
            <button
              onClick={() => update.mutate({ key, value: draft[key] })}
              className="btn-secondary"
            >
              Salvar
            </button>
          </div>
        ))}
        <button onClick={() => reloadJobs.mutate()} className="btn-primary" style={{ marginTop: 8 }}>
          Reload schedulers
        </button>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ fontSize: 14, marginBottom: 12 }}>LLM</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '180px 1fr auto', gap: 8 }}>
          <label style={{ fontSize: 13, alignSelf: 'center' }}>llm_model</label>
          <input
            value={draft.llm_model?.value ?? ''}
            onChange={e => setDraft(d => ({ ...d, llm_model: { value: e.target.value } }))}
          />
          <button onClick={() => update.mutate({ key: 'llm_model', value: draft.llm_model })} className="btn-secondary">Salvar</button>
        </div>
      </div>

      <div className="card">
        <h3 style={{ fontSize: 14, marginBottom: 12 }}>Jobs ativos</h3>
        <table>
          <thead><tr><th>ID</th><th>Próximo run</th><th>Trigger</th><th></th></tr></thead>
          <tbody>
            {jobs.data?.map(j => {
              const pending = runJob.isPending && runJob.variables === j.id
              return (
                <tr key={j.id}>
                  <td><strong>{j.id}</strong></td>
                  <td>{j.next_run?.replace('T', ' ').slice(0, 16) ?? '—'}</td>
                  <td style={{ fontSize: 11, color: 'var(--text-muted)' }}>{j.trigger}</td>
                  <td>
                    <button
                      onClick={() => runJob.mutate(j.id)}
                      disabled={pending}
                      className="btn-secondary"
                    >
                      {pending ? 'Rodando…' : 'Rodar agora'}
                    </button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
