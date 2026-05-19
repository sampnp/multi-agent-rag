import Sidebar from '../components/layout/Sidebar'
import Header from '../components/layout/Header'

const PIPELINE = [
  {
    name: 'Planner',
    icon: '🗂️',
    color: 'border-blue-700 bg-blue-950/30',
    badge: 'bg-blue-900/50 text-blue-300',
    description: 'Breaks the user query into 2–3 focused subtasks using llama3.1.',
    outputs: ['Subtask list', 'Memory context hint'],
  },
  {
    name: 'Researcher',
    icon: '🔍',
    color: 'border-purple-700 bg-purple-950/30',
    badge: 'bg-purple-900/50 text-purple-300',
    description: 'Routes the query through the Adaptive Retrieval Engine: vector (Qdrant), keyword (Elasticsearch), graph (Neo4j), or web (DuckDuckGo).',
    outputs: ['Ranked evidence chunks', 'Retrieval trace'],
  },
  {
    name: 'Executor',
    icon: '⚡',
    color: 'border-yellow-700 bg-yellow-950/30',
    badge: 'bg-yellow-900/50 text-yellow-300',
    description: 'Generates a streamed response using context from Researcher + memory layers injected into the prompt.',
    outputs: ['Streamed answer tokens', 'Draft response'],
  },
  {
    name: 'Critic',
    icon: '🔎',
    color: 'border-orange-700 bg-orange-950/30',
    badge: 'bg-orange-900/50 text-orange-300',
    description: 'Evaluates the draft for accuracy, completeness, and clarity. Routes back to Executor for up to 2 revision cycles if quality is insufficient.',
    outputs: ['is_acceptable flag', 'Critique text'],
  },
  {
    name: 'Memory',
    icon: '💾',
    color: 'border-green-700 bg-green-950/30',
    badge: 'bg-green-900/50 text-green-300',
    description: 'Persists the Q&A to all memory layers: short-term (Redis), episodic (sorted set), and vector (Qdrant memory_vectors). Triggers LLM compression when history exceeds 15 turns.',
    outputs: ['Short-term entry', 'Episode record', 'Vector embedding'],
  },
]

const STACK = [
  { label: 'Orchestration', value: 'LangGraph StateGraph' },
  { label: 'LLM', value: 'llama3.1 via Ollama' },
  { label: 'Embeddings', value: 'nomic-embed-text (768-dim)' },
  { label: 'Vector DB', value: 'Qdrant' },
  { label: 'Keyword DB', value: 'Elasticsearch (BM25)' },
  { label: 'Graph DB', value: 'Neo4j' },
  { label: 'Web Search', value: 'DuckDuckGo (free)' },
  { label: 'Memory cache', value: 'Redis' },
]

export default function Agents() {
  return (
    <div className="flex h-screen bg-gray-900 overflow-hidden">
      <Sidebar />
      <div className="flex flex-col flex-1 ml-60 min-w-0">
        <Header title="Agents" isWsConnected={false} />
        <main className="flex-1 overflow-y-auto px-6 py-6 space-y-8">

          {/* Pipeline diagram */}
          <section>
            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">Agent Pipeline</h2>
            <div className="flex flex-col gap-0">
              {PIPELINE.map((agent, i) => (
                <div key={agent.name} className="flex gap-4">
                  {/* Connector column */}
                  <div className="flex flex-col items-center w-8 shrink-0">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-base border-2 ${agent.color}`}>
                      {agent.icon}
                    </div>
                    {i < PIPELINE.length - 1 && (
                      <div className="w-px flex-1 bg-gray-700 my-1" />
                    )}
                  </div>
                  {/* Card */}
                  <div className={`mb-3 flex-1 rounded-xl border px-4 py-3 ${agent.color}`}>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-semibold text-white">{agent.name}</span>
                      {agent.outputs.map((o) => (
                        <span key={o} className={`text-[10px] px-2 py-0.5 rounded-full ${agent.badge}`}>{o}</span>
                      ))}
                    </div>
                    <p className="text-xs text-gray-400 leading-relaxed">{agent.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Routing logic */}
          <section>
            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">Routing Logic</h2>
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 font-mono text-xs text-gray-300 space-y-1">
              <p><span className="text-brand-400">START</span> → Planner → Researcher → Executor → Critic</p>
              <p className="pl-4 text-gray-500">if is_acceptable OR iteration ≥ 2:</p>
              <p className="pl-8"><span className="text-green-400">→ Memory → END</span></p>
              <p className="pl-4 text-gray-500">else:</p>
              <p className="pl-8"><span className="text-yellow-400">→ Executor</span> <span className="text-gray-500">(retry, max 2 cycles)</span></p>
            </div>
          </section>

          {/* Stack */}
          <section>
            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">Technology Stack</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {STACK.map(({ label, value }) => (
                <div key={label} className="bg-gray-800 border border-gray-700 rounded-xl px-4 py-3">
                  <p className="text-[10px] text-gray-500 uppercase tracking-wide mb-0.5">{label}</p>
                  <p className="text-sm text-white font-medium">{value}</p>
                </div>
              ))}
            </div>
          </section>

        </main>
      </div>
    </div>
  )
}
