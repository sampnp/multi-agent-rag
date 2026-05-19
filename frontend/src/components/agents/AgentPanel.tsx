import type { AgentStatus } from '../../types'
import type { RetrievalTrace } from '../../services/ragApi'
import RetrievalBadge from '../retrieval/RetrievalBadge'

const AGENTS = ['Planner', 'Researcher', 'Executor', 'Critic', 'Memory'] as const

const ICONS: Record<string, string> = {
  Planner:    '🗂️',
  Researcher: '🔍',
  Executor:   '⚡',
  Critic:     '🔎',
  Memory:     '💾',
}

interface AgentPanelProps {
  statuses: AgentStatus[]
  retrievalTrace?: RetrievalTrace | null
}

function getStatus(agent: string, statuses: AgentStatus[]) {
  return statuses.find((s) => s.agent_name === agent)
}

function StatusBadge({ status }: { status: AgentStatus['status'] }) {
  const map = {
    idle:    'bg-gray-700 text-gray-400',
    running: 'bg-blue-900/60 text-blue-300',
    done:    'bg-green-900/60 text-green-300',
    error:   'bg-red-900/60 text-red-300',
  }
  return (
    <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full uppercase tracking-wide ${map[status]}`}>
      {status}
    </span>
  )
}

export default function AgentPanel({ statuses, retrievalTrace }: AgentPanelProps) {
  return (
    <aside className="w-60 shrink-0 border-l border-gray-700 bg-gray-900 flex flex-col p-3 gap-2 overflow-y-auto">
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider px-1 mb-1">
        Agent Pipeline
      </p>

      {AGENTS.map((agent) => {
        const s = getStatus(agent, statuses)
        const status = s?.status ?? 'idle'
        const message = s?.message ?? ''

        return (
          <div
            key={agent}
            className={`rounded-xl border px-3 py-2.5 transition-all ${
              status === 'running'
                ? 'border-blue-700 bg-blue-950/40'
                : status === 'done'
                ? 'border-green-800 bg-green-950/30'
                : status === 'error'
                ? 'border-red-800 bg-red-950/30'
                : 'border-gray-700 bg-gray-800/50'
            }`}
          >
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 min-w-0">
                <span className="text-base shrink-0">{ICONS[agent]}</span>
                <span className="text-sm font-medium text-gray-200 truncate">{agent}</span>
              </div>
              <div className="flex items-center gap-1.5 shrink-0">
                {status === 'running' && (
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
                )}
                <StatusBadge status={status} />
              </div>
            </div>
            {message && (
              <p className="text-[11px] text-gray-400 mt-1.5 leading-snug line-clamp-2">{message}</p>
            )}
          </div>
        )
      })}

      {retrievalTrace && (
        <div className="mt-1">
          <RetrievalBadge trace={retrievalTrace} />
        </div>
      )}

      <div className="mt-auto pt-2 border-t border-gray-800">
        <p className="text-[10px] text-gray-600 text-center">Powered by LangGraph + Ollama</p>
      </div>
    </aside>
  )
}
