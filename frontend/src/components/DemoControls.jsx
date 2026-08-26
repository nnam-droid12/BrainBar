import { useEffect, useRef, useState } from 'react'
import { api } from '../api.js'

const SETUPS = ['1', '2', '3', '4']
const FAULTS = [
  { value: '', label: 'No fault (clean take)' },
  { value: 'vram_spike', label: 'VRAM spike' },
  { value: 'node_death', label: 'Node death' },
  { value: 'genlock_drift', label: 'Genlock drift' },
  { value: 'tracking_jitter', label: 'Tracking jitter' },
  { value: 'thermal_throttle', label: 'Thermal throttle' },
]
const NODES = ['node-1', 'node-2', 'node-3', 'node-4', 'node-5', 'node-6']

// A scripted, escalating 3-take run for a live judging demo: clean baseline, then a
// quality fault (exercises Sift/annotation-playbook/VRAM-forecast checks), then a
// hardware failure (exercises the full incident/paging/drain path) — one click instead
// of several manual arm/roll/cut cycles under demo pressure.
const SCENARIO = [
  {
    setupId: '4',
    fault: '',
    node: null,
    title: 'Clean plate — baseline',
    narration: 'No fault armed — watch all five agents light up and the crew confirm a clean take.',
  },
  {
    setupId: '2',
    fault: 'vram_spike',
    node: 'node-3',
    title: 'VRAM spike on node-3',
    narration:
      'Technical Director pulls real Mimir/Loki evidence, checks its own annotation history and any Sift investigation, and First AD checks the live Grafana ML VRAM forecast.',
  },
  {
    setupId: '3',
    fault: 'node_death',
    node: 'node-6',
    title: 'Hardware failure on node-6',
    narration:
      'Watch the incident banner: First AD opens a Grafana incident, pages the on-call escalation chain, silences the alert storm, and drains the node.',
  },
]

const STATUS_ICON = { running: '⏳', done: '✅', timeout: '⚠', error: '✕' }

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export default function DemoControls({ stream }) {
  const [setupId, setSetupId] = useState('1')
  const [fault, setFault] = useState('')
  const [node, setNode] = useState('node-6')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')

  const [scenarioRunning, setScenarioRunning] = useState(false)
  const [scenarioLog, setScenarioLog] = useState([])

  // Avoids stale closures inside the scenario's async loop — React state captured at
  // loop-start would never see takes that arrive mid-run over the WebSocket.
  const takesRef = useRef(stream?.takes || [])
  const takesByIdRef = useRef(stream?.takesById || {})
  useEffect(() => {
    takesRef.current = stream?.takes || []
    takesByIdRef.current = stream?.takesById || {}
  }, [stream?.takes, stream?.takesById])

  const disabled = busy || scenarioRunning

  async function run(fn, label) {
    setBusy(true)
    setMessage('')
    try {
      await fn()
      setMessage(label)
    } catch (err) {
      setMessage(`error: ${err.message}`)
    } finally {
      setBusy(false)
    }
  }

  async function waitForNewTake(beforeCount, timeoutMs = 20000) {
    const start = Date.now()
    while (takesRef.current.length <= beforeCount) {
      if (Date.now() - start > timeoutMs) return null
      await sleep(400)
    }
    return takesRef.current[takesRef.current.length - 1]
  }

  async function waitForActionLog(takeId, timeoutMs = 90000) {
    const start = Date.now()
    while (!takesByIdRef.current[takeId]?.action_log) {
      if (Date.now() - start > timeoutMs) return false
      await sleep(500)
    }
    return true
  }

  function updateLog(index, patch) {
    setScenarioLog((log) => log.map((entry, i) => (i === index ? { ...entry, ...patch } : entry)))
  }

  async function runScenario() {
    setScenarioRunning(true)
    setScenarioLog(SCENARIO.map((s) => ({ title: s.title, narration: s.narration, status: 'pending' })))

    for (let i = 0; i < SCENARIO.length; i++) {
      const step = SCENARIO[i]
      updateLog(i, { status: 'running' })
      try {
        if (step.fault) await api.armFault(step.fault, step.node)
        const beforeCount = takesRef.current.length
        await api.startTake(step.setupId)
        const takeId = await waitForNewTake(beforeCount)
        if (!takeId) throw new Error('take did not start in time')
        const landed = await waitForActionLog(takeId)
        updateLog(i, { status: landed ? 'done' : 'timeout', takeId })
      } catch (err) {
        updateLog(i, { status: 'error', error: err.message })
      }
    }

    setScenarioLog((log) => [...log, { title: 'Wrap', narration: 'Compiling dailies with Grafana deep-links.', status: 'running' }])
    try {
      await api.wrapShoot()
      setScenarioLog((log) => log.map((entry, i) => (i === log.length - 1 ? { ...entry, status: 'done' } : entry)))
    } catch (err) {
      setScenarioLog((log) => log.map((entry, i) => (i === log.length - 1 ? { ...entry, status: 'error', error: err.message } : entry)))
    }
    setScenarioRunning(false)
  }

  return (
    <div className="demo-controls">
      <h3>Demo controls</h3>

      <div className="demo-scenario">
        <button className="demo-scenario-button" disabled={disabled} onClick={runScenario}>
          {scenarioRunning ? '🎬 Running scenario…' : '🎬 Run demo scenario (3 takes)'}
        </button>
        {scenarioLog.length > 0 && (
          <ul className="demo-scenario-log">
            {scenarioLog.map((entry, i) => (
              <li key={i} className={`demo-scenario-step demo-scenario-${entry.status}`}>
                <span className="demo-scenario-icon">{STATUS_ICON[entry.status] || '·'}</span>
                <div>
                  <strong>{entry.title}</strong>
                  <p className="muted small">{entry.error || entry.narration}</p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="demo-controls-row">
        <select value={setupId} onChange={(e) => setSetupId(e.target.value)} disabled={disabled}>
          {SETUPS.map((s) => (
            <option key={s} value={s}>
              Setup {s}
            </option>
          ))}
        </select>
        <button
          disabled={disabled}
          onClick={() => run(() => api.startTake(setupId), `rolling setup ${setupId}`)}
        >
          Roll take
        </button>
        <button disabled={disabled} className="secondary" onClick={() => run(() => api.stopTake(), 'cut')}>
          Cut
        </button>
      </div>

      <div className="demo-controls-row">
        <select value={fault} onChange={(e) => setFault(e.target.value)} disabled={disabled}>
          {FAULTS.map((f) => (
            <option key={f.value} value={f.value}>
              {f.label}
            </option>
          ))}
        </select>
        <select value={node} onChange={(e) => setNode(e.target.value)} disabled={disabled || !fault}>
          {NODES.map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>
        <button
          disabled={disabled || !fault}
          onClick={() => run(() => api.armFault(fault, node), `armed ${fault} on ${node}`)}
        >
          Arm for next take
        </button>
      </div>

      <div className="demo-controls-row">
        <button disabled={disabled} className="secondary" onClick={() => run(() => api.wrapShoot(), 'wrapped')}>
          Wrap shoot
        </button>
      </div>

      {message && <p className="demo-controls-message">{message}</p>}
    </div>
  )
}
