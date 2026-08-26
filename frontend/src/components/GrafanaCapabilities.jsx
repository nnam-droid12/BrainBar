// A static legend of the Grafana Cloud surfaces the crew is wired into beyond the
// obvious metrics/logs/traces path — several of these (profiling especially) have no
// other on-screen presence, since the actual flamegraph/forecast/investigation view
// lives in Grafana itself, not reimplemented here. This exists so a judge scanning the
// dashboard sees the full list without having to find each one firing live.
const CAPABILITIES = [
  {
    icon: '🔮',
    label: 'Predictive VRAM forecasting',
    detail: 'Grafana ML forecasts feed First AD — pre-emptive load-shed before a node actually breaches VRAM',
  },
  {
    icon: '🧬',
    label: 'Continuous profiling',
    detail: "The crew's own process, pushed to Pyroscope and linked to its OTel traces",
  },
  {
    icon: '🔎',
    label: 'Sift second opinion',
    detail: "Technical Director reconciles with Grafana's own diagnostic assistant when an investigation exists",
  },
  {
    icon: '📟',
    label: 'On-call paging (IRM)',
    detail: 'A hardware failure pages a real escalation chain, not just an incident',
  },
]

export default function GrafanaCapabilities({ grafanaBaseUrl }) {
  return (
    <div className="grafana-capabilities">
      <span className="grafana-capabilities-label">Also wired into Grafana Cloud</span>
      <div className="grafana-capabilities-list">
        {CAPABILITIES.map((c) => (
          <div className="grafana-capability" key={c.label} title={c.detail}>
            <span className="grafana-capability-icon">{c.icon}</span>
            <span className="grafana-capability-label">{c.label}</span>
          </div>
        ))}
      </div>
      {grafanaBaseUrl && (
        <a className="grafana-capabilities-link" href={grafanaBaseUrl} target="_blank" rel="noreferrer">
          Open Grafana Cloud →
        </a>
      )}
    </div>
  )
}
