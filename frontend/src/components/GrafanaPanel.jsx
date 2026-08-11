/**
 * Embeds a live Grafana dashboard (or a single panel) via iframe. Renders a
 * placeholder instead of a broken iframe when no Grafana Cloud stack is configured
 * yet — see .env.example's VITE_GRAFANA_BASE_URL.
 */
export default function GrafanaPanel({ dashboardUid, panelId, title, height = 300, timeRange }) {
  const base = import.meta.env.VITE_GRAFANA_BASE_URL

  if (!base) {
    return (
      <div className="grafana-panel grafana-panel-placeholder" style={{ height }}>
        <p className="muted small">
          {title || 'Grafana panel'} — set VITE_GRAFANA_BASE_URL to embed this live.
        </p>
      </div>
    )
  }

  const params = new URLSearchParams({
    orgId: '1',
    panelId: panelId ?? '',
    theme: 'dark',
    ...(timeRange || {}),
  })
  const src = `${base}/d-solo/${dashboardUid}?${params.toString()}`

  return (
    <div className="grafana-panel">
      {title && <h4>{title}</h4>}
      <iframe
        src={src}
        title={title || dashboardUid}
        width="100%"
        height={height}
        frameBorder="0"
      />
    </div>
  )
}
