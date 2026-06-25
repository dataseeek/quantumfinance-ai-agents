import { useEffect, useRef } from 'react'
import { createChart, CandlestickSeries, LineSeries, type IChartApi } from 'lightweight-charts'
import type { ChartData } from '../api'

export default function CandlestickChart({ data }: { data: ChartData | undefined }) {
  const ref = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)

  useEffect(() => {
    if (!ref.current || !data) return
    const chart = createChart(ref.current, {
      width: ref.current.clientWidth,
      height: 380,
      layout: { background: { color: '#1a1f2e' }, textColor: '#e8eaed' },
      grid: { vertLines: { color: '#232a3a' }, horzLines: { color: '#232a3a' } },
      timeScale: { borderColor: '#2d3548' },
      rightPriceScale: { borderColor: '#2d3548' },
    })
    chartRef.current = chart

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#4caf50', downColor: '#ef5350',
      borderUpColor: '#4caf50', borderDownColor: '#ef5350',
      wickUpColor: '#4caf50', wickDownColor: '#ef5350',
    })
    candleSeries.setData(data.ohlc.map(d => ({ time: d.time, open: d.open, high: d.high, low: d.low, close: d.close })))

    // SMA20 overlay (single value at last point — for full overlay we'd need to compute per-bar; placeholder)
    const sma = chart.addSeries(LineSeries, { color: '#ffa726', lineWidth: 2, title: 'SMA20' })
    const sma20 = data.indicators.sma20
    sma.setData(data.ohlc.map(d => ({ time: d.time, value: sma20 })))

    const ro = new ResizeObserver(entries => {
      for (const e of entries) chart.applyOptions({ width: e.contentRect.width })
    })
    ro.observe(ref.current)
    chart.timeScale().fitContent()

    return () => { ro.disconnect(); chart.remove() }
  }, [data])

  return <div ref={ref} style={{ width: '100%', height: 380 }} />
}
