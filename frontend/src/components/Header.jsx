import { Link } from 'react-router-dom'

export default function Header({ scene, setupId, takeNumber, connected, wall, onWallChange }) {
  return (
    <header className="app-header">
      <Link to="/" className="app-header-brand">
        <span className="brand-mark">BRAINBAR</span>
        <span className="brand-sub">virtual production supervisor</span>
      </Link>

      <div className="app-header-status">
        <span className="header-field">
          <label>scene</label>
          <strong>{scene || '—'}</strong>
        </span>
        <span className="header-field">
          <label>setup</label>
          <strong>{setupId || '—'}</strong>
        </span>
        <span className="header-field">
          <label>take</label>
          <strong>{takeNumber || '—'}</strong>
        </span>
        <span className={`connection-dot ${connected ? 'connection-live' : 'connection-down'}`}>
          {connected ? 'LIVE' : 'DISCONNECTED'}
        </span>
      </div>

      <nav className="wall-switch">
        <button className={wall === 'production' ? 'active' : ''} onClick={() => onWallChange('production')}>
          Production Wall
        </button>
        <button className={wall === 'crew' ? 'active' : ''} onClick={() => onWallChange('crew')}>
          Crew Wall
        </button>
      </nav>
    </header>
  )
}
