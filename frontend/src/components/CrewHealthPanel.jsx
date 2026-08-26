import { api } from '../api.js'
import { usePolledData } from '../usePolledData.js'
import TokenUsageChart from './TokenUsageChart.jsx'
import TokenCostChart from './TokenCostChart.jsx'
import McpToolActivityChart from './McpToolActivityChart.jsx'

export default function CrewHealthPanel() {
  const { data } = usePolledData(api.getCrewTelemetry, 15000)

  const hasTokens = data?.tokens_by_agent?.length > 0
  const hasCost = data?.cost_usd_by_agent?.length > 0
  const hasTools = data?.mcp_tool_calls?.length > 0
  const hallucinations = data?.hallucinated_tool_calls_1h ?? 0
  const quotaErrors = data?.pro_quota_errors_10m ?? 0
  const isClean = hallucinations === 0 && quotaErrors === 0
  const totalCost = data?.cost_usd_total ?? 0

  return (
    <div className="panel crew-health-panel">
      <h3>
        Crew Health — token cost &amp; MCP tool activity
        {hasCost && <span className="crew-health-total-cost"> · est. ${totalCost.toFixed(2)} this session</span>}
      </h3>
      {!hasTokens && !hasTools && (
        <p className="muted small">
          No crew activity recorded yet this session — roll a take to see live Gemini
          token usage and Grafana MCP tool-call volume.
        </p>
      )}
      {(hasTokens || hasTools) && (
        <div className={`crew-trust-strip ${isClean ? 'crew-trust-clean' : 'crew-trust-warn'}`}>
          <span className="crew-trust-icon">{isClean ? '✓' : '⚠'}</span>
          <span>
            {isClean
              ? 'Agent trust: clean — no hallucinated tool calls, no Pro-quota errors.'
              : [
                  hallucinations > 0 && `${hallucinations} hallucinated tool call${hallucinations === 1 ? '' : 's'} (1h)`,
                  quotaErrors > 0 && `${quotaErrors} Pro-quota error${quotaErrors === 1 ? '' : 's'} (10m)`,
                ]
                  .filter(Boolean)
                  .join(' · ')}
          </span>
        </div>
      )}
      {hasTokens && (
        <div className="crew-health-section">
          <h4 className="chart-subhead">Token usage by agent</h4>
          <TokenUsageChart data={data.tokens_by_agent} />
        </div>
      )}
      {hasCost && (
        <div className="crew-health-section">
          <h4 className="chart-subhead">Estimated cost by agent</h4>
          <TokenCostChart data={data.cost_usd_by_agent} />
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
