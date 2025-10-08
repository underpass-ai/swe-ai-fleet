import { useEffect, useState, useCallback } from 'react'
import { useSSE } from './useSSE'

const API = (path: string) => ((import.meta as any).env?.VITE_API_BASE || '/api') + path

export default function ContextViewer() {
  const [storyId, setStoryId] = useState('')
  const [role, setRole] = useState('DEV')
  const [phase, setPhase] = useState('DESIGN')
  const [context, setContext] = useState('')
  const [loading, setLoading] = useState(false)

  const loadContext = useCallback(async () => {
    if (!storyId) return

    setLoading(true)
    try {
      const res = await fetch(API(`/context/${storyId}/${role}/${phase}`))
      const data = await res.json()
      setContext(data.context || JSON.stringify(data, null, 2))
    } catch (err) {
      console.error('Failed to load context:', err)
      setContext('Error loading context')
    } finally {
      setLoading(false)
    }
  }, [storyId, role, phase])

  // SSE live updates
  useSSE(
    storyId ? API(`/events/stream?storyId=${storyId}`) : '',
    useCallback(() => {
      loadContext()
    }, [loadContext])
  )

  useEffect(() => {
    loadContext()
  }, [loadContext])

  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-medium text-lg">Context Viewer</h2>
        <div className="flex items-center gap-2">
          {storyId && (
            <span className="px-2 py-1 text-xs bg-green-100 text-green-700 rounded-full animate-pulse">
              Live
            </span>
          )}
        </div>
      </div>

      <div className="space-y-3">
        <input
          className="w-full px-4 py-2 text-sm border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          placeholder="Story ID (e.g., s-abc123)"
          value={storyId}
          onChange={(e) => setStoryId(e.target.value)}
        />

        <div className="grid grid-cols-2 gap-2">
          <select
            className="px-3 py-2 text-sm border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            value={role}
            onChange={(e) => setRole(e.target.value)}
          >
            <option value="DEV">DEV</option>
            <option value="QA">QA</option>
            <option value="DEVOPS">DEVOPS</option>
            <option value="ARCHITECT">ARCHITECT</option>
          </select>

          <select
            className="px-3 py-2 text-sm border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            value={phase}
            onChange={(e) => setPhase(e.target.value)}
          >
            <option value="DESIGN">DESIGN</option>
            <option value="BUILD">BUILD</option>
            <option value="TEST">TEST</option>
            <option value="DOCS">DOCS</option>
          </select>
        </div>

        <button
          className="w-full px-4 py-2 text-sm bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50"
          onClick={loadContext}
          disabled={!storyId || loading}
        >
          {loading ? 'Loading...' : 'Load Context'}
        </button>
      </div>

      <div className="mt-4">
        <pre className="text-xs whitespace-pre-wrap max-h-[500px] overflow-auto bg-gray-50 border border-gray-200 rounded-xl p-4 font-mono">
          {context || 'No context loaded. Enter a Story ID and click Load Context.'}
        </pre>
      </div>
    </div>
  )
}

