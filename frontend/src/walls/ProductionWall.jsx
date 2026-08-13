import { useEffect, useState } from 'react'
import VerdictCard from '../components/VerdictCard.jsx'
import TakeTimeline from '../components/TakeTimeline.jsx'
import CoverageMap from '../components/CoverageMap.jsx'
import IncidentBanner from '../components/IncidentBanner.jsx'
import DemoControls from '../components/DemoControls.jsx'
import StageHealthPanel from '../components/StageHealthPanel.jsx'
import LiveTakeHero from '../components/LiveTakeHero.jsx'
import OnboardingStrip from '../components/OnboardingStrip.jsx'

const GRAFANA_BASE = import.meta.env.VITE_GRAFANA_BASE_URL

export default function ProductionWall({ stream }) {
  const { takes, takesById, scene, coverageOwed, activeIncident, dailies, report } = stream
  const [selectedId, setSelectedId] = useState(null)

  useEffect(() => {
    if (takes.length > 0) setSelectedId(takes[takes.length - 1])
  }, [takes.length])

  const selected = selectedId ? takesById[selectedId] : null

  return (
    <div className="production-wall-shell">
      <LiveTakeHero take={selected} dailiesReady={!!dailies} />

      <div className="wall production-wall">
        <div className="wall-col wall-col-main">
          <IncidentBanner incident={activeIncident} grafanaBaseUrl={GRAFANA_BASE} />
          <VerdictCard take={selected} />
          <StageHealthPanel />
          {dailies && (
            <div className="dailies-panel">
              <h3>Technical dailies — {dailies.scene}</h3>
              {report && <p className="dailies-report">{report}</p>}
              <ul>
                {dailies.shots.map((shot) => (
                  <li key={shot.take_id}>
                    <strong>{shot.take_id}</strong> — {shot.verdict} — {shot.evidence_summary}
                    {shot.grafana_deeplink && (
                      <a href={shot.grafana_deeplink} target="_blank" rel="noreferrer">
                        {' '}
                        Grafana →
                      </a>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <div className="wall-col wall-col-side">
          <OnboardingStrip />
          <DemoControls />
          <CoverageMap scene={scene} coverageOwed={coverageOwed} />
          <TakeTimeline takes={takes} takesById={takesById} selectedId={selectedId} onSelect={setSelectedId} />
        </div>
      </div>
    </div>
  )
}
