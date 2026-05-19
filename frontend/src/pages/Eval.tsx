import { useEffect, useState } from 'react'
import { Activity, CheckCircle, Zap, Play, RefreshCw, ChevronDown, ChevronRight } from 'lucide-react'
import Sidebar from '../components/layout/Sidebar'
import Header from '../components/layout/Header'
import { evalApi } from '../services/evalApi'
import type { AgentStat, EvalRun, MetricStat } from '../services/evalApi'

const METRIC_META: Record<string, { label: string; goodAbove: number; color: string }> = {
  faithfulness:       { label: 'Faithfulness',       goodAbove: 0.75, color: 'text-green-400' },
  answer_relevancy:   { label: 'Answer Relevancy',   goodAbove: 0.70, color: 'text-blue-400' },
  context_precision:  { label: 'Context Precision',  goodAbove: 0.65, color: 'text-violet-400' },
  hallucination_score:{ label: 'Hallucination Rate', goodAbove: -1,   color: 'text-red-400' }, // lower is better
}

function ScoreBadge({ value, goodAbove }: { value: number; goodAbove: number }) {
  const isHallucination = goodAbove < 0
  const isGood = isHallucination ? value < 0.25 : value >= goodAbove
  return (
    <span className={`text-lg font-bold tabular-nums ${isGood ? 'text-green-400' : value > 0.5 ? 'text-yellow-400' : 'text-red-400'}`}>
      {(value * 100).toFixed(1)}%
    </span>
  )
}

function MetricCard({ name, stat }: { name: string; stat: MetricStat }) {
  const meta = METRIC_META[name] ?? { label: name, goodAbove: 0.5, color: 'text-gray-400' }
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 flex flex-col gap-2">
      <p className={`text-xs font-semibold uppercase tracking-wider ${meta.color}`}>{meta.label}</p>
      <ScoreBadge value={stat.avg} goodAbove={meta.goodAbove} />
      <p className="text-[11px] text-gray-500">{stat.count} evaluations</p>
      <div className="w-full bg-gray-700 rounded-full h-1.5 mt-1">
        <div
          className={`h-1.5 rounded-full ${stat.avg >= meta.goodAbove ? 'bg-green-500' : stat.avg >= 0.5 ? 'bg-yellow-500' : 'bg-red-500'}`}
          style={{ width: `${Math.min(stat.avg * 100, 100)}%` }}
        />
      </div>
    </div>
  )
}

function AgentRow({ stat }: { stat: AgentStat }) {
  const rate = stat.success_rate
  const rateColor = rate === null ? 'text-gray-500' : rate >= 0.9 ? 'text-green-400' : rate >= 0.7 ? 'text-yellow-400' : 'text-red-400'
  return (
    <tr className="border-t border-gray-700">
      <td className="py-2.5 px-4 text-sm text-white">{stat.agent}</td>
      <td className="py-2.5 px-4 text-sm text-green-400 tabular-nums">{stat.successes}</td>
      <td className="py-2.5 px-4 text-sm text-red-400 tabular-nums">{stat.failures}</td>
      <td className={`py-2.5 px-4 text-sm tabular-nums ${rateColor}`}>
        {rate !== null ? `${(rate * 100).toFixed(1)}%` : '—'}
      </td>
      <td className="py-2.5 px-4 text-sm text-gray-400 tabular-nums">
        {stat.avg_latency_ms > 0 ? `${stat.avg_latency_ms.toFixed(0)}ms` : '—'}
      </td>
    </tr>
  )
}

