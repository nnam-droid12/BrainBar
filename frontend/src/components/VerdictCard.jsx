import VerdictBadge from './VerdictBadge.jsx'

export default function VerdictCard({ take }) {
  if (!take) {
    return (
      <div className="verdict-card verdict-card-empty">
        <p className="muted">No take rolling yet. Roll a take from the demo controls to see the call.</p>
      </div>
    )
  }

  const { verdict, technical, creative } = take.verdict || {}
  const rolling = take.rolling

  return (
    <div className={`verdict-card verdict-card-${verdict || 'pending'}`}>
      <div className="verdict-card-header">
        <div>
          <div className="verdict-card-eyebrow">
            {take.scene} · SETUP {take.setup_id} · TAKE {take.take_number}
          </div>
          <div className="verdict-card-timecode">
            {take.start_timecode || '--:--:--:--'} &rarr; {take.end_timecode || '--:--:--:--'}
          </div>
        </div>
        <VerdictBadge verdict={take.verdict} rolling={rolling} error={take.error} size="lg" />
      </div>

      {rolling && <p className="verdict-card-rolling">● ROLLING</p>}

      {!rolling && !take.verdict && take.error && (
        <div className="verdict-card-analyzing verdict-card-error">
          <p className="verdict-card-error-pulse">✕ Analysis failed</p>
          <p className="muted small">
            {take.error}
          </p>
          <p className="muted small">
            This is almost always a Vertex AI rate limit from heavy testing volume, not
            a broken take — roll this setup again from the demo controls to retry, or
            wait a minute for quota to recover.
          </p>
        </div>
      )}

      {!rolling && !take.verdict && !take.error && (
        <div className="verdict-card-analyzing">
          <p className="verdict-card-analyzing-pulse">● Crew is analyzing this take…</p>
          <p className="muted small">
            Continuity and the Technical Director are querying Grafana and the script in
            parallel, then the Supervisor synthesizes the call. This usually takes
            10–30s, but can take longer under Vertex AI rate limits — the page updates
            live over WebSocket the moment it lands, no need to refresh.
          </p>
        </div>
      )}

      {take.verdict && (
        <>
          <p className="verdict-card-headline">{take.verdict.headline}</p>
          <p className="verdict-card-reasoning">{take.verdict.reasoning}</p>

          <div className="verdict-card-evidence">
            <div className="evidence-block">
              <h4>Technical</h4>
              <p className={technical?.clean ? 'evidence-clean' : 'evidence-issue'}>
                {technical?.clean ? 'Clean' : 'Issue detected'} · model: {technical?.model_tier_used}
              </p>
              <p className="muted small">{technical?.summary}</p>
            </div>
            <div className="evidence-block">
              <h4>Creative</h4>
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
        </>
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
