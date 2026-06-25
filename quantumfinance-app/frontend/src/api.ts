import axios from 'axios'

export const api = axios.create({ baseURL: '/api' })

export type Ticker = {
  symbol: string
  name: string
  sector: string
  last: number | null
  prev_close: number | null
  change_pct: number | null
  volume: number | null
}

export type Recommendation = {
  id: number
  ticker: string
  date: string
  recommendation: 'COMPRAR' | 'VENDER' | 'AGUARDAR'
  reasoning: string
}

export type NewsItem = {
  id: number
  source: string
  title: string
  url: string
  published_at: string | null
  sentiment: string | null
}

export type CvmFiling = {
  id: number
  category: string
  title: string
  filed_at: string | null
  link: string | null
  doc_type: string
}

export type Portfolio = {
  id: number
  name: string
  risk_profile: 'conservative' | 'moderate' | 'aggressive' | null
  description: string | null
  cash: number
  equity: number
  initial: number
  total_pnl: number
  total_pnl_pct: number
  positions: Array<{
    ticker: string
    quantity: number
    avg_price: number
    last_price: number
    market_value: number
    pnl: number
    pnl_pct: number
  }>
}

export type Agent = {
  id: number
  name: string
  role: string
  goal: string
  backstory: string
  tool_names: string[]
  max_iter: number
  is_system: boolean
}

export type SwingPlan = {
  ticker: string
  rec: string
  price: number
  support: { label: string; value: number | null }
  resistance: { label: string; value: number | null }
  stop: number | null
  target: number | null
  risk_reward: number | null
  atr_pct: number
  holding: string
  signals: { buy: number; sell: number }
  approved: boolean
}

export type ChartData = {
  ticker: string
  period: string
  ohlc: Array<{ time: string; open: number; high: number; low: number; close: number; volume: number }>
  indicators: {
    rsi: number; macd: number; macd_signal: number; macd_hist: number;
    sma20: number; ema20: number; bb_upper: number; bb_lower: number; last_close: number
  }
}
