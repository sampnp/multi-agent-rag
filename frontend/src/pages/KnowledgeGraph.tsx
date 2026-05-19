import { useEffect, useState } from 'react'
import { Search, RefreshCw } from 'lucide-react'
import Sidebar from '../components/layout/Sidebar'
import Header from '../components/layout/Header'
import { graphApi } from '../services/graphApi'
import type { EntityNode, GraphSearchResult, GraphStats, RelationshipRecord } from '../services/graphApi'

const LABEL_COLORS: Record<string, string> = {
  Person:       'bg-blue-900/50 text-blue-300 border-blue-700',
  Organization: 'bg-purple-900/50 text-purple-300 border-purple-700',
  Project:      'bg-yellow-900/50 text-yellow-300 border-yellow-700',
  Topic:        'bg-green-900/50 text-green-300 border-green-700',
  Concept:      'bg-cyan-900/50 text-cyan-300 border-cyan-700',
  Document:     'bg-gray-700 text-gray-300 border-gray-600',
}

const LABEL_ICONS: Record<string, string> = {
  Person: '👤', Organization: '🏢', Project: '📁', Topic: '🏷️', Concept: '💡', Document: '📄',
}

function TypeBadge({ type }: { type: string }) {
  return (
    <span className={`inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full border font-medium ${LABEL_COLORS[type] ?? 'bg-gray-700 text-gray-300 border-gray-600'}`}>
      <span>{LABEL_ICONS[type] ?? '?'}</span>{type}
    </span>
  )
}

type Tab = 'entities' | 'relationships' | 'search'

