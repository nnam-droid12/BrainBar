const STEPS = [
  { n: '1', text: 'Pick a setup and optionally arm a fault below' },
  { n: '2', text: 'Click Roll take — the stage simulator streams real telemetry live' },
  { n: '3', text: 'Click Cut — the crew above lights up as each agent analyzes the take' },
  { n: '4', text: 'A verdict stamp lands in ~15-60s, with evidence you can inspect below' },
]

export default function OnboardingStrip() {
  return (
    <div className="onboarding-strip">
      <span className="onboarding-strip-label">How to run this demo</span>
      <ol>
        {STEPS.map((s) => (
          <li key={s.n}>
            <span className="onboarding-strip-n">{s.n}</span>
            {s.text}
          </li>
        ))}
      </ol>
    </div>
  )
}
