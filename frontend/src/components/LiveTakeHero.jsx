import { LABELS } from './VerdictBadge.jsx'
import CrewStatusRow from './CrewStatusRow.jsx'

function StatusStamp({ take }) {
  if (!take) {
    return (
      <div className="live-stamp live-stamp-idle">
        <span>STANDING BY</span>
      </div>
    )
  }
  if (take.rolling) {
    return (
      <div className="live-stamp live-stamp-rolling">
        <span className="live-stamp-dot" />
        ROLLING
      </div>
    )
  }
  if (take.error) {
    return (
      <div className="live-stamp live-stamp-verdict live-stamp-error">
        <span>ANALYSIS FAILED</span>
      </div>
    )
  }
  if (!take.verdict) {
    return (
      <div className="live-stamp live-stamp-analyzing">
        <span className="live-stamp-dot" />
        CREW ANALYZING
      </div>
    )
  }
  const key = typeof take.verdict === 'string' ? take.verdict : take.verdict.verdict
  return (
    <div className={`live-stamp live-stamp-verdict live-stamp-${key}`}>
      <span>{LABELS[key] || key}</span>
    </div>
  )
}

export default function LiveTakeHero({ take, dailiesReady }) {
  return (
    <section className="live-hero">
      <div className="live-hero-top">
        <div className="live-hero-info">
          <p className="live-hero-eyebrow">Live take</p>
          <h2 className="live-hero-title">
            {take ? `${take.scene} · Setup ${take.setup_id} · Take ${take.take_number}` : 'No take rolling yet'}
          </h2>
          <p className="live-hero-timecode">
            {take?.start_timecode || '--:--:--:--'} &rarr; {take?.end_timecode || '--:--:--:--'}
          </p>
          {take?.verdict && (
            <p className="live-hero-headline">{take.verdict.headline}</p>
          )}
          {!take && (
            <p className="live-hero-headline muted">
              Pick a setup and click <strong>Roll take</strong> in the demo controls to
              watch the crew analyze a take live.
            </p>
          )}
        </div>
        <StatusStamp take={take} />
      </div>
      <CrewStatusRow take={take} dailiesReady={dailiesReady} />
    </section>
  )
}
