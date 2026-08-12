const LABELS = {
  circle: 'CIRCLED',
  hold: 'HOLD',
  reshoot: 'RESHOOT',
  fixable_in_post: 'FIXABLE IN POST',
}

export default function VerdictBadge({ verdict, rolling = false, error = null, size = 'md' }) {
  if (!verdict) {
    if (rolling) return <span className={`badge badge-rolling badge-${size}`}>ROLLING</span>
    if (error) return <span className={`badge badge-error badge-${size}`}>ANALYSIS FAILED</span>
    return <span className={`badge badge-analyzing badge-${size}`}>ANALYZING…</span>
  }
  const key = typeof verdict === 'string' ? verdict : verdict.verdict
  return <span className={`badge badge-${key} badge-${size}`}>{LABELS[key] || key}</span>
}
