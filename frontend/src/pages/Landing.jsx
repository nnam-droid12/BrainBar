import { Link } from 'react-router-dom'

const STATS = [
  { value: '$200K–$500K', label: 'per day to run a volume stage — the cost of a wasted shoot day' },
  { value: 'Invisible', label: 'in the viewfinder — dropped frames, sync drift, and jitter show up only in the 4K deliverable' },
  { value: 'Weeks later', label: 'is when the damage is usually discovered — after the set is gone' },
]

const STEPS = [
  {
    n: '01',
    title: 'Slate',
    body: 'The stage rolls. Camera tracking, genlock, and the render cluster stream real telemetry into Grafana Cloud for the whole take.',
  },
  {
    n: '02',
    title: 'Cut',
    body: 'On cut, the Technical Director and Continuity analyze the take in parallel — one against live Grafana telemetry, one against the script and shot list.',
  },
  {
    n: '03',
    title: 'Verdict',
    body: 'The Supervisor fuses both into a single call — circle, hold, reshoot, or fixable-in-post — with timecoded evidence, not a guess.',
  },
  {
    n: '04',
    title: 'Action',
    body: 'The First AD pre-stages the corrective take, opens a Grafana incident if hardware failed, and annotates the dashboard — before the crew moves on.',
  },
  {
    n: '05',
    title: 'Dailies',
    body: 'The DIT hands editorial a technical-dailies package with a Grafana deep-link per shot, and the Supervisor writes the end-of-day report.',
  },
]

const CREW = [
  { role: 'Supervisor', tag: 'Root agent', body: "Synthesizes the circle-take call and self-governs its own model routing against a latency budget." },
  { role: 'Continuity', tag: 'Creative intent', body: 'Grounded on the script, shot list, and storyboards — tracks what’s captured vs. still owed.' },
  { role: 'Technical Director', tag: 'Telemetry', body: 'Diagnoses frame drops, VRAM, sync drift, and jitter straight from Grafana Cloud.' },
  { role: 'First AD', tag: 'Action', body: 'Pre-stages reshoots, opens Grafana incidents, silences alert storms, annotates the dashboard.' },
  { role: 'DIT', tag: 'Handoff', body: 'Compiles technical dailies with a Grafana deep-link per shot and the end-of-day report.' },
]

const GCP_SERVICES = [
  'Gemini Enterprise Agent Platform (ADK)',
  'Gemini Pro & Flash',
  'RAG Engine + Vector Search',
  'Document AI',
  'Memory Bank',
  'Agent Engine',
  'Cloud Run',
  'Cloud Storage',
  'BigQuery',
]

const GRAFANA_SURFACE = [
  'Metrics (Mimir)',
  'Logs (Loki)',
  'Traces (Tempo)',
  'Dashboards',
  'Alerting & Incidents (IRM)',
  'AI Observability',
  'Grafana MCP server',
]

export default function Landing() {
  return (
    <div className="landing">
      <header className="landing-nav">
        <span className="landing-brand">BrainBar</span>
        <nav className="landing-nav-links">
          <a href="#how-it-works">How it works</a>
          <a href="#crew">The crew</a>
          <a href="#stack">Stack</a>
          <Link to="/dashboard" className="landing-nav-cta">
            View Dashboard
          </Link>
        </nav>
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
            View Dashboard
          </Link>
          <a href="#how-it-works" className="landing-cta-ghost">
            See how it works
          </a>
        </div>
      </section>

      <section className="landing-problem">
        <div className="landing-section-head">
          <p className="landing-eyebrow">The problem</p>
          <h2>The take looked perfect. It wasn't.</h2>
        </div>
        <div className="landing-problem-grid">
          {STATS.map((s) => (
            <div className="landing-problem-card" key={s.value}>
              <span className="landing-stat">{s.value}</span>
              <p>{s.label}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="landing-steps" id="how-it-works">
        <div className="landing-section-head">
          <p className="landing-eyebrow">How it works</p>
          <h2>One closed loop, every take</h2>
          <p className="landing-section-sub">
            From slate to dailies, the crew fuses live stage telemetry with the shot's
            creative intent — and takes real action on what it finds.
          </p>
        </div>
        <ol className="landing-steps-list">
          {STEPS.map((step) => (
            <li key={step.n} className="landing-step">
              <span className="landing-step-n">{step.n}</span>
              <div>
                <h3>{step.title}</h3>
                <p>{step.body}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="landing-crew" id="crew">
        <div className="landing-section-head">
          <p className="landing-eyebrow">The crew</p>
          <h2>Five agents, one verdict</h2>
        </div>
        <div className="landing-crew-grid">
          {CREW.map((c) => (
            <div className="crew-card" key={c.role}>
              <span className="crew-card-tag">{c.tag}</span>
              <h3>{c.role}</h3>
              <p>{c.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="landing-loop">
        <div className="landing-loop-inner">
          <p className="landing-eyebrow">The closed loop</p>
          <h2>The crew watches the shoot — and watches itself</h2>
          <p className="landing-section-sub">
            Every Gemini call and every Grafana MCP tool call the crew makes is itself
            exported as telemetry into the same Grafana Cloud stack it queries. The
            Supervisor reads that data back before every take to stay inside an on-set
            latency budget, routing routine takes to a fast model and hero shots to a
            stronger one.
          </p>
        </div>
      </section>

      <section className="landing-stack" id="stack">
        <div className="landing-section-head">
          <p className="landing-eyebrow">Built on</p>
          <h2>Real infrastructure, called at runtime</h2>
        </div>
        <div className="landing-stack-grid">
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
        </div>
      </section>

      <section className="landing-final-cta">
        <h2>See the circle-take call in action.</h2>
        <p>Step through a scripted shoot, trigger a fault, and watch the crew respond.</p>
        <Link to="/dashboard" className="landing-cta-primary">
          View Dashboard
        </Link>
      </section>

      <footer className="landing-footer">
        <span className="landing-brand">BrainBar</span>
        <a
          href="https://github.com/nnam-droid12/BrainBar"
          target="_blank"
          rel="noreferrer"
          className="landing-footer-link"
        >
          Source on GitHub
        </a>
        <span className="landing-footer-meta">Apache-2.0</span>
      </footer>
    </div>
  )
}
