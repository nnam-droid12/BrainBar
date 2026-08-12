import { useEffect, useState } from 'react'

/** Polls `fetchFn` every `intervalMs`, starting immediately. Keeps the last good
 * value on the screen through a failed poll rather than clearing it. */
export function usePolledData(fetchFn, intervalMs = 15000) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false

    async function poll() {
      try {
        const result = await fetchFn()
        if (!cancelled) {
          setData(result)
          setError(null)
        }
      } catch (err) {
        if (!cancelled) setError(err)
      }
    }

    poll()
    const id = setInterval(poll, intervalMs)
    return () => {
      cancelled = true
      clearInterval(id)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intervalMs])

  return { data, error }
}
