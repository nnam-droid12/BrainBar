import { useEffect, useReducer, useRef } from 'react'
import { api } from './api.js'

const initialState = {
  connected: false,
  scene: '',
  setupId: '',
  takeNumber: 0,
  takes: [],
  takesById: {},
  coverageOwed: {},
  dailies: null,
  report: null,
  activeIncident: null,
  grafanaAlerts: [],
  stageActions: [],
}

function upsertTake(state, takeId, patch) {
  const existing = state.takesById[takeId] || { take_id: takeId }
  const updated = { ...existing, ...patch }
  const takesById = { ...state.takesById, [takeId]: updated }
  const takes = state.takes.includes(takeId) ? state.takes : [...state.takes, takeId]
  return { ...state, takesById, takes }
}

function reducer(state, action) {
  switch (action.type) {
    case 'hydrate': {
      const s = action.payload
      const takesById = {}
      const takes = []
      for (const t of s.takes || []) {
        takesById[t.take_id] = t
        takes.push(t.take_id)
      }
      return {
        ...state,
        scene: s.scene,
        setupId: s.setup_id,
        takeNumber: s.take_number,
        takes,
        takesById,
        coverageOwed: s.coverage_owed || {},
        dailies: s.dailies || null,
        activeIncident: s.active_incident || null,
      }
    }
    case 'connected':
      return { ...state, connected: true }
    case 'disconnected':
      return { ...state, connected: false }
    case 'slate': {
      const p = action.payload
      const next = upsertTake(state, p.take_id, {
        take_id: p.take_id,
        scene: p.scene,
        setup_id: p.setup,
        take_number: p.take,
        rolling: true,
        verdict: null,
        action_log: null,
        routing: null,
        fault_armed: p.fault_armed || null,
      })
      return { ...next, scene: p.scene, setupId: p.setup, takeNumber: p.take }
    }
    case 'cut': {
      const p = action.payload
      return upsertTake(state, p.take_id, {
        start_timecode: p.start_timecode,
        end_timecode: p.end_timecode,
        rolling: false,
      })
    }
    case 'verdict': {
      const p = action.payload
      const next = upsertTake(state, p.take_id, { verdict: p.verdict, rolling: false })
      const owed = { ...next.coverageOwed, [p.verdict.scene]: p.verdict.creative.coverage_owed }
      return { ...next, coverageOwed: owed }
    }
    case 'routing_decision': {
      const p = action.payload
      return upsertTake(state, p.take_id, { routing: p.routing })
    }
    case 'action_log': {
      const p = action.payload
      return upsertTake(state, p.take_id, { action_log: p.action_log })
    }
    case 'verdict_error': {
      const p = action.payload
      return upsertTake(state, p.take_id, { error: p.error, rolling: false })
    }
    case 'node_down': {
      const p = action.payload
      return {
        ...state,
        activeIncident: { node: p.node, take_id: p.take_id, status: 'detected' },
      }
    }
    case 'stage_action':
      return { ...state, stageActions: [action.payload, ...state.stageActions].slice(0, 50) }
    case 'grafana_alert':
      return { ...state, grafanaAlerts: [action.payload, ...state.grafanaAlerts].slice(0, 50) }
    case 'wrap':
      return { ...state, dailies: action.payload.dailies, report: action.payload.report }
    default:
      return state
  }
}

export function useLiveStream() {
  const [state, dispatch] = useReducer(reducer, initialState)
  const wsRef = useRef(null)

  useEffect(() => {
    let cancelled = false
    api
      .getState()
      .then((s) => {
        if (!cancelled) dispatch({ type: 'hydrate', payload: s })
      })
      .catch(() => {
        // backend not reachable yet — the WebSocket connection below will keep retrying
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    let retryDelay = 1000

    function connect() {
      if (cancelled) return
      const ws = new WebSocket(api.wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        retryDelay = 1000
        dispatch({ type: 'connected' })
      }
      ws.onclose = () => {
        dispatch({ type: 'disconnected' })
        if (!cancelled) {
          setTimeout(connect, retryDelay)
          retryDelay = Math.min(retryDelay * 1.5, 10000)
        }
      }
      ws.onerror = () => ws.close()
      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          dispatch({ type: msg.event, payload: msg })
        } catch {
          // ignore malformed frames
        }
      }
    }

    connect()
    return () => {
      cancelled = true
      wsRef.current?.close()
    }
  }, [])

  return state
}
