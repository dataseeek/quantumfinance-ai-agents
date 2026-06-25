import { NavLink, Route, Routes } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import News from './pages/News'
import CVM from './pages/CVM'
import Chat from './pages/Chat'
import Portfolio from './pages/Portfolio'
import Agents from './pages/Agents'
import Settings from './pages/Settings'
import Backtest from './pages/Backtest'
import Accuracy from './pages/Accuracy'
import { ToastProvider } from './components/Toast'

export default function App() {
  return (
    <ToastProvider>
    <div style={{ display: 'grid', gridTemplateColumns: '220px 1fr', minHeight: '100vh' }}>
      <aside style={{ background: 'var(--bg-card)', borderRight: '1px solid var(--border)', padding: 20 }}>
        <h1 style={{ fontSize: 16, fontWeight: 700, marginBottom: 4, color: 'var(--text)' }}>QuantumFinance</h1>
        <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 20 }}>AI Agent Home Broker</p>
        <nav style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {[
            { to: '/', label: 'Dashboard' },
            { to: '/news', label: 'News' },
            { to: '/cvm', label: 'CVM RI' },
            { to: '/chat', label: 'Chat' },
            { to: '/portfolio', label: 'Portfolio' },
            { to: '/backtest', label: 'Backtest' },
            { to: '/accuracy', label: 'Acurácia' },
            { to: '/agents', label: 'Agents' },
            { to: '/settings', label: 'Settings' },
          ].map(({ to, label }) => (
            <NavLink
              key={to} to={to} end={to === '/'}
              style={({ isActive }) => ({
                padding: '8px 12px',
                borderRadius: 6,
                color: isActive ? 'var(--pink)' : 'var(--text)',
                background: isActive ? 'rgba(233,30,99,0.1)' : 'transparent',
                textDecoration: 'none',
                fontSize: 13,
              })}
            >
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main style={{ padding: 24, overflow: 'auto' }}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/news" element={<News />} />
          <Route path="/cvm" element={<CVM />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/portfolio" element={<Portfolio />} />
          <Route path="/backtest" element={<Backtest />} />
          <Route path="/accuracy" element={<Accuracy />} />
          <Route path="/agents" element={<Agents />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
    </ToastProvider>
  )
}
