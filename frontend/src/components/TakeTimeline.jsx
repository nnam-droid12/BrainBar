import VerdictBadge from './VerdictBadge.jsx'

export default function TakeTimeline({ takes, takesById, selectedId, onSelect }) {
  const ordered = [...takes].reverse()
  return (
    <div className="take-timeline">
      <h3>Take timeline</h3>
      {ordered.length === 0 && <p className="muted small">No takes yet this session.</p>}
      <ul>
        {ordered.map((id) => {
          const t = takesById[id]
          return (
            <li
              key={id}
              className={id === selectedId ? 'take-row take-row-selected' : 'take-row'}
              onClick={() => onSelect(id)}
            >
              <span className="take-row-id">
                {t.scene} · S{t.setup_id} · T{t.take_number}
              </span>
              <VerdictBadge verdict={t.verdict} rolling={t.rolling} error={t.error} size="sm" />
            </li>
          )
        })}
      </ul>
    </div>
  )
}
