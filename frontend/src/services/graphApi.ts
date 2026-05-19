import { useAuthStore } from '../store/authStore'

const BASE = import.meta.env.VITE_API_URL ?? ''

function authHeaders(): Record<string, string> {
  const token = useAuthStore.getState().accessToken
  return token
    ? { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
    : { 'Content-Type': 'application/json' }
}

export interface EntityNode {
  type: string
  name: string
  description: string | null
  created_at: number | null
}

export interface RelationshipRecord {
  from_type: string
  from_name: string
  relation: string
  to_type: string
  to_name: string
  weight: number | null
}

export interface GraphStats {
  stats: Record<string, number>
  total_nodes: number
}

export interface GraphSearchResult {
  cypher: string
  rows: Record<string, string>[]
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

export const graphApi = {
  getStats: () => _get<GraphStats>('/graph/stats'),
  getEntities: (limit = 50) => _get<{ entities: EntityNode[] }>(`/graph/entities?limit=${limit}`).then(r => r.entities),
  getRelationships: (limit = 60) => _get<{ relationships: RelationshipRecord[] }>(`/graph/relationships?limit=${limit}`).then(r => r.relationships),
  search: (query: string) => _post<GraphSearchResult>('/graph/search', { query }),
}
