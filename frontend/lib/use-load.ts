import { useCallback, useEffect, useRef, useState } from "react"

/** Load data on mount, optionally re-poll every `intervalMs`. Polling keeps the last good data on screen. */
export function useLoad<T>(fn: () => Promise<T>, intervalMs?: number) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const fnRef = useRef(fn)
  fnRef.current = fn

  const reload = useCallback(async () => {
    try {
      setData(await fnRef.current())
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    reload()
    if (!intervalMs) return
    const id = setInterval(reload, intervalMs)
    return () => clearInterval(id)
  }, [reload, intervalMs])

  return { data, error, loading, reload }
}
