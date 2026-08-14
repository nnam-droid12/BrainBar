// Real LED-volume production footage, not a synthetic stand-in or an interview about
// production: "The Mirage Demo Reel 2025 (Virtual Production Showcase)" — 2D House's
// own upload of finished spots actually shot on their LED volume (a stadium-set
// insurance spot, a car spot), no talking-head/EPK segments anywhere in it. Verified
// by scrubbing the actual embed frame-by-frame before picking these timestamps -
// see the earlier "just an interview" bug this replaced. `end` keeps each loop
// tightly inside one clip instead of drifting into the other segment.
const VIDEOS = [
  { id: '1-BHTEI4y6U', start: 5, end: 48, label: 'Stadium spot — 2D House "The Mirage" LED volume' },
  { id: '1-BHTEI4y6U', start: 50, end: 131, label: 'Genesis GV70 spot — 2D House "The Mirage" LED volume' },
]

export default function StageVolumeFeed({ setupId }) {
  const index = Number(setupId) % VIDEOS.length || 0
  const video = VIDEOS[index] || VIDEOS[0]
  const src = `https://www.youtube.com/embed/${video.id}?autoplay=1&mute=1&loop=1&playlist=${video.id}&controls=0&modestbranding=1&rel=0&start=${video.start}&end=${video.end}`

  return (
    <div className="stage-volume-feed">
      <div className="stage-volume-feed-frame">
        <iframe
          key={`${video.id}-${video.start}`}
          src={src}
          title={video.label}
          frameBorder="0"
          allow="autoplay; encrypted-media"
          allowFullScreen
        />
      </div>
      <p className="stage-volume-feed-caption">
        Real LED-volume production footage ({video.label}) — courtesy 2D House.
        Illustrative: this is the kind of stage BrainBar is built for, not a live feed
        of the take in progress.
      </p>
    </div>
  )
}
