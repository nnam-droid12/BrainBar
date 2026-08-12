import { useState } from 'react'

const DEFAULT_COLOR = '#7c3aed'

/**
 * A single-series horizontal bar chart. `data` is [{label, value}], already sorted by
 * the caller. No legend (a single series names itself via the chart title).
 */
export default function SingleSeriesBarChart({ data, color = DEFAULT_COLOR, unit = '', barHeight = 16, formatValue }) {
  const [hover, setHover] = useState(null)

  if (!data || data.length === 0) {
    return <p className="muted small">No data yet.</p>
  }

  const max = Math.max(...data.map((r) => r.value), 1)
  const fmt = formatValue || ((v) => `${Math.round(v * 10) / 10}${unit}`)

  return (
    <div className="chart">
      <div className="chart-rows" style={{ rowGap: 10 }}>
        {data.map((r) => {
          const pct = (r.value / max) * 100
          return (
            <div className="chart-row chart-row-tool" key={r.label}>
              <span className="chart-row-label chart-row-label-tool" title={r.label}>
                {r.label}
              </span>
              <div
                className="chart-bar-track"
                style={{ height: barHeight }}
                onMouseEnter={() => setHover(r.label)}
                onMouseLeave={() => setHover(null)}
                onFocus={() => setHover(r.label)}
                onBlur={() => setHover(null)}
                tabIndex={0}
              >
                <div className="chart-bar-segment" style={{ width: `${pct}%`, background: color }} />
                {hover === r.label && (
                  <div className="chart-tooltip">
                    <strong>{fmt(r.value)}</strong>
                    <span>{r.label}</span>
                  </div>
                )}
              </div>
              <span className="chart-row-value">{fmt(r.value)}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
