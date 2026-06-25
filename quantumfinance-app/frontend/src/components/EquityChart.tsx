import { useEffect, useRef } from 'react'
import { createChart, LineSeries, type IChartApi } from 'lightweight-charts'

export type EquityPoint = {
  date: string
  agent_equity: number
  bh_equity: number
}

export default function EquityChart({ data, height = 280 }: { data: EquityPoint[] | undefined; height?: number }) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current || !data || data.length === 0) return
    const chart: IChartApi = createChart(ref.current, {
      width: ref.current.clientWidth,
      height,
      layout: { background: { color: '#1a1f2e' }, textColor: '#e8eaed' },
      grid: { vertLines: { color: '#232a3a' }, horzLines: { color: '#232a3a' } },
      timeScale: { borderColor: '#2d3548' },
      rightPriceScale: { borderColor: '#2d3548' },
    })

    const agent = chart.addSeries(LineSeries, { color: '#e91e63', lineWidth: 2, title: 'Agente' })
    const bh = chart.addSeries(LineSeries, { color: '#42a5f5', lineWidth: 2, lineStyle: 1, title: 'Buy & Hold' })

    agent.setData(data.map(d => ({ time: d.date, value: d.agent_equity })))
    bh.setData(data.map(d => ({ time: d.date, value: d.bh_equity })))

    const ro = new ResizeObserver(entries => {
      for (const e of entries) chart.applyOptions({ width: e.contentRect.width })
    })
    ro.observe(ref.current)
    chart.timeScale().fitContent()

    return () => { ro.disconnect(); chart.remove() }
  }, [data, height])

  return <div ref={ref} style={{ width: '100%', height }} />
}
