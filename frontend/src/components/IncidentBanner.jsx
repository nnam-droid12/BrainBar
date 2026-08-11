export default function IncidentBanner({ incident, grafanaBaseUrl }) {
  if (!incident) return null

  const isHandled = incident.status === 'handled'
  const incidentAction = incident.actions?.find((a) => a.type === 'open_incident')

  return (
    <div className={`incident-banner ${isHandled ? 'incident-handled' : 'incident-active'}`}>
      <span className="incident-icon">{isHandled ? '✓' : '⚠'}</span>
      <div className="incident-body">
        <strong>{incident.node} went offline</strong> on take {incident.take_id}
        {isHandled ? ' — First AD opened an incident and drove it to resolution.' : ' — First AD responding…'}
        {incidentAction?.grafana_ref && grafanaBaseUrl && (
          <a
            className="incident-link"
            href={`${grafanaBaseUrl}${incidentAction.grafana_ref}`}
            target="_blank"
            rel="noreferrer"
          >
            View Grafana incident →
          </a>
        )}
      </div>
    </div>
  )
}
