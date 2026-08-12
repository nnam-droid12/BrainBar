const LABELS = {
  circle: 'CIRCLED',
  hold: 'HOLD',
  reshoot: 'RESHOOT',
  fixable_in_post: 'FIXABLE IN POST',
}

export default function VerdictBadge({ verdict, rolling = false, size = 'md' }) {
  if (!verdict) {
    return rolling ? (
      <span className={`badge badge-rolling badge-${size}`}>ROLLING</span>
    ) : (
      <span className={`badge badge-analyzing badge-${size}`}>ANALYZING…</span>
    )
  }
  const key = typeof verdict === 'string' ? verdict : verdict.verdict
  return <span className={`badge badge-${key} badge-${size}`}>{LABELS[key] || key}</span>
}
