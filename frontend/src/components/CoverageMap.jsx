const ALL_TYPES = ['master', 'single', 'reverse', 'clean_plate']

export default function CoverageMap({ scene, coverageOwed }) {
  const owed = coverageOwed[scene] || []
  return (
    <div className="coverage-map">
      <h3>Coverage — {scene || '—'}</h3>
      <ul>
        {ALL_TYPES.map((type) => {
          const isOwed = owed.includes(type)
          return (
            <li key={type} className={isOwed ? 'coverage-owed' : 'coverage-captured'}>
              <span className="coverage-dot" />
              {type.replace('_', ' ')}
              <span className="coverage-status">{isOwed ? 'owed' : 'captured'}</span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
