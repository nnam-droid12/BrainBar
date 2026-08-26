import SingleSeriesBarChart from './SingleSeriesBarChart.jsx'

const COST_COLOR = '#f59e0b'

function formatUsd(v) {
  return v < 0.01 && v > 0 ? '<$0.01' : `$${v.toFixed(2)}`
}

export default function TokenCostChart({ data }) {
  if (!data || data.length === 0) {
    return <p className="muted small">No cost recorded yet this session.</p>
  }
  const rows = data
    .map((r) => ({ label: r.agent.replace(/_/g, ' '), value: r.cost_usd }))
    .sort((a, b) => b.value - a.value)
  return <SingleSeriesBarChart data={rows} color={COST_COLOR} formatValue={formatUsd} />
}
