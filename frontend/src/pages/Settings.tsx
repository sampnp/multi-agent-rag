import { useState } from 'react'
import { Settings as SettingsIcon, Trash2, User, Server } from 'lucide-react'
import Sidebar from '../components/layout/Sidebar'
import Header from '../components/layout/Header'
import { useAuth } from '../hooks/useAuth'
import { memoryApi } from '../services/memoryApi'

export default function Settings() {
  const { user, logout } = useAuth()
  const [clearing, setClearing] = useState(false)
  const [cleared, setCleared] = useState(false)

  const handleClearMemory = async () => {
    if (!window.confirm('Clear all memory? This cannot be undone.')) return
    setClearing(true)
    try {
      await memoryApi.clear()
      setCleared(true)
      setTimeout(() => setCleared(false), 3000)
    } finally {
      setClearing(false)
    }
  }

  const INFO = [
    { label: 'LLM', value: 'llama3.1 (Ollama — local, free)' },
    { label: 'Embeddings', value: 'nomic-embed-text (768-dim)' },
    { label: 'Vector DB', value: 'Qdrant' },
    { label: 'Keyword search', value: 'Elasticsearch (BM25)' },
    { label: 'Graph DB', value: 'Neo4j' },
    { label: 'Cache / Memory', value: 'Redis' },
    { label: 'Orchestration', value: 'LangGraph' },
    { label: 'Backend', value: 'FastAPI (Python)' },
    { label: 'Frontend', value: 'React 18 + Vite + Tailwind' },
  ]

  return (
    <div className="flex h-screen bg-gray-900 overflow-hidden">
      <Sidebar />
      <div className="flex flex-col flex-1 ml-60 min-w-0">
        <Header title="Settings" isWsConnected={false} />
        <main className="flex-1 overflow-y-auto px-6 py-6 space-y-8 max-w-2xl">

          {/* Account */}
          <section>
            <div className="flex items-center gap-2 mb-4">
              <User className="w-4 h-4 text-gray-400" />
              <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Account</h2>
            </div>
            <div className="bg-gray-800 border border-gray-700 rounded-xl divide-y divide-gray-700">
              <div className="flex items-center justify-between px-4 py-3">
                <span className="text-sm text-gray-400">Username</span>
                <span className="text-sm text-white font-medium">{user?.username}</span>
              </div>
              <div className="flex items-center justify-between px-4 py-3">
                <span className="text-sm text-gray-400">Email</span>
                <span className="text-sm text-white">{user?.email}</span>
              </div>
              <div className="flex items-center justify-between px-4 py-3">
                <span className="text-sm text-gray-400">Status</span>
                <span className="text-xs bg-green-900/50 text-green-400 border border-green-800 px-2 py-0.5 rounded-full">
                  {user?.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
            </div>
            <button
              onClick={logout}
              className="mt-3 text-sm text-red-400 hover:text-red-300 transition-colors"
            >
              Sign out of this account
            </button>
          </section>

          {/* Memory */}
          <section>
            <div className="flex items-center gap-2 mb-4">
              <SettingsIcon className="w-4 h-4 text-gray-400" />
              <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Memory</h2>
            </div>
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 flex items-start justify-between gap-4">
              <div>
                <p className="text-sm text-white font-medium">Clear All Memory</p>
                <p className="text-xs text-gray-400 mt-0.5">
                  Wipes short-term history, episodic events, vector memories, and the compressed summary.
                </p>
                {cleared && <p className="text-xs text-green-400 mt-1">Memory cleared successfully.</p>}
              </div>
              <button
                onClick={handleClearMemory}
                disabled={clearing}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-red-400 hover:text-red-300 border border-red-900 rounded-lg hover:bg-red-950/30 transition-colors disabled:opacity-50 shrink-0"
              >
                <Trash2 className="w-3.5 h-3.5" />
                {clearing ? 'Clearing…' : 'Clear'}
              </button>
            </div>
          </section>

          {/* Stack */}
          <section>
            <div className="flex items-center gap-2 mb-4">
              <Server className="w-4 h-4 text-gray-400" />
              <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Stack</h2>
            </div>
            <div className="bg-gray-800 border border-gray-700 rounded-xl divide-y divide-gray-700">
              {INFO.map(({ label, value }) => (
                <div key={label} className="flex items-center justify-between px-4 py-2.5">
                  <span className="text-sm text-gray-400">{label}</span>
                  <span className="text-sm text-white">{value}</span>
                </div>
              ))}
            </div>
          </section>

        </main>
      </div>
    </div>
  )
}
