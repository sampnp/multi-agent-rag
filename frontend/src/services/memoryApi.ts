import { useAuthStore } from '../store/authStore'

const BASE = import.meta.env.VITE_API_URL ?? ''

function authHeaders(): Record<string, string> {
  const token = useAuthStore.getState().accessToken
  return token ? { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' } : { 'Content-Type': 'application/json' }
}

export interface MemoryEntry {
  query: string
  response: string
  timestamp: number
}

export interface MemoryStats {
  short_term_turns: number
  episodic_events: number
  vector_memories: number
  has_summary: boolean
}

export interface SemanticResult extends MemoryEntry {
  similarity: number
  composite_score: number
}

async function _get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}/api${path}`, { headers: authHeaders() })
  if (!res.ok) throw new Error(`Request failed: ${res.status}`)
  return res.json()
}

async function _post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}/api${path}`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`Request failed: ${res.status}`)
  return res.json()
}

export const memoryApi = {
  getHistory: (limit = 20) =>
    _get<{ history: MemoryEntry[] }>(`/memory/history?limit=${limit}`).then(r => r.history),

  getEpisodes: (limit = 30) =>
    _get<{ episodes: MemoryEntry[] }>(`/memory/episodes?limit=${limit}`).then(r => r.episodes),

  getSummary: () =>
    _get<{ summary: string }>('/memory/summary').then(r => r.summary),

  getStats: () =>
    _get<MemoryStats>('/memory/stats'),

  search: (query: string, limit = 5) =>
    _post<{ results: SemanticResult[] }>('/memory/search', { query, limit }).then(r => r.results),

  clear: () =>
    fetch(`${BASE}/api/memory/clear`, { method: 'DELETE', headers: authHeaders() }).then(r => r.json()),
}
