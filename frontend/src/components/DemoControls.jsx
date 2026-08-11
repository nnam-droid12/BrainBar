import { useState } from 'react'
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

export default function DemoControls() {
  const [setupId, setSetupId] = useState('1')
  const [fault, setFault] = useState('')
  const [node, setNode] = useState('node-6')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')

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

  return (
    <div className="demo-controls">
      <h3>Demo controls</h3>

      <div className="demo-controls-row">
        <select value={setupId} onChange={(e) => setSetupId(e.target.value)}>
          {SETUPS.map((s) => (
            <option key={s} value={s}>
              Setup {s}
            </option>
          ))}
        </select>
        <button
          disabled={busy}
          onClick={() => run(() => api.startTake(setupId), `rolling setup ${setupId}`)}
        >
          Roll take
        </button>
        <button disabled={busy} className="secondary" onClick={() => run(() => api.stopTake(), 'cut')}>
          Cut
        </button>
      </div>

      <div className="demo-controls-row">
        <select value={fault} onChange={(e) => setFault(e.target.value)}>
          {FAULTS.map((f) => (
            <option key={f.value} value={f.value}>
              {f.label}
            </option>
          ))}
        </select>
        <select value={node} onChange={(e) => setNode(e.target.value)} disabled={!fault}>
          {NODES.map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>
        <button
          disabled={busy || !fault}
          onClick={() => run(() => api.armFault(fault, node), `armed ${fault} on ${node}`)}
        >
          Arm for next take
        </button>
      </div>

      <div className="demo-controls-row">
        <button disabled={busy} className="secondary" onClick={() => run(() => api.wrapShoot(), 'wrapped')}>
          Wrap shoot
        </button>
      </div>

      {message && <p className="demo-controls-message">{message}</p>}
    </div>
  )
}
