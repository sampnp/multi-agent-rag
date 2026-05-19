import { useAuthStore } from '../store/authStore'

const BASE = import.meta.env.VITE_API_URL ?? ''

function authHeaders(): Record<string, string> {
  const token = useAuthStore.getState().accessToken
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export interface ActionItem {
  task: string
  owner: string
  due: string
  priority: 'high' | 'medium' | 'low'
}

export interface Decision {
  decision: string
  rationale: string
}

export interface Blocker {
  issue: string
  owner: string
  blocks: string
}

export interface SpeakerTurn {
  speaker: string
  start: number
  end: number
  text: string
}

export interface MeetingRecord {
  id: string
  original_name: string
  status: 'processing' | 'ready' | 'error'
  duration_seconds: number | null
  topics: string[]
  action_items: ActionItem[]
  decisions: Decision[]
  blockers: Blocker[]
  speakers: SpeakerTurn[]
  transcript: string | null
  error_message: string | null
  created_at: string
}

export interface JiraIssue {
  task: string
  key: string
  url: string
  status: string
}

async function _get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}/api${path}`, { headers: authHeaders() })
  if (!res.ok) throw new Error(`Request failed: ${res.status}`)
  return res.json()
}

export const meetingsApi = {
  upload: async (file: File): Promise<{ id: string; status: string; original_name: string }> => {
    const form = new FormData()
    form.append('file', file)
    const res = await fetch(`${BASE}/api/meetings/upload`, {
      method: 'POST',
      headers: authHeaders(),
      body: form,
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Upload failed' }))
      throw new Error(err.detail ?? 'Upload failed')
    }
    return res.json()
  },

  list: () => _get<MeetingRecord[]>('/meetings/'),
  get: (id: string) => _get<MeetingRecord>(`/meetings/${id}`),
  getBlockers: () => _get<{ blockers: object[]; decisions: object[] }>('/meetings/blockers'),

  pushToJira: async (id: string): Promise<{ issues: JiraIssue[] }> => {
    const res = await fetch(`${BASE}/api/meetings/${id}/jira`, {
      method: 'POST',
      headers: authHeaders(),
    })
    if (!res.ok) throw new Error('Jira push failed')
    return res.json()
  },

  delete: async (id: string): Promise<void> => {
    await fetch(`${BASE}/api/meetings/${id}`, { method: 'DELETE', headers: authHeaders() })
  },
}
