import { useEffect, useState } from 'react'

const API = (path: string) => ((import.meta as any).env?.VITE_API_BASE || '/api') + path

type Story = {
  story_id: string
  title: string
  state: string
  dor_score: number
  brief: string
}

export default function PlannerBoard() {
  const [stories, setStories] = useState<Story[]>([])
  const [title, setTitle] = useState('')
  const [brief, setBrief] = useState('')
  const [loading, setLoading] = useState(false)

  async function loadStories() {
    setLoading(true)
    try {
      const res = await fetch(API('/planner/stories'))
      const data = await res.json()
      setStories(data.stories || [])
    } catch (err) {
      console.error('Failed to load stories:', err)
    } finally {
      setLoading(false)
    }
  }

  async function createStory() {
    if (!title || !brief) return

    try {
      await fetch(
        API(`/planner/stories?title=${encodeURIComponent(title)}&brief=${encodeURIComponent(brief)}`),
        { method: 'POST' }
      )
      setTitle('')
      setBrief('')
      loadStories()
    } catch (err) {
      console.error('Failed to create story:', err)
    }
  }

  async function transition(storyId: string, event: string) {
    try {
      await fetch(API(`/planner/stories/${storyId}/transition`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event, actor: 'po' }),
      })
      loadStories()
    } catch (err) {
      console.error('Failed to transition:', err)
    }
  }

  useEffect(() => {
    loadStories()
  }, [])

  return (
    <div className="space-y-4">
      {/* Create Story Card */}
      <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="font-medium text-lg mb-4">New Story</h2>
        <div className="space-y-3">
          <input
            className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Story title (e.g., As a user, I want...)"
          />
          <textarea
            className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
            rows={3}
            value={brief}
            onChange={(e) => setBrief(e.target.value)}
            placeholder="Brief description and context"
          />
          <button
            className="w-full px-4 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            onClick={createStory}
            disabled={!title || !brief}
          >
            Create Story
          </button>
        </div>
      </div>

      {/* Stories List */}
      <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-medium text-lg">Stories</h2>
          <button
            className="px-4 py-2 text-sm border border-gray-300 rounded-xl hover:bg-gray-50"
            onClick={loadStories}
            disabled={loading}
          >
            {loading ? 'Loading...' : 'Refresh'}
          </button>
        </div>

        {stories.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <p>No stories yet. Create your first one above!</p>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 gap-4">
            {stories.map((story) => (
              <article
                key={story.story_id}
                className="rounded-xl border border-gray-200 p-4 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1">
                    <h3 className="font-medium text-base">
                      {story.title || story.story_id}
                    </h3>
                    <p className="text-sm text-gray-500 mt-1 line-clamp-2">
                      {story.brief}
                    </p>
                  </div>
                </div>

                <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-100">
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-3 py-1 text-xs font-medium rounded-full ${getStateColor(
                        story.state
                      )}`}
                    >
                      {story.state}
                    </span>
                    <span
                      className={`px-3 py-1 text-xs font-medium rounded-full ${getScoreColor(
                        story.dor_score
                      )}`}
                    >
                      DoR: {story.dor_score}
                    </span>
                  </div>

                  <div className="flex gap-2">
                    <button
                      className="px-3 py-1 text-xs border border-gray-300 rounded-lg hover:bg-gray-50"
                      onClick={() => transition(story.story_id, 'approve_scope')}
                    >
                      Approve
                    </button>
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function getStateColor(state: string): string {
  const colors: Record<string, string> = {
    BACKLOG: 'bg-gray-100 text-gray-700',
    DRAFT: 'bg-yellow-100 text-yellow-700',
    DESIGN: 'bg-blue-100 text-blue-700',
    BUILD: 'bg-purple-100 text-purple-700',
    TEST: 'bg-orange-100 text-orange-700',
    DOCS: 'bg-indigo-100 text-indigo-700',
    DONE: 'bg-green-100 text-green-700',
  }
  return colors[state] || 'bg-gray-100 text-gray-700'
}

function getScoreColor(score: number): string {
  if (score >= 90) return 'bg-green-100 text-green-700'
  if (score >= 75) return 'bg-blue-100 text-blue-700'
  if (score >= 50) return 'bg-yellow-100 text-yellow-700'
  return 'bg-red-100 text-red-700'
}

