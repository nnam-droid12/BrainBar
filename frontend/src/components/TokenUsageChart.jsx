import { useState } from 'react'

const INPUT_COLOR = '#7c3aed'
const OUTPUT_COLOR = '#0d9488'
const BAR_H = 18
const ROW_GAP = 14
const SEGMENT_GAP = 2

function formatTokens(n) {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}K`
  return String(Math.round(n))
}

export default function TokenUsageChart({ data }) {
  const [hover, setHover] = useState(null)

  if (!data || data.length === 0) {
    return <p className="muted small">No token usage recorded yet this session.</p>
  }

  const rows = [...data].sort((a, b) => b.input + b.output - (a.input + a.output))
  const max = Math.max(...rows.map((r) => r.input + r.output), 1)
  const width = 100 // percent-based scale, rendered via CSS width

  return (
    <div className="chart chart-tokens">
      <div className="chart-legend">
        <span className="chart-legend-item">
          <span className="chart-legend-swatch" style={{ background: INPUT_COLOR }} />
          Input tokens
        </span>
        <span className="chart-legend-item">
          <span className="chart-legend-swatch" style={{ background: OUTPUT_COLOR }} />
          Output tokens
        </span>
      </div>
      <div className="chart-rows" style={{ rowGap: ROW_GAP }}>
        {rows.map((r) => {
          const total = r.input + r.output
          const inputPct = (r.input / max) * width
          const outputPct = (r.output / max) * width
          return (
            <div className="chart-row" key={r.agent}>
              <span className="chart-row-label">{r.agent.replace(/_/g, ' ')}</span>
              <div
                className="chart-bar-track"
                style={{ height: BAR_H }}
                onMouseEnter={() => setHover(r.agent)}
                onMouseLeave={() => setHover(null)}
                onFocus={() => setHover(r.agent)}
                onBlur={() => setHover(null)}
                tabIndex={0}
              >
                <div
                  className="chart-bar-segment"
                  style={{
                    width: `${inputPct}%`,
                    background: INPUT_COLOR,
                    marginRight: SEGMENT_GAP,
                  }}
                />
                <div
                  className="chart-bar-segment"
                  style={{ width: `${outputPct}%`, background: OUTPUT_COLOR }}
                />
                {hover === r.agent && (
                  <div className="chart-tooltip">
                    <strong>{formatTokens(total)} tokens</strong>
                    <span>{r.agent.replace(/_/g, ' ')}</span>
                    <span className="chart-tooltip-row">
                      <span className="chart-legend-swatch" style={{ background: INPUT_COLOR }} />
                      input {formatTokens(r.input)}
                    </span>
                    <span className="chart-tooltip-row">
                      <span className="chart-legend-swatch" style={{ background: OUTPUT_COLOR }} />
                      output {formatTokens(r.output)}
                    </span>
                  </div>
                )}
              </div>
              <span className="chart-row-value">{formatTokens(total)}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
