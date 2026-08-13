import { AGENTS, agentStatus, STATUS_LABEL } from '../crewStatus.js'

const INITIALS = {
  continuity: 'CO',
  technical_director: 'TD',
  supervisor: 'SV',
  first_ad: '1AD',
  dit: 'DIT',
}

export default function CrewStatusRow({ take, dailiesReady }) {
  return (
    <div className="crew-status-row">
      {AGENTS.map((agent) => {
        const status = agentStatus(agent.key, take, dailiesReady)
        return (
          <div key={agent.key} className={`crew-chip crew-chip-${status}`}>
            <span className="crew-chip-avatar">{INITIALS[agent.key]}</span>
            <div className="crew-chip-body">
              <span className="crew-chip-name">{agent.label}</span>
              <span className="crew-chip-role">{agent.role}</span>
              <span className="crew-chip-status">
                <span className="crew-chip-dot" />
                {STATUS_LABEL[status]}
              </span>
            </div>
          </div>
        )
      })}
    </div>
  )
}
