// Real LED-volume production footage, not a synthetic stand-in: "The Virtual
// Production of The Mandalorian" — uploaded by Industrial Light & Magic's own
// channel, confirmed embeddable via YouTube's oEmbed endpoint. This is reference
// footage of the real kind of stage BrainBar is built for, not a live feed of the
// take in progress (see the caption below the frame) - the actual live signal in
// this cockpit is the telemetry, the crew status row, and the verdict itself.
const VIDEOS = [
  { id: 'gUnxzVOs3rk', label: 'The Mandalorian, Season 1 — ILM StageCraft' },
  { id: '-gX4N5rDYeQ', label: 'The Mandalorian, Season 2 — ILM StageCraft' },
]

export default function StageVolumeFeed({ setupId }) {
  const index = Number(setupId) % VIDEOS.length || 0
  const video = VIDEOS[index] || VIDEOS[0]
  // start=15 skips a few seconds of title card; adjust per-video once you've
  // eyeballed where the good LED-volume shots actually start.
  const src = `https://www.youtube.com/embed/${video.id}?autoplay=1&mute=1&loop=1&playlist=${video.id}&controls=0&modestbranding=1&rel=0&start=15`

  return (
    <div className="stage-volume-feed">
      <div className="stage-volume-feed-frame">
        <iframe
          key={video.id}
          src={src}
          title={video.label}
          frameBorder="0"
          allow="autoplay; encrypted-media"
          allowFullScreen
        />
      </div>
      <p className="stage-volume-feed-caption">
        Real LED-volume production footage ({video.label}) — courtesy Industrial
        Light &amp; Magic. Illustrative: this is the kind of stage BrainBar is built
        for, not a live feed of the take in progress.
      </p>
    </div>
  )
}
