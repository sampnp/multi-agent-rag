import { useAuthStore } from '../store/authStore'

const BASE = import.meta.env.VITE_API_URL ?? ''

function headers(): Record<string, string> {
  const token = useAuthStore.getState().accessToken
  return token ? { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' } : {}
}

export interface MetricStat {
  avg: number
  count: number
}

export interface AgentStat {
  agent: string
  successes: number
  failures: number
  total: number
  success_rate: number | null
  avg_latency_ms: number
}

export interface EvalRun {
  run_id: string
  timestamp: string
  scores: Record<string, number>
}

export interface ScoreResult {
  query: string
  scores: Record<string, { score: number; reasoning: string }>
}

export const evalApi = {
  getStats: async (): Promise<{ metrics: Record<string, MetricStat>; agents: AgentStat[] }> => {
    const res = await fetch(`${BASE}/api/eval/stats`, { headers: headers() })
    if (!res.ok) throw new Error('Failed to fetch eval stats')
    return res.json()
  },

  getRuns: async (): Promise<{ runs: EvalRun[]; total: number }> => {
    const res = await fetch(`${BASE}/api/eval/runs`, { headers: headers() })
    if (!res.ok) throw new Error('Failed to fetch runs')
    return res.json()
  },

  scoreOne: async (query: string, response: string, contexts: string[] = []): Promise<ScoreResult> => {
    const res = await fetch(`${BASE}/api/eval/score`, {
      method: 'POST',
      headers: headers(),
      body: JSON.stringify({ query, response, contexts }),
    })
    if (!res.ok) throw new Error('Failed to score')
    return res.json()
  },

  triggerBenchmark: async (): Promise<{ run_id: string; status: string }> => {
    const res = await fetch(`${BASE}/api/eval/run`, {
      method: 'POST',
      headers: headers(),
      body: JSON.stringify({ cases: null }),
    })
    if (!res.ok) throw new Error('Failed to trigger benchmark')
    return res.json()
  },
}
