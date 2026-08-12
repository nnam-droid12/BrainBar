import { api } from '../api.js'
import { usePolledData } from '../usePolledData.js'
import SingleSeriesBarChart from './SingleSeriesBarChart.jsx'

export default function StageHealthPanel() {
  const { data } = usePolledData(api.getStageTelemetry, 10000)

  const frameTime = (data?.frame_time_by_node || [])
    .map((r) => ({ label: r.node, value: r.ms }))
    .sort((a, b) => b.value - a.value)
  const vram = (data?.vram_by_node || [])
    .map((r) => ({ label: r.node, value: r.percent }))
    .sort((a, b) => b.value - a.value)

  const hasData = frameTime.length > 0 || vram.length > 0

  return (
    <div className="panel stage-health-panel">
      <h3>Stage Health</h3>
      {!hasData && (
        <p className="muted small">
          No active telemetry — roll a take to see live render node metrics from Grafana Cloud.
        </p>
      )}
      {frameTime.length > 0 && (
        <div className="stage-health-section">
          <h4 className="chart-subhead">Render frame time (ms, budget 16.6ms)</h4>
          <SingleSeriesBarChart
            data={frameTime}
            color="#7c3aed"
            formatValue={(v) => `${v.toFixed(1)}ms`}
            barHeight={14}
          />
        </div>
      )}
      {vram.length > 0 && (
        <div className="stage-health-section">
          <h4 className="chart-subhead">VRAM utilization</h4>
          <SingleSeriesBarChart
            data={vram}
            color="#0d9488"
            formatValue={(v) => `${v.toFixed(0)}%`}
            barHeight={14}
          />
        </div>
      )}
    </div>
  )
}
