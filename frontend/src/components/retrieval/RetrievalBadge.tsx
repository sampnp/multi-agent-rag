import type { RetrievalTrace } from '../../services/ragApi'

const SOURCE_COLORS: Record<string, string> = {
  vector:  'bg-purple-900/50 text-purple-300 border-purple-700',
  keyword: 'bg-yellow-900/50 text-yellow-300 border-yellow-700',
  graph:   'bg-cyan-900/50 text-cyan-300 border-cyan-700',
  web:     'bg-green-900/50 text-green-300 border-green-700',
}

const SOURCE_ICONS: Record<string, string> = {
  vector:  '⟳',
  keyword: '#',
  graph:   '◎',
  web:     '🌐',
}

interface RetrievalBadgeProps {
  trace: RetrievalTrace
}

export default function RetrievalBadge({ trace }: RetrievalBadgeProps) {
  return (
    <div className="rounded-xl border border-gray-700 bg-gray-800/60 p-3 space-y-2">
      <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">Retrieval Strategy</p>

      <div className="flex flex-wrap gap-1.5">
        {trace.strategies_used.map((s) => (
          <span
            key={s}
            className={`inline-flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded-full border ${SOURCE_COLORS[s] ?? 'bg-gray-700 text-gray-300 border-gray-600'}`}
          >
            <span>{SOURCE_ICONS[s] ?? '?'}</span>
            {s}
            {trace.source_counts[s] !== undefined && (
              <span className="opacity-70">({trace.source_counts[s]})</span>
            )}
          </span>
        ))}
      </div>

      {trace.reasoning && (
        <p className="text-[10px] text-gray-500 leading-snug">{trace.reasoning}</p>
      )}

      <p className="text-[10px] text-gray-600">{trace.total_results} chunks retrieved total</p>
    </div>
  )
}
