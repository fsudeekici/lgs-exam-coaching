import { formatChange } from '../format'

/** Signed change with an arrow, so direction never depends on colour alone. */
export default function Delta({ change }: { change: number | null }) {
  if (change === null) return <span className="text-slate-400">—</span>
  if (change === 0) return <span className="tabular-nums text-slate-500">= değişmedi</span>
  return (
    <span className={`font-medium tabular-nums ${change > 0 ? 'text-green-800' : 'text-red-700'}`}>
      {change > 0 ? '▲' : '▼'} {formatChange(change)}
    </span>
  )
}
