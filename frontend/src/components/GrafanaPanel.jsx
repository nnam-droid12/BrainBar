/**
 * Embeds a live Grafana dashboard via iframe. Renders a placeholder instead of a
 * broken iframe when no Grafana Cloud stack is configured yet (see .env.example's
 * VITE_GRAFANA_BASE_URL), and always shows a working "Open in Grafana" link
 * underneath — a plain authenticated d-solo iframe is blocked by Grafana Cloud's
 * frame-ancestors security headers by default (shows as "refused to connect"), and a
 * browser can't detect that failure to fall back automatically. Pass `publicUrl` once
 * a Public Dashboard has been created for this dashboard (see
 * simulator/grafana_provisioning/) to get a real, unblocked embed.
 */
export default function GrafanaPanel({ dashboardUid, publicUrl, panelId, title, height = 300, timeRange }) {
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
    theme: 'light',
    ...(timeRange || {}),
  })
  const src = publicUrl || `${base}/d-solo/${dashboardUid}?${params.toString()}`
  const openUrl = `${base}/d/${dashboardUid}`

  return (
    <div className="grafana-panel">
      {title && <h4>{title}</h4>}
      <iframe src={src} title={title || dashboardUid} width="100%" height={height} frameBorder="0" />
      <a href={openUrl} target="_blank" rel="noreferrer" className="grafana-panel-open-link">
        {publicUrl ? 'Open in Grafana ↗' : "Panel not loading? Open in Grafana ↗"}
      </a>
    </div>
  )
}
