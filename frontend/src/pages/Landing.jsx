import { Link } from 'react-router-dom'

const GCP_SERVICES = [
  'Gemini Enterprise Agent Platform (ADK)',
  'Gemini Pro & Flash',
  'RAG Engine + Vector Search',
  'Document AI',
  'Memory Bank',
  'Agent Engine',
  'Cloud Run',
  'Cloud Storage',
]

const GRAFANA_SURFACE = [
  'Metrics (Mimir)',
  'Logs (Loki)',
  'Traces (Tempo)',
  'Dashboards',
  'Alerting & Incidents (IRM)',
  'AI Observability',
]

export default function Landing() {
  return (
    <div className="landing">
      <header className="landing-nav">
        <span className="landing-brand">BrainBar</span>
        <Link to="/dashboard" className="landing-nav-cta">
          Launch Cockpit
        </Link>
      </header>

      <section className="landing-hero">
        <p className="landing-eyebrow">Autonomous virtual-production supervisor</p>
        <h1>
          Did we actually get it —<br />
          technically and creatively?
        </h1>
        <p className="landing-sub">
          A five-agent crew that fuses a shot's creative intent with the take's live
          telemetry on an LED-volume stage, and answers that question before the crew
          moves on. It circles clean takes, holds broken ones with evidence, pre-stages
          the reshoot, and hands editorial a technical-dailies package with a Grafana
          deep-link for every shot.
        </p>
        <div className="landing-cta-row">
          <Link to="/dashboard" className="landing-cta-primary">
            Launch Cockpit →
          </Link>
        </div>
      </section>

      <section className="landing-problem">
        <div className="landing-problem-card">
          <span className="landing-stat">$200K–$500K</span>
          <p>per day to run a volume stage — the cost of a wasted shoot day</p>
        </div>
        <div className="landing-problem-card">
          <span className="landing-stat">Invisible</span>
          <p>in the viewfinder — dropped frames, sync drift, and jitter show up only in the 4K deliverable</p>
        </div>
        <div className="landing-problem-card">
          <span className="landing-stat">Weeks later</span>
          <p>is when the damage is usually discovered — after the set is gone</p>
        </div>
      </section>

      <section className="landing-crew">
        <h2>The crew</h2>
        <div className="landing-crew-grid">
          <div className="crew-card">
            <h3>Supervisor</h3>
            <p>Synthesizes the circle-take call and self-governs model routing against its own latency budget.</p>
          </div>
          <div className="crew-card">
            <h3>Continuity</h3>
            <p>Grounded on the script, shot list, and storyboards — tracks what's captured vs. still owed.</p>
          </div>
          <div className="crew-card">
            <h3>Technical Director</h3>
            <p>Diagnoses frame drops, VRAM, sync drift, and jitter straight from Grafana Cloud telemetry.</p>
          </div>
          <div className="crew-card">
            <h3>First AD</h3>
            <p>Pre-stages the reshoot, opens Grafana incidents, silences alert storms, annotates the dashboard.</p>
          </div>
          <div className="crew-card">
            <h3>DIT</h3>
            <p>Compiles technical dailies with a Grafana deep-link per shot and the end-of-day report.</p>
          </div>
        </div>
      </section>

      <section className="landing-stack">
        <div className="landing-stack-col">
          <h4>Google Cloud</h4>
          <ul>
            {GCP_SERVICES.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </div>
        <div className="landing-stack-col">
          <h4>Grafana</h4>
          <ul>
            {GRAFANA_SURFACE.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </div>
      </section>

      <footer className="landing-footer">
        <Link to="/dashboard" className="landing-cta-secondary">
          Enter the control room →
        </Link>
      </footer>
    </div>
  )
}
