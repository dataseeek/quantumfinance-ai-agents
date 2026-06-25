export default function RecPill({ rec }: { rec: string }) {
  const cls = rec === 'COMPRAR' ? 'pill pill-buy'
    : rec === 'VENDER' ? 'pill pill-sell' : 'pill pill-hold'
  return <span className={cls}>{rec}</span>
}
