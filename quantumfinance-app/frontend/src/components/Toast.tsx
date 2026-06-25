import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'

type Kind = 'success' | 'error' | 'info'
type Toast = { id: number; kind: Kind; text: string }
type Ctx = { push: (kind: Kind, text: string) => void }

const ToastCtx = createContext<Ctx | null>(null)

export function useToast() {
  const ctx = useContext(ToastCtx)
  if (!ctx) throw new Error('useToast must be used inside <ToastProvider>')
  return ctx
}

export function errorMessage(err: any): string {
  return err?.response?.data?.detail
    ?? err?.response?.data?.error
    ?? err?.message
    ?? 'Erro desconhecido'
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Toast[]>([])

  const push = useCallback((kind: Kind, text: string) => {
    setItems(prev => [...prev, { id: Date.now() + Math.random(), kind, text }])
  }, [])

  return (
    <ToastCtx.Provider value={{ push }}>
      {children}
      <div
        style={{
          position: 'fixed', bottom: 16, right: 16, zIndex: 9999,
          display: 'flex', flexDirection: 'column', gap: 8, maxWidth: 380,
        }}
      >
        {items.map(t => (
          <ToastItem key={t.id} toast={t} onDone={() => setItems(prev => prev.filter(x => x.id !== t.id))} />
        ))}
      </div>
    </ToastCtx.Provider>
  )
}

function ToastItem({ toast, onDone }: { toast: Toast; onDone: () => void }) {
  useEffect(() => {
    const id = setTimeout(onDone, toast.kind === 'error' ? 8000 : 4000)
    return () => clearTimeout(id)
  }, [toast.kind, onDone])

  const bg = toast.kind === 'error' ? '#c62828' : toast.kind === 'success' ? '#2e7d32' : '#1565c0'
  return (
    <div
      role={toast.kind === 'error' ? 'alert' : 'status'}
      style={{
        background: bg, color: 'white', padding: '10px 14px',
        borderRadius: 8, boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
        fontSize: 13, lineHeight: 1.4, display: 'flex', gap: 8, alignItems: 'flex-start',
      }}
    >
      <span style={{ flex: 1 }}>{toast.text}</span>
      <button
        onClick={onDone}
        style={{ background: 'transparent', border: 0, color: 'white', cursor: 'pointer', fontSize: 16, lineHeight: 1, padding: 0 }}
        aria-label="Fechar"
      >×</button>
    </div>
  )
}
