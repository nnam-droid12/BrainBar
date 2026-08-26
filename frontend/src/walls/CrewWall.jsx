import CrewHealthPanel from '../components/CrewHealthPanel.jsx'
import GrafanaCapabilities from '../components/GrafanaCapabilities.jsx'
import { AGENTS } from '../crewStatus.js'

const LATENCY_BUDGET_MS = Number(import.meta.env.VITE_LATENCY_BUDGET_MS || 15000)
const GRAFANA_BASE = import.meta.env.VITE_GRAFANA_BASE_URL

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
      <div className="crew-wall-intro panel">
        <h3>Agent ops — the crew watching itself</h3>
        <p className="muted small">
          Every Gemini call and every Grafana MCP tool call the crew makes is itself
          exported as telemetry into the same Grafana Cloud stack it queries on set.
          This is that self-observability loop, live: what each of the five agents is
          costing in tokens, how many real Grafana tool calls they're making, and
          whether the Supervisor is staying inside its on-set latency budget.
        </p>
        <div className="crew-wall-roster">
          {AGENTS.map((a) => (
            <span key={a.key} className="crew-wall-roster-item">
              <strong>{a.label}</strong> — {a.role}
            </span>
          ))}
        </div>
        <GrafanaCapabilities grafanaBaseUrl={GRAFANA_BASE} />
      </div>

      <div className="wall-col wall-col-main">
        <div className="panel">
          <h3>Verdict latency vs. budget ({LATENCY_BUDGET_MS / 1000}s)</h3>
          <p className="muted small">
            Time from cut to a synthesized verdict, for the whole crew pipeline — this
            is what the Supervisor's own model-routing decisions are trying to protect.
          </p>
          {withVerdicts.length === 0 && <p className="muted small">No verdicts yet this session.</p>}
          {withVerdicts.map((t) => (
            <LatencyBar key={t.take_id} take={t} />
          ))}
        </div>

        <CrewHealthPanel />
      </div>

      <div className="wall-col wall-col-side">
        <div className="panel">
          <h3>Model routing</h3>
          <p className="muted small">
            The Supervisor picks Gemini Pro or Flash per take against its own observed
            latency headroom — routine coverage gets the fast model, hero shots get the
            stronger one.
          </p>
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
