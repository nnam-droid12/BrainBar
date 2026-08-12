import { api } from '../api.js'
import { usePolledData } from '../usePolledData.js'
import TokenUsageChart from './TokenUsageChart.jsx'
import McpToolActivityChart from './McpToolActivityChart.jsx'

export default function CrewHealthPanel() {
  const { data } = usePolledData(api.getCrewTelemetry, 15000)

  const hasTokens = data?.tokens_by_agent?.length > 0
  const hasTools = data?.mcp_tool_calls?.length > 0

  return (
    <div className="panel crew-health-panel">
      <h3>Crew Health — token cost &amp; MCP tool activity</h3>
      {!hasTokens && !hasTools && (
        <p className="muted small">
          No crew activity recorded yet this session — roll a take to see live Gemini
          token usage and Grafana MCP tool-call volume.
        </p>
      )}
      {hasTokens && (
        <div className="crew-health-section">
          <h4 className="chart-subhead">Token usage by agent</h4>
          <TokenUsageChart data={data.tokens_by_agent} />
        </div>
      )}
      {hasTools && (
        <div className="crew-health-section">
          <h4 className="chart-subhead">Grafana MCP tool calls</h4>
          <McpToolActivityChart data={data.mcp_tool_calls} />
        </div>
      )}
    </div>
  )
}
