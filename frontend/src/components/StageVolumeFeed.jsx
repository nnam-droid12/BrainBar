import { useEffect, useRef } from 'react'

// Real behind-the-scenes production footage. Two independently-verified sources —
// verified by seeking the actual embed to each timestamp and confirming (via the
// player's own reported currentTime, not by guessing) what's actually on screen.
// Two earlier picks turned out wrong: the first video wasn't embeddable outside
// youtube.com at all, the second was overwhelmingly interview footage that a naive
// frame-sample missed because raw currentTime seeks on the underlying <video>
// element don't reliably land where you tell them to.
//
// Clip A: ILM's "The Virtual Production of The Mandalorian Season Two" cuts almost
// entirely between interview and finished-shot footage, but 269s-278s is a real,
// confirmed-clean on-set window: crew watching a take on the video-village monitors,
// then the wide reveal of the curved LED wall with the camera crane and an actor on
// the practical floor - actual gear, actual crew, actual production.
// Clip B: 2D House's "Mirage Demo Reel" - finished spots actually shot on their LED
// volume, zero interview content anywhere in its runtime.
//
// YouTube's `loop=1&playlist=<id>` URL params only loop the *whole* video, not a
// start/end sub-range - after `end` they fall straight back to 0 and keep playing
// forward (confirmed by polling the embed's own currentTime across a full loop
// cycle). Looping a specific window requires the real IFrame Player API: seekTo()
// back to `start` once playback passes `end`.
const VIDEOS = [
  { id: '-gX4N5rDYeQ', start: 269, end: 278, label: 'On the volume floor — ILM, The Mandalorian S2' },
  { id: '1-BHTEI4y6U', start: 5, end: 48, label: 'Stadium spot — 2D House "The Mirage" LED volume' },
]

let apiPromise = null
function loadYouTubeApi() {
  if (window.YT && window.YT.Player) return Promise.resolve(window.YT)
  if (apiPromise) return apiPromise
  apiPromise = new Promise((resolve) => {
    const prev = window.onYouTubeIframeAPIReady
    window.onYouTubeIframeAPIReady = () => {
      prev?.()
      resolve(window.YT)
    }
    const tag = document.createElement('script')
    tag.src = 'https://www.youtube.com/iframe_api'
    document.head.appendChild(tag)
  })
  return apiPromise
}

export default function StageVolumeFeed({ setupId }) {
  const index = Number(setupId) % VIDEOS.length || 0
  const video = VIDEOS[index] || VIDEOS[0]
  const mountRef = useRef(null)

  useEffect(() => {
    let player = null
    let pollId = null
    let cancelled = false

    loadYouTubeApi().then((YT) => {
      if (cancelled || !mountRef.current) return
      player = new YT.Player(mountRef.current, {
        videoId: video.id,
        playerVars: {
          autoplay: 1,
          mute: 1,
          controls: 0,
          modestbranding: 1,
          rel: 0,
          start: video.start,
          playsinline: 1,
        },
        events: {
          onReady: (e) => {
            e.target.mute()
            e.target.playVideo()
            pollId = setInterval(() => {
              const t = e.target.getCurrentTime?.()
              if (typeof t === 'number' && t >= video.end) {
                e.target.seekTo(video.start, true)
              }
            }, 500)
          },
        },
      })
    })

    return () => {
      cancelled = true
      if (pollId) clearInterval(pollId)
      player?.destroy?.()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [video.id, video.start, video.end])

  return (
    <div className="stage-volume-feed">
      <div className="stage-volume-feed-frame">
        <div ref={mountRef} />
      </div>
      <p className="stage-volume-feed-caption">
        Real LED-volume production footage ({video.label}). Illustrative: this is the
        kind of stage BrainBar is built for, not a live feed of the take in progress.
      </p>
    </div>
  )
}
