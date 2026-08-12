import { useState } from 'react'
import { Link } from 'react-router-dom'
import Header from '../components/Header.jsx'
import ProductionWall from '../walls/ProductionWall.jsx'
import CrewWall from '../walls/CrewWall.jsx'
import { useLiveStream } from '../useLiveStream.js'

export default function Dashboard() {
  const stream = useLiveStream()
  const [wall, setWall] = useState('production')

  return (
    <div className="app-shell dashboard-shell">
      <Header
        scene={stream.scene}
        setupId={stream.setupId}
        takeNumber={stream.takeNumber}
        connected={stream.connected}
        wall={wall}
        onWallChange={setWall}
      />
      <main>{wall === 'production' ? <ProductionWall stream={stream} /> : <CrewWall stream={stream} />}</main>
      <Link to="/" className="back-to-landing">
        &larr; BrainBar
      </Link>
    </div>
  )
}
