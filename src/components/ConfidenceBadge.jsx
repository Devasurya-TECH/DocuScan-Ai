export default function ConfidenceBadge({ value }) {
  const percentage = Math.round(Number(value) * (Number(value) <= 1 ? 100 : 1))
  const style = percentage >= 85 ? 'bg-emerald-50 text-emerald-700 ring-emerald-200' : percentage >= 60 ? 'bg-amber-50 text-amber-700 ring-amber-200' : 'bg-rose-50 text-rose-700 ring-rose-200'
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ${style}`}>{Number.isFinite(percentage) ? `${percentage}%` : 'N/A'}</span>
}