function RunRow({ run }: { run: EvalRun }) {
  const [open, setOpen] = useState(false)
  const ts = new Date(run.timestamp).toLocaleString()
  const avgScore = Object.values(run.scores).reduce((a, b) => a + b, 0) / Object.keys(run.scores).length

  return (
    <div className="border border-gray-700 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-3 w-full px-4 py-3 text-left hover:bg-gray-800/50 transition-colors"
      >
        {open ? <ChevronDown className="w-3.5 h-3.5 text-gray-500 shrink-0" /> : <ChevronRight className="w-3.5 h-3.5 text-gray-500 shrink-0" />}
        <span className="text-xs text-gray-400 font-mono">{run.run_id.slice(0, 8)}…</span>
        <span className="text-xs text-gray-500 flex-1">{ts}</span>
        <span className="text-xs font-semibold text-brand-400">{(avgScore * 100).toFixed(1)}% avg</span>
      </button>
      {open && (
        <div className="px-4 pb-3 grid grid-cols-2 gap-2 bg-gray-800/30">
          {Object.entries(run.scores).map(([k, v]) => {
            const meta = METRIC_META[k]
            return (
              <div key={k} className="flex items-center justify-between text-xs">
                <span className="text-gray-400">{meta?.label ?? k}</span>
                <ScoreBadge value={v} goodAbove={meta?.goodAbove ?? 0.5} />
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// On-demand scorer
function InlineScorer() {
  const [query, setQuery] = useState('')
  const [response, setResponse] = useState('')
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<Record<string, { score: number; reasoning: string }> | null>(null)
  const [err, setErr] = useState('')

  const run = async () => {
    if (!query.trim() || !response.trim() || running) return
    setRunning(true); setErr(''); setResult(null)
    try {
      const res = await evalApi.scoreOne(query, response)
      setResult(res.scores)
    } catch (e: unknown) {
      setErr((e as Error).message)
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="space-y-3">
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Score a Response On-Demand</p>
      <textarea
        value={query}
        onChange={e => setQuery(e.target.value)}
        placeholder="Question…"
        rows={2}
        className="w-full bg-gray-800 border border-gray-700 rounded-xl px-3 py-2 text-sm text-white placeholder-gray-500 resize-none focus:outline-none focus:ring-2 focus:ring-brand-500"
      />
      <textarea
        value={response}
        onChange={e => setResponse(e.target.value)}
        placeholder="Answer to evaluate…"
        rows={4}
        className="w-full bg-gray-800 border border-gray-700 rounded-xl px-3 py-2 text-sm text-white placeholder-gray-500 resize-none focus:outline-none focus:ring-2 focus:ring-brand-500"
      />
      <button
        onClick={run}
        disabled={running || !query.trim() || !response.trim()}
        className="flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white text-sm font-medium rounded-xl transition-colors"
      >
        {running ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
        {running ? 'Scoring…' : 'Score'}
      </button>
      {err && <p className="text-xs text-red-400">{err}</p>}
      {result && (
        <div className="space-y-2">
          {Object.entries(result).map(([k, v]) => {
            const meta = METRIC_META[k]
            return (
              <div key={k} className="bg-gray-800 border border-gray-700 rounded-xl p-3">
                <div className="flex items-center justify-between mb-1">
                  <span className={`text-xs font-semibold ${meta?.color ?? 'text-gray-400'}`}>{meta?.label ?? k}</span>
                  <ScoreBadge value={v.score} goodAbove={meta?.goodAbove ?? 0.5} />
                </div>
                {v.reasoning && <p className="text-[11px] text-gray-500 leading-snug">{v.reasoning.slice(0, 200)}</p>}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default function Eval() {
  const [metrics, setMetrics] = useState<Record<string, MetricStat>>({})
  const [agents, setAgents] = useState<AgentStat[]>([])
  const [runs, setRuns] = useState<EvalRun[]>([])
  const [loading, setLoading] = useState(true)
  const [benchmarking, setBenchmarking] = useState(false)
  const [benchMsg, setBenchMsg] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const [statsRes, runsRes] = await Promise.all([evalApi.getStats(), evalApi.getRuns()])
      setMetrics(statsRes.metrics)
      setAgents(statsRes.agents)
      setRuns(runsRes.runs)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const runBenchmark = async () => {
    setBenchmarking(true); setBenchMsg('')
    try {
      const res = await evalApi.triggerBenchmark()
      setBenchMsg(`Benchmark started — run ID: ${res.run_id.slice(0, 8)}… (results appear in ~30s)`)
      setTimeout(load, 35000)
    } catch (e: unknown) {
      setBenchMsg((e as Error).message)
    } finally {
      setBenchmarking(false)
    }
  }

  return (
    <div className="flex h-screen bg-gray-900 overflow-hidden">
      <Sidebar />
      <div className="flex flex-col flex-1 ml-60 min-w-0">
        <Header title="Evaluation & Observability" isWsConnected={false} />
        <main className="flex flex-1 overflow-hidden">

          {/* Left panel */}
          <div className="w-80 shrink-0 border-r border-gray-700 flex flex-col p-4 gap-4 overflow-y-auto">
            <InlineScorer />

            <div className="border-t border-gray-700 pt-4 space-y-3">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Benchmark Suite</p>
              <p className="text-[11px] text-gray-500 leading-snug">
                Runs 3 built-in test cases through all 4 RAGAS-equivalent metrics using LLM-as-judge scoring.
              </p>
              <button
                onClick={runBenchmark}
                disabled={benchmarking}
                className="flex items-center gap-2 px-4 py-2 bg-indigo-700 hover:bg-indigo-600 disabled:bg-gray-700 disabled:cursor-not-allowed text-white text-sm font-medium rounded-xl transition-colors w-full justify-center"
              >
                {benchmarking ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                {benchmarking ? 'Running…' : 'Run Default Benchmark'}
              </button>
              {benchMsg && <p className="text-[11px] text-brand-300 leading-snug">{benchMsg}</p>}
            </div>

            <div className="border-t border-gray-700 pt-4 space-y-2">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Observability</p>
              <div className="bg-gray-800 border border-gray-700 rounded-xl p-3 text-xs text-gray-400 space-y-1.5">
                <p className="font-medium text-gray-300">Prometheus + Grafana</p>
                <p>Start the observability stack:</p>
                <code className="text-brand-300 block text-[10px]">docker compose -f docker-compose.observability.yml up -d</code>
                <p className="mt-1">Then open Grafana at <span className="text-brand-300">localhost:3001</span> (admin/admin)</p>
              </div>
              <div className="bg-gray-800 border border-gray-700 rounded-xl p-3 text-xs text-gray-400 space-y-1.5">
                <p className="font-medium text-gray-300">OpenTelemetry / Jaeger</p>
                <p>Set in backend .env:</p>
                <code className="text-brand-300 block text-[10px]">OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317</code>
                <p className="mt-1">Traces at <span className="text-brand-300">localhost:16686</span></p>
              </div>
              <div className="bg-gray-800 border border-gray-700 rounded-xl p-3 text-xs text-gray-400 space-y-1.5">
                <p className="font-medium text-gray-300">LangSmith (optional)</p>
                <p>Set in backend .env:</p>
                <code className="text-brand-300 block text-[10px]">LANGSMITH_API_KEY=ls__...</code>
              </div>
            </div>
          </div>

          {/* Right panel */}
          <div className="flex-1 overflow-y-auto p-5 space-y-6">

            {/* Metric overview */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">RAG Quality Metrics (All-Time Avg)</p>
                <button onClick={load} className="text-xs text-gray-500 hover:text-white flex items-center gap-1">
                  <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} /> Refresh
                </button>
              </div>
              {Object.keys(metrics).length === 0 ? (
                <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 text-center">
                  <Activity className="w-8 h-8 text-gray-700 mx-auto mb-2" />
                  <p className="text-sm text-gray-500">No evaluations yet — run a benchmark or score a response</p>
                </div>
              ) : (
                <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
                  {Object.entries(metrics).map(([k, v]) => <MetricCard key={k} name={k} stat={v} />)}
                </div>
              )}
            </div>

            {/* Agent success rates */}
            <div>
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Agent Success Rates</p>
              <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
                <table className="w-full text-left">
                  <thead>
                    <tr className="border-b border-gray-700">
                      <th className="py-2.5 px-4 text-xs text-gray-500 font-semibold uppercase">Agent</th>
                      <th className="py-2.5 px-4 text-xs text-gray-500 font-semibold uppercase">Successes</th>
                      <th className="py-2.5 px-4 text-xs text-gray-500 font-semibold uppercase">Failures</th>
                      <th className="py-2.5 px-4 text-xs text-gray-500 font-semibold uppercase">Rate</th>
                      <th className="py-2.5 px-4 text-xs text-gray-500 font-semibold uppercase">Avg Latency</th>
                    </tr>
                  </thead>
                  <tbody>
                    {agents.length === 0 ? (
                      <tr><td colSpan={5} className="py-6 text-center text-sm text-gray-500">No agent data yet</td></tr>
                    ) : (
                      agents.map(a => <AgentRow key={a.agent} stat={a} />)
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Benchmark run history */}
            <div>
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Benchmark Run History</p>
              {runs.length === 0 ? (
                <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 text-center">
                  <CheckCircle className="w-8 h-8 text-gray-700 mx-auto mb-2" />
                  <p className="text-sm text-gray-500">No benchmark runs yet</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {runs.map(r => <RunRow key={r.run_id} run={r} />)}
                </div>
              )}
            </div>

          </div>
        </main>
      </div>
    </div>
  )
}
