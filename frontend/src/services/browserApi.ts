import { useAuthStore } from '../store/authStore'

const BASE = import.meta.env.VITE_API_URL ?? ''

function authHeaders(): Record<string, string> {
  const token = useAuthStore.getState().accessToken
  return token ? { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' } : {}
}

export interface BrowserTemplate {
  id: string
  name: string
  description: string
  task: string
}

export type BrowserEventType =
  | { type: 'step_start'; payload: { step: number; action: string; detail: Record<string, unknown> } }
  | { type: 'step_done'; payload: { step: number; action: string; result: string } }
  | { type: 'extracted'; payload: { step: number; url: string; data: Record<string, unknown> } }
  | { type: 'report'; payload: { content: string; steps: number } }
  | { type: 'error'; payload: { message: string } }

export const browserApi = {
  getTemplates: async (): Promise<BrowserTemplate[]> => {
    const res = await fetch(`${BASE}/api/browser/templates`, { headers: authHeaders() })
    if (!res.ok) throw new Error('Failed to fetch templates')
    const data = await res.json()
    return data.templates
  },

  async *runTask(task: string): AsyncGenerator<BrowserEventType> {
    const res = await fetch(`${BASE}/api/browser/run`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ task }),
    })
    if (!res.ok || !res.body) throw new Error('Failed to start browser task')

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
          yield JSON.parse(data) as BrowserEventType
        } catch {
          // skip malformed lines
        }
      }
    }
  },
}
