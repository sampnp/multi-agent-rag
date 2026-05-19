import { useEffect, useRef, useState } from 'react'
import { Search, Trash2, RefreshCw } from 'lucide-react'
import Sidebar from '../components/layout/Sidebar'
import Header from '../components/layout/Header'
import { memoryApi } from '../services/memoryApi'
import type { MemoryEntry, MemoryStats, SemanticResult } from '../services/memoryApi'

function timeAgo(ts: number): string {
  const diff = (Date.now() / 1000 - ts)
  if (diff < 60) return 'just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

function StatCard({ label, value, sub }: { label: string; value: number | string; sub?: string }) {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl px-5 py-4">
      <p className="text-2xl font-bold text-white">{value}</p>
      <p className="text-sm text-gray-400 mt-0.5">{label}</p>
      {sub && <p className="text-xs text-gray-600 mt-1">{sub}</p>}
    </div>
  )
}

function EntryCard({ entry, score }: { entry: MemoryEntry; score?: number }) {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 space-y-2">
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-medium text-brand-400 leading-snug">{entry.query}</p>
        <div className="flex items-center gap-2 shrink-0">
          {score !== undefined && (
            <span className="text-[10px] bg-purple-900/50 text-purple-300 border border-purple-700 px-2 py-0.5 rounded-full">
              {(score * 100).toFixed(0)}% match
            </span>
          )}
          <span className="text-[10px] text-gray-500">{timeAgo(entry.timestamp)}</span>
        </div>
      </div>
      <p className="text-xs text-gray-400 leading-relaxed line-clamp-3">{entry.response}</p>
    </div>
  )
}

type Tab = 'history' | 'episodes' | 'search'

export default function Memory() {
  const [tab, setTab] = useState<Tab>('history')
  const [stats, setStats] = useState<MemoryStats | null>(null)
  const [history, setHistory] = useState<MemoryEntry[]>([])
  const [episodes, setEpisodes] = useState<MemoryEntry[]>([])
  const [summary, setSummary] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SemanticResult[]>([])
  const [loading, setLoading] = useState(false)
  const [clearing, setClearing] = useState(false)
  const searchRef = useRef<HTMLInputElement>(null)

  const load = async () => {
    setLoading(true)
    try {
      const [s, h, e, sum] = await Promise.all([
        memoryApi.getStats(),
        memoryApi.getHistory(20),
        memoryApi.getEpisodes(30),
        memoryApi.getSummary(),
      ])
      setStats(s)
      setHistory(h.reverse())
      setEpisodes(e)
      setSummary(sum)
    } catch {
      // silently ignore — memory may not be populated yet
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleSearch = async () => {
    if (!searchQuery.trim()) return
    setLoading(true)
    try {
      const results = await memoryApi.search(searchQuery, 5)
      setSearchResults(results)
    } catch {
      setSearchResults([])
    } finally {
      setLoading(false)
    }
  }

  const handleClear = async () => {
    if (!window.confirm('Clear all memory layers? This cannot be undone.')) return
    setClearing(true)
    try {
      await memoryApi.clear()
      await load()
      setSearchResults([])
    } finally {
      setClearing(false)
    }
  }

  const tabs: { id: Tab; label: string }[] = [
    { id: 'history', label: 'Recent History' },
    { id: 'episodes', label: 'Episodes' },
    { id: 'search', label: 'Semantic Search' },
  ]

  return (
    <div className="flex h-screen bg-gray-900 overflow-hidden">
      <Sidebar />
      <div className="flex flex-col flex-1 ml-60 min-w-0">
        <Header title="Memory" isWsConnected={false} />
        <main className="flex-1 overflow-y-auto px-6 py-6 space-y-6">

          {/* Stats row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard label="Short-term turns" value={stats?.short_term_turns ?? '—'} sub="sliding window" />
            <StatCard label="Episodic events" value={stats?.episodic_events ?? '—'} sub="30-day TTL" />
            <StatCard label="Vector memories" value={stats?.vector_memories ?? '—'} sub="semantic index" />
            <StatCard label="Summary" value={stats?.has_summary ? 'Yes' : 'None'} sub="LLM compressed" />
          </div>

          {/* Summary card */}
          {summary && (
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Compressed Summary</p>
              <p className="text-sm text-gray-300 whitespace-pre-wrap leading-relaxed">{summary}</p>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-between">
            <div className="flex gap-1 bg-gray-800 border border-gray-700 rounded-lg p-1">
              {tabs.map((t) => (
                <button
                  key={t.id}
                  onClick={() => setTab(t.id)}
                  className={`px-4 py-1.5 rounded-md text-sm transition-colors ${
                    tab === t.id ? 'bg-brand-600 text-white' : 'text-gray-400 hover:text-white'
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>
            <div className="flex gap-2">
              <button
                onClick={load}
                disabled={loading}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-400 hover:text-white border border-gray-700 rounded-lg hover:bg-gray-800 transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
                Refresh
              </button>
              <button
                onClick={handleClear}
                disabled={clearing}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-red-400 hover:text-red-300 border border-red-900 rounded-lg hover:bg-red-950/30 transition-colors disabled:opacity-50"
              >
                <Trash2 className="w-3.5 h-3.5" />
                Clear All
              </button>
            </div>
          </div>

          {/* Tab content */}
          {tab === 'history' && (
            <div className="space-y-3">
              {history.length === 0 ? (
                <p className="text-sm text-gray-500 text-center py-10">No conversation history yet. Start a chat on the Dashboard.</p>
              ) : (
                history.map((entry, i) => <EntryCard key={i} entry={entry} />)
              )}
            </div>
          )}

          {tab === 'episodes' && (
            <div className="space-y-3">
              {episodes.length === 0 ? (
                <p className="text-sm text-gray-500 text-center py-10">No episodic memories yet.</p>
              ) : (
                episodes.map((entry, i) => <EntryCard key={i} entry={entry} />)
              )}
            </div>
          )}

          {tab === 'search' && (
            <div className="space-y-4">
              <div className="flex gap-3">
                <input
                  ref={searchRef}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  placeholder="Search past conversations semantically…"
                  className="flex-1 bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
                <button
                  onClick={handleSearch}
                  disabled={loading || !searchQuery.trim()}
                  className="flex items-center gap-2 px-4 py-2.5 bg-brand-600 hover:bg-brand-700 disabled:bg-gray-700 text-white text-sm rounded-xl transition-colors disabled:cursor-not-allowed"
                >
                  <Search className="w-4 h-4" />
                  Search
                </button>
              </div>
              <div className="space-y-3">
                {searchResults.length === 0 && searchQuery && !loading && (
                  <p className="text-sm text-gray-500 text-center py-6">No results found.</p>
                )}
                {searchResults.map((r, i) => (
                  <EntryCard key={i} entry={r} score={r.composite_score} />
                ))}
              </div>
            </div>
          )}

        </main>
      </div>
    </div>
  )
}
