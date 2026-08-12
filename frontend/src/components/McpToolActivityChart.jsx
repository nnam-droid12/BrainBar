import SingleSeriesBarChart from './SingleSeriesBarChart.jsx'

export default function McpToolActivityChart({ data }) {
  if (!data || data.length === 0) {
    return <p className="muted small">No MCP tool calls recorded yet this session.</p>
  }
  const rows = data.map((r) => ({ label: r.tool.replace(/^grafana_/, ''), value: r.count }))
  return <SingleSeriesBarChart data={rows} unit=" calls" formatValue={(v) => `${Math.round(v)}`} />
}
