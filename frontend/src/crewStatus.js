// Derives each crew agent's live status from the same WebSocket-driven take fields
// the rest of the cockpit already renders — no separate "agent is working" event
// exists, but the pipeline is strictly sequential (see backend/routes/internal.py's
// _on_cut), so the take's own state transitions double as the crew's.
export const AGENTS = [
  { key: 'continuity', label: 'Continuity', role: 'creative intent vs. script & shot list' },
  { key: 'technical_director', label: 'Technical Director', role: 'live stage telemetry' },
  { key: 'supervisor', label: 'Supervisor', role: 'synthesizes the circle-take call' },
  { key: 'first_ad', label: 'First AD', role: 'acts on the verdict' },
  { key: 'dit', label: 'DIT', role: 'compiles technical dailies at wrap' },
]

export function agentStatus(agentKey, take, dailiesReady) {
  if (agentKey === 'dit') return dailiesReady ? 'done' : 'standby'
  if (!take) return 'standby'
  if (take.error && !take.verdict) {
    return agentKey === 'first_ad' ? 'standby' : 'error'
  }
  if (take.rolling) return 'standby'
  if (agentKey === 'first_ad') {
    if (!take.verdict) return 'standby'
    return take.action_log ? 'done' : 'active'
  }
  return take.verdict ? 'done' : 'active'
}

export const STATUS_LABEL = {
  standby: 'Standing by',
  active: 'Working…',
  done: 'Done',
  error: 'Error',
}
