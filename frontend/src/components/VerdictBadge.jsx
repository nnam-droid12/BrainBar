const LABELS = {
  circle: 'CIRCLED',
  hold: 'HOLD',
  reshoot: 'RESHOOT',
  fixable_in_post: 'FIXABLE IN POST',
}

export default function VerdictBadge({ verdict, size = 'md' }) {
  if (!verdict) {
    return <span className={`badge badge-pending badge-${size}`}>ROLLING</span>
  }
  const key = typeof verdict === 'string' ? verdict : verdict.verdict
  return <span className={`badge badge-${key} badge-${size}`}>{LABELS[key] || key}</span>
}
