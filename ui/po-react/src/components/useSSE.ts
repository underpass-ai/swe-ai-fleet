import { useEffect, useRef } from 'react'

/**
 * Custom hook for Server-Sent Events (SSE)
 * Automatically reconnects and handles cleanup
 */
export function useSSE(url: string, onMessage: (data: any) => void) {
  const esRef = useRef<EventSource | null>(null)

  useEffect(() => {
    if (!url) return

    const es = new EventSource(url)
    esRef.current = es

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        onMessage(data)
      } catch (err) {
        console.error('Failed to parse SSE message:', err)
      }
    }

    es.onerror = (error) => {
      console.error('SSE error:', error)
      es.close()
    }

    return () => {
      es.close()
    }
  }, [url, onMessage])

  return esRef
}



