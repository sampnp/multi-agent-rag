import { useAuthStore } from '../store/authStore'

const BASE = import.meta.env.VITE_API_URL ?? ''

function authHeaders(): Record<string, string> {
  const token = useAuthStore.getState().accessToken
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export interface DocumentRecord {
  id: string
  original_name: string
  status: 'processing' | 'ready' | 'error'
  chunk_count: number
  page_count: number
  error_message: string | null
  created_at: string
}

export const documentsApi = {
  upload: async (file: File): Promise<DocumentRecord> => {
    const form = new FormData()
    form.append('file', file)
    const res = await fetch(`${BASE}/api/documents/upload`, {
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

  list: async (): Promise<DocumentRecord[]> => {
    const res = await fetch(`${BASE}/api/documents/`, {
      headers: authHeaders(),
    })
    if (!res.ok) throw new Error('Failed to fetch documents')
    return res.json()
  },

  delete: async (id: string): Promise<void> => {
    const res = await fetch(`${BASE}/api/documents/${id}`, {
      method: 'DELETE',
      headers: authHeaders(),
    })
    if (!res.ok) throw new Error('Failed to delete document')
  },
}

export interface RetrievalTrace {
  strategies_used: string[]
  reasoning: string
  source_counts: Record<string, number>
  total_results: number
}

export interface MemorySaveInfo {
  short_term_entries: number
  compressed: boolean
  episode_recorded: boolean
  vector_stored: boolean
}

export type AgentEvent =
  | { type: 'agent_status'; agent: string; status: 'running' | 'done' | 'error'; message: string }
  | { type: 'retrieval_trace'; trace: RetrievalTrace }
  | { type: 'memory_saved'; info: MemorySaveInfo }
  | { type: 'chat_token'; token: string }
  | { type: 'stream_start' }
  | { type: 'stream_end' }
  | { type: 'error'; message: string }

export async function* streamAgent(message: string): AsyncGenerator<AgentEvent> {
  const res = await fetch(`${BASE}/api/chat/agent`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ message }),
  })

  if (!res.ok || !res.body) throw new Error('Agent request failed')

  const reader = res.body.getReader()
  const decoder = new TextDecoder()

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    const text = decoder.decode(value, { stream: true })
    for (const line of text.split('\n')) {
      if (!line.startsWith('data: ')) continue
      const data = line.slice(6).trim()
      if (data === '[DONE]') return
      try {
        const raw = JSON.parse(data)
        if (raw.type === 'agent_status') {
          yield {
            type: 'agent_status',
            agent: raw.payload.agent,
            status: raw.payload.status,
            message: raw.payload.message ?? '',
          }
        } else if (raw.type === 'retrieval_trace') {
          yield { type: 'retrieval_trace', trace: raw.payload as RetrievalTrace }
        } else if (raw.type === 'memory_saved') {
          yield { type: 'memory_saved', info: raw.payload as MemorySaveInfo }
        } else if (raw.type === 'chat_token') {
          yield { type: 'chat_token', token: raw.payload.token }
        } else if (raw.type === 'stream_start') {
          yield { type: 'stream_start' }
        } else if (raw.type === 'stream_end') {
          yield { type: 'stream_end' }
        } else if (raw.type === 'error') {
          yield { type: 'error', message: raw.payload.message ?? 'Unknown error' }
        }
      } catch {
        // skip malformed lines
      }
    }
  }
}

export async function* streamRag(message: string): AsyncGenerator<string> {
  const res = await fetch(`${BASE}/api/chat/rag`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ message }),
  })

  if (!res.ok || !res.body) throw new Error('Chat request failed')

  const reader = res.body.getReader()
  const decoder = new TextDecoder()

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    const text = decoder.decode(value, { stream: true })
    for (const line of text.split('\n')) {
      if (!line.startsWith('data: ')) continue
      const data = line.slice(6).trim()
      if (data === '[DONE]') return
      try {
        const parsed = JSON.parse(data)
        if (parsed.token) yield parsed.token
        if (parsed.error) throw new Error(parsed.error)
      } catch {
        // skip malformed lines
      }
    }
  }
}
