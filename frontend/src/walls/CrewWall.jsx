import GrafanaPanel from '../components/GrafanaPanel.jsx'

const LATENCY_BUDGET_MS = Number(import.meta.env.VITE_LATENCY_BUDGET_MS || 15000)

function LatencyBar({ take }) {
  const ms = take.verdict?.latency_ms ?? 0
  const pct = Math.min((ms / LATENCY_BUDGET_MS) * 100, 100)
  const over = ms > LATENCY_BUDGET_MS
  return (
    <div className="latency-row">
      <span className="latency-label">
        {take.scene} S{take.setup_id} T{take.take_number}
      </span>
      <div className="latency-track">
        <div className={`latency-fill ${over ? 'latency-over' : ''}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="latency-value">{ms ? `${Math.round(ms)}ms` : '—'}</span>
    </div>
  )
}

export default function CrewWall({ stream }) {
  const { takes, takesById } = stream
  const withVerdicts = takes.filter((id) => takesById[id]?.verdict).map((id) => takesById[id])
  const withRouting = takes.filter((id) => takesById[id]?.routing).map((id) => takesById[id])

  return (
    <div className="wall crew-wall">
      <div className="wall-col wall-col-main">
        <div className="panel">
          <h3>Verdict latency vs. budget ({LATENCY_BUDGET_MS / 1000}s)</h3>
          {withVerdicts.length === 0 && <p className="muted small">No verdicts yet this session.</p>}
          {withVerdicts.map((t) => (
            <LatencyBar key={t.take_id} take={t} />
          ))}
        </div>

        <GrafanaPanel dashboardUid="brainbar-crew-health" title="Crew Health — token cost & MCP tool activity" height={420} />
      </div>

      <div className="wall-col wall-col-side">
        <div className="panel">
          <h3>Model routing</h3>
          {withRouting.length === 0 && <p className="muted small">No routing decisions yet.</p>}
          <ul className="routing-list">
            {withRouting
              .slice()
              .reverse()
              .map((t) => (
                <li key={t.take_id}>
                  <div className="routing-row-head">
                    <span>{t.take_id}</span>
                    <span className={`tier-chip tier-${t.routing.tier}`}>{t.routing.tier}</span>
                  </div>
                  <p className="muted small">{t.routing.reason}</p>
                </li>
              ))}
          </ul>
        </div>
      </div>
    </div>
  )
}
