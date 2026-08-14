import { useEffect, useRef } from 'react'

// Real behind-the-scenes footage of an actual film crew shooting on an LED volume -
// not finished/produced output (a commercial, a movie scene) and not an interview
// about production. Verified by seeking the actual embed to each timestamp and
// confirming, via the player's own reported currentTime (not a guess, not a raw
// DOM currentTime hack that doesn't reliably seek YouTube's segmented player), what
// is actually on screen. Three earlier picks turned out wrong: one video wasn't
// embeddable outside youtube.com at all, one was overwhelmingly interview footage,
// and one (2D House's demo reel) was real and non-interview but shows finished ad
// spots, not the crew/gear/actors mid-shoot - i.e. still not "behind the scenes."
//
// From ILM's "The Virtual Production of The Mandalorian Season Two" - a featurette
// that otherwise cuts fast between interview and finished-shot footage - 269s-278s
// is a confirmed-clean on-set window: crew watching a take on the video-village
// monitors, then the wide reveal of the curved LED wall with the camera crane and
// an actor on the practical floor. Actual gear, actual crew, actual production.
//
// YouTube's `loop=1&playlist=<id>` URL params only loop the *whole* video, not a
// start/end sub-range - after `end` they fall straight back to 0 and keep playing
// forward (confirmed by polling the embed's own currentTime across a full loop
// cycle). Looping a specific window requires the real IFrame Player API: seekTo()
// back to `start` once playback passes `end`.
const VIDEOS = [
  { id: '-gX4N5rDYeQ', start: 269, end: 278, label: 'On the volume floor — ILM, The Mandalorian S2' },
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

export default function StageVolumeFeed({ setupId, narrating = false }) {
  const index = Number(setupId) % VIDEOS.length || 0
  const video = VIDEOS[index] || VIDEOS[0]
  const mountRef = useRef(null)
  const playerRef = useRef(null)

  useEffect(() => {
    let pollId = null
    let cancelled = false

    loadYouTubeApi().then((YT) => {
      if (cancelled || !mountRef.current) return
      playerRef.current = new YT.Player(mountRef.current, {
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
      playerRef.current?.destroy?.()
      playerRef.current = null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [video.id, video.start, video.end])

  // The moment the Supervisor's spoken call starts, restart the loop from its
  // opening frame - the video-village reveal - so what's on screen tracks roughly
  // with "calling it live" instead of looping on whatever offset it happened to be
  // at when the verdict landed.
  useEffect(() => {
    if (narrating) {
      playerRef.current?.seekTo?.(video.start, true)
    }
  }, [narrating, video.start])

  return (
    <div className={`stage-volume-feed ${narrating ? 'stage-volume-feed-live' : ''}`}>
      <div className="stage-volume-feed-frame">
        <div ref={mountRef} />
        {narrating && <span className="stage-volume-feed-live-badge">● CALLING IT</span>}
      </div>
      <p className="stage-volume-feed-caption">
        Real LED-volume production footage ({video.label}). Illustrative: this is the
        kind of stage BrainBar is built for, not a live feed of the take in progress.
      </p>
    </div>
  )
}
