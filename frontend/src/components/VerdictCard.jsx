export default function VerdictCard({ take }) {
  if (!take) {
    return (
      <div className="verdict-card verdict-card-empty">
        <h3 className="verdict-card-title">Evidence &amp; reasoning</h3>
        <p className="muted small">Roll a take above to see the crew's evidence here once a verdict lands.</p>
      </div>
    )
  }

  const { verdict, technical, creative } = take.verdict || {}

  if (take.rolling) {
    return (
      <div className="verdict-card verdict-card-empty">
        <h3 className="verdict-card-title">Evidence &amp; reasoning</h3>
        <p className="muted small">Take is rolling — evidence appears here the moment it cuts and the crew reports back.</p>
      </div>
    )
  }

  if (!take.verdict && take.error) {
    return (
      <div className="verdict-card verdict-card-empty">
        <h3 className="verdict-card-title">Evidence &amp; reasoning</h3>
        <p className="verdict-card-error-pulse">✕ Analysis failed</p>
        <p className="muted small">{take.error}</p>
        <p className="muted small">
          The crew hit a backend error partway through analysis — usually a transient
          Vertex AI hiccup (rate limit or a brief service blip) rather than a problem
          with the take itself. Roll this setup again from the demo controls to retry.
        </p>
      </div>
    )
  }

  if (!take.verdict) {
    return (
      <div className="verdict-card verdict-card-empty">
        <h3 className="verdict-card-title">Evidence &amp; reasoning</h3>
        <p className="verdict-card-analyzing-pulse">● Crew is analyzing this take…</p>
        <p className="muted small">
          Continuity and the Technical Director are querying Grafana and the script in
          parallel (watch them light up above), then the Supervisor synthesizes the
          call. This usually takes 15–60s — the page updates live over WebSocket the
          moment it lands, no need to refresh.
        </p>
      </div>
    )
  }

  return (
    <div className={`verdict-card verdict-card-${verdict}`}>
      <h3 className="verdict-card-title">Evidence &amp; reasoning</h3>
      <p className="verdict-card-reasoning">{take.verdict.reasoning}</p>

      <div className="verdict-card-evidence">
        <div className="evidence-block">
          <h4>Technical — Technical Director</h4>
          <p className={technical?.clean ? 'evidence-clean' : 'evidence-issue'}>
            {technical?.clean ? 'Clean' : 'Issue detected'} · model: {technical?.model_tier_used}
          </p>
          <p className="muted small">{technical?.summary}</p>
        </div>
        <div className="evidence-block">
          <h4>Creative — Continuity</h4>
          <p className={creative?.matches_intent ? 'evidence-clean' : 'evidence-issue'}>
            {creative?.matches_intent ? 'Matches intent' : 'Intent mismatch'}
          </p>
          <p className="muted small">{creative?.summary}</p>
        </div>
      </div>

      {creative?.coverage_owed?.length > 0 && (
        <p className="verdict-card-owed">
          Coverage still owed: {creative.coverage_owed.join(', ')}
        </p>
      )}

      {take.action_log?.actions?.length > 0 && (
        <div className="verdict-card-actions">
          <h4>First AD actions</h4>
          <ul>
            {take.action_log.actions.map((a, i) => (
              <li key={i}>
                <span className="action-type">{a.type}</span> — {a.rationale}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
