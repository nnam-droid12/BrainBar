// Display metadata for agents.schemas.ActionType — keep in sync with that enum.
// Anything not listed here (there shouldn't be any) falls back to a generic look in
// VerdictCard rather than breaking, since this is presentation-only.
export const ACTION_META = {
  annotate_dashboard: { icon: '📝', label: 'Annotated dashboard', variant: 'neutral' },
  pre_stage_reshoot: { icon: '🔁', label: 'Pre-staged reshoot', variant: 'neutral' },
  open_incident: { icon: '🚨', label: 'Opened incident', variant: 'reactive' },
  silence_alert: { icon: '🔕', label: 'Silenced alert', variant: 'neutral' },
  resolve_incident: { icon: '✅', label: 'Resolved incident', variant: 'neutral' },
  preventive_load_shed: { icon: '🔮', label: 'Predicted & prevented', variant: 'predictive' },
  page_oncall: { icon: '📟', label: 'Paged on-call', variant: 'reactive' },
}

export function actionMeta(type) {
  return ACTION_META[type] || { icon: '•', label: type, variant: 'neutral' }
}