export default function KnowledgeGraph() {
  const [stats, setStats] = useState<GraphStats | null>(null)
  const [entities, setEntities] = useState<EntityNode[]>([])
  const [relationships, setRelationships] = useState<RelationshipRecord[]>([])
  const [tab, setTab] = useState<Tab>('entities')
  const [loading, setLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResult, setSearchResult] = useState<GraphSearchResult | null>(null)
  const [searching, setSearching] = useState(false)
  const [filterType, setFilterType] = useState<string>('All')

  const load = async () => {
    setLoading(true)
    try {
      const [s, e, r] = await Promise.all([
        graphApi.getStats(),
        graphApi.getEntities(80),
        graphApi.getRelationships(60),
      ])
      setStats(s)
      setEntities(e)
      setRelationships(r)
    } catch {
      // Neo4j may not be populated yet
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleSearch = async () => {
    if (!searchQuery.trim()) return
    setSearching(true)
    try {
      const result = await graphApi.search(searchQuery)
      setSearchResult(result)
    } catch {
      setSearchResult(null)
    } finally {
      setSearching(false)
    }
  }

  const allTypes = ['All', ...Array.from(new Set(entities.map(e => e.type)))]
  const filteredEntities = filterType === 'All' ? entities : entities.filter(e => e.type === filterType)

  const STAT_LABELS = ['Person', 'Organization', 'Project', 'Topic', 'Concept', 'Document']

  return (
    <div className="flex h-screen bg-gray-900 overflow-hidden">
      <Sidebar />
      <div className="flex flex-col flex-1 ml-60 min-w-0">
        <Header title="Knowledge Graph" isWsConnected={false} />
        <main className="flex-1 overflow-y-auto px-6 py-6 space-y-6">

          {/* Stats */}
          <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
            {STAT_LABELS.map(label => (
              <div key={label} className={`rounded-xl border px-3 py-3 text-center ${LABEL_COLORS[label] ?? 'bg-gray-800 border-gray-700'}`}>
                <p className="text-xl font-bold text-white">{stats?.stats[label] ?? 0}</p>
                <p className="text-[10px] mt-0.5 opacity-80">{LABEL_ICONS[label]} {label}</p>
              </div>
            ))}
          </div>

          {/* Empty state */}
          {stats?.total_nodes === 0 && !loading && (
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 text-center">
              <p className="text-sm text-gray-400">No entities yet. Upload a PDF document to populate the knowledge graph automatically.</p>
            </div>
          )}

          {/* Tabs */}
          <div className="flex items-center justify-between">
            <div className="flex gap-1 bg-gray-800 border border-gray-700 rounded-lg p-1">
              {(['entities', 'relationships', 'search'] as Tab[]).map(t => (
                <button key={t} onClick={() => setTab(t)}
                  className={`px-4 py-1.5 rounded-md text-sm capitalize transition-colors ${tab === t ? 'bg-brand-600 text-white' : 'text-gray-400 hover:text-white'}`}>
                  {t}
                </button>
              ))}
            </div>
            <button onClick={load} disabled={loading}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-400 hover:text-white border border-gray-700 rounded-lg hover:bg-gray-800 transition-colors disabled:opacity-50">
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>

          {/* Entities tab */}
          {tab === 'entities' && (
            <div className="space-y-3">
              {/* Type filter */}
              <div className="flex gap-1.5 flex-wrap">
                {allTypes.map(t => (
                  <button key={t} onClick={() => setFilterType(t)}
                    className={`text-xs px-3 py-1 rounded-full border transition-colors ${filterType === t ? 'bg-brand-600 border-brand-600 text-white' : 'border-gray-700 text-gray-400 hover:text-white hover:border-gray-500'}`}>
                    {t}
                  </button>
                ))}
              </div>
              <div className="grid gap-2">
                {filteredEntities.length === 0 && (
                  <p className="text-sm text-gray-500 text-center py-8">No entities found.</p>
                )}
                {filteredEntities.map((e, i) => (
                  <div key={i} className="flex items-start justify-between gap-3 bg-gray-800 border border-gray-700 rounded-xl px-4 py-3">
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-white truncate">{e.name}</p>
                      {e.description && (
                        <p className="text-xs text-gray-400 mt-0.5 line-clamp-1">{e.description}</p>
                      )}
                    </div>
                    <TypeBadge type={e.type} />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Relationships tab */}
          {tab === 'relationships' && (
            <div className="overflow-x-auto rounded-xl border border-gray-700">
              {relationships.length === 0 ? (
                <p className="text-sm text-gray-500 text-center py-8">No relationships found.</p>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-700 bg-gray-800/60">
                      <th className="text-left px-4 py-2.5 text-xs text-gray-400 font-medium">From</th>
                      <th className="text-left px-4 py-2.5 text-xs text-gray-400 font-medium">Relation</th>
                      <th className="text-left px-4 py-2.5 text-xs text-gray-400 font-medium">To</th>
                      <th className="text-right px-4 py-2.5 text-xs text-gray-400 font-medium">Weight</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-700/50">
                    {relationships.map((r, i) => (
                      <tr key={i} className="hover:bg-gray-800/40 transition-colors">
                        <td className="px-4 py-2.5">
                          <div className="flex items-center gap-2">
                            <TypeBadge type={r.from_type} />
                            <span className="text-white text-xs truncate max-w-[120px]">{r.from_name}</span>
                          </div>
                        </td>
                        <td className="px-4 py-2.5">
                          <span className="text-xs font-mono text-brand-400">{r.relation}</span>
                        </td>
                        <td className="px-4 py-2.5">
                          <div className="flex items-center gap-2">
                            <TypeBadge type={r.to_type} />
                            <span className="text-white text-xs truncate max-w-[120px]">{r.to_name}</span>
                          </div>
                        </td>
                        <td className="px-4 py-2.5 text-right text-xs text-gray-400">{r.weight ?? 1}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}

          {/* NL Search tab */}
          {tab === 'search' && (
            <div className="space-y-4">
              <div className="flex gap-3">
                <input
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleSearch()}
                  placeholder="Ask a relationship question, e.g. 'Who works on the AI project?'"
                  className="flex-1 bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
                <button onClick={handleSearch} disabled={searching || !searchQuery.trim()}
                  className="flex items-center gap-2 px-4 py-2.5 bg-brand-600 hover:bg-brand-700 disabled:bg-gray-700 text-white text-sm rounded-xl transition-colors disabled:cursor-not-allowed">
                  <Search className="w-4 h-4" />
                  {searching ? 'Searching…' : 'Search'}
                </button>
              </div>

              {searchResult && (
                <div className="space-y-3">
                  <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">
                    <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1.5">Generated Cypher</p>
                    <pre className="text-xs text-brand-300 font-mono whitespace-pre-wrap break-all">{searchResult.cypher}</pre>
                  </div>
                  {searchResult.rows.length === 0 ? (
                    <p className="text-sm text-gray-500 text-center py-4">No results returned by this Cypher query.</p>
                  ) : (
                    <div className="overflow-x-auto rounded-xl border border-gray-700">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-gray-700 bg-gray-800/60">
                            {Object.keys(searchResult.rows[0]).map(k => (
                              <th key={k} className="text-left px-4 py-2.5 text-xs text-gray-400 font-medium">{k}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-700/50">
                          {searchResult.rows.map((row, i) => (
                            <tr key={i} className="hover:bg-gray-800/40">
                              {Object.values(row).map((v, j) => (
                                <td key={j} className="px-4 py-2.5 text-xs text-gray-300">{v}</td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

        </main>
      </div>
    </div>
  )
}
