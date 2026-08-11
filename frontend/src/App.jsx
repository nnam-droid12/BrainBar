import { useState } from 'react'
import Header from './components/Header.jsx'
import ProductionWall from './walls/ProductionWall.jsx'
import CrewWall from './walls/CrewWall.jsx'
import { useLiveStream } from './useLiveStream.js'

export default function App() {
  const stream = useLiveStream()
  const [wall, setWall] = useState('production')

  return (
    <div className="app-shell">
      <Header
        scene={stream.scene}
        setupId={stream.setupId}
        takeNumber={stream.takeNumber}
        connected={stream.connected}
        wall={wall}
        onWallChange={setWall}
      />
      <main>{wall === 'production' ? <ProductionWall stream={stream} /> : <CrewWall stream={stream} />}</main>
    </div>
  )
}
