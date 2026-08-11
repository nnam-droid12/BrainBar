const BACKEND_HTTP = import.meta.env.VITE_BACKEND_HTTP_URL || 'http://localhost:8080'
const BACKEND_WS = import.meta.env.VITE_BACKEND_WS_URL || 'ws://localhost:8080/stream'

async function request(path, options) {
  const res = await fetch(`${BACKEND_HTTP}${path}`, {
    headers: { 'content-type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText)
    throw new Error(`${options?.method || 'GET'} ${path} -> ${res.status}: ${detail}`)
  }
  return res.json()
}

export const api = {
  wsUrl: BACKEND_WS,
  getState: () => request('/state'),
  getShootStatus: () => request('/shoot/status'),
  startTake: (setupId) =>
    request('/shoot/start', { method: 'POST', body: JSON.stringify({ setup_id: setupId }) }),
  stopTake: () => request('/shoot/stop', { method: 'POST' }),
  wrapShoot: () => request('/shoot/wrap', { method: 'POST' }),
  armFault: (faultType, node) =>
    request('/faults/next', {
      method: 'POST',
      body: JSON.stringify({ fault_type: faultType, node: node || null }),
    }),
  clearFault: () => request('/faults/clear', { method: 'POST' }),
}
