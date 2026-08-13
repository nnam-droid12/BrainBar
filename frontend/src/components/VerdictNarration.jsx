import { useEffect, useRef, useState } from 'react'

// Plays the Supervisor's spoken verdict call (agents/narration.py, Gemini Live API)
// the moment its audio lands over the WebSocket. Keyed on audioUrl so it (re)plays
// exactly once per take, even though the take object otherwise updates in place.
export default function VerdictNarration({ take }) {
  const audioRef = useRef(null)
  const [playing, setPlaying] = useState(false)
  const playedUrlRef = useRef(null)

  useEffect(() => {
    const url = take?.audioUrl
    if (!url || playedUrlRef.current === url) return
    playedUrlRef.current = url
    const el = audioRef.current
    if (!el) return
    el.src = url
    el.play().catch(() => {
      // Autoplay can be blocked before any user gesture on the page; the demo
      // controls (roll take / cut) already provide one in normal use.
    })
  }, [take?.audioUrl])

  if (!take?.audioUrl) return null

  return (
    <div className="verdict-narration">
      <span className={`verdict-narration-dot ${playing ? 'verdict-narration-dot-live' : ''}`} />
      Supervisor calling it{playing ? '…' : ''}
      <audio
        ref={audioRef}
        onPlay={() => setPlaying(true)}
        onEnded={() => setPlaying(false)}
        onPause={() => setPlaying(false)}
      />
    </div>
  )
}
