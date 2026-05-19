import { useEffect, useRef, useState } from 'react'
import { Globe, Play, ChevronRight, CheckCircle, AlertCircle, Download } from 'lucide-react'
import Sidebar from '../components/layout/Sidebar'
import Header from '../components/layout/Header'
import { browserApi } from '../services/browserApi'
import type { BrowserTemplate } from '../services/browserApi'

const ACTION_ICONS: Record<string, string> = {
  navigate: '🌐',
  search: '🔍',
  click: '👆',
  fill: '✏️',
  scroll_down: '⬇️',
  extract: '📋',
  done: '✅',
}

interface StepEntry {
  step: number
  action: string
  detail: Record<string, unknown>
  result?: string
  status: 'running' | 'done' | 'error'
}

function StepCard({ entry }: { entry: StepEntry }) {
  const icon = ACTION_ICONS[entry.action] ?? '⚡'
  const detailStr = entry.detail.url
    ? String(entry.detail.url)
    : entry.detail.text
    ? String(entry.detail.text)
    : entry.detail.query
    ? String(entry.detail.query)
    : entry.detail.description
    ? String(entry.detail.description)
    : ''

  return (
    <div className={`flex gap-3 items-start rounded-xl border px-4 py-3 text-sm transition-all ${
      entry.status === 'running'
        ? 'border-blue-700 bg-blue-950/30'
        : entry.status === 'error'
        ? 'border-red-700 bg-red-950/20'
        : 'border-gray-700 bg-gray-800/50'
    }`}>
      <div className="flex items-center gap-2 shrink-0 mt-0.5">
        <span className="text-xs text-gray-500 w-5 text-right">{entry.step}</span>
        <span className="text-base">{icon}</span>
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-gray-300 uppercase tracking-wide">{entry.action}</span>
          {entry.status === 'running' && (
            <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
          )}
          {entry.status === 'done' && (
            <CheckCircle className="w-3.5 h-3.5 text-green-400" />
          )}
          {entry.status === 'error' && (
            <AlertCircle className="w-3.5 h-3.5 text-red-400" />
          )}
        </div>
        {detailStr && (
          <p className="text-xs text-blue-300 truncate mt-0.5">{detailStr}</p>
        )}
        {entry.result && (
          <p className="text-xs text-gray-400 mt-1 leading-snug">{entry.result}</p>
        )}
      </div>
    </div>
  )
}

function ExtractedCard({ data, url, step }: { data: Record<string, unknown>; url: string; step: number }) {
  const [expanded, setExpanded] = useState(false)
  return (
    <div className="border border-green-800 bg-green-950/20 rounded-xl p-3">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 w-full text-left"
      >
        <span className="text-xs font-semibold text-green-400">📋 Step {step} — Extracted data</span>
        <span className="text-[10px] text-gray-500 truncate flex-1">{url}</span>
        <ChevronRight className={`w-3.5 h-3.5 text-gray-500 shrink-0 transition-transform ${expanded ? 'rotate-90' : ''}`} />
      </button>
      {expanded && (
        <pre className="mt-2 text-xs text-gray-300 overflow-x-auto whitespace-pre-wrap">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  )
}

export default function Browser() {
  const [templates, setTemplates] = useState<BrowserTemplate[]>([])
  const [task, setTask] = useState('')
  const [running, setRunning] = useState(false)
  const [steps, setSteps] = useState<StepEntry[]>([])
  const [extractions, setExtractions] = useState<Array<{ step: number; url: string; data: Record<string, unknown> }>>([])
  const [report, setReport] = useState('')
  const [error, setError] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    browserApi.getTemplates().then(setTemplates).catch(() => {})
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [steps])

  const handleRun = async () => {
    if (!task.trim() || running) return
    setRunning(true)
    setSteps([])
    setExtractions([])
    setReport('')
    setError('')

    try {
      for await (const event of browserApi.runTask(task)) {
        if (event.type === 'step_start') {
          setSteps(prev => [...prev, {
            step: event.payload.step,
            action: event.payload.action,
            detail: event.payload.detail,
            status: 'running',
          }])
        } else if (event.type === 'step_done') {
          setSteps(prev => prev.map(s =>
            s.step === event.payload.step
              ? { ...s, result: event.payload.result, status: 'done' }
              : s
          ))
        } else if (event.type === 'extracted') {
          setExtractions(prev => [...prev, { step: event.payload.step, url: event.payload.url, data: event.payload.data }])
          setSteps(prev => prev.map(s =>
            s.step === event.payload.step ? { ...s, status: 'done' } : s
          ))
        } else if (event.type === 'report') {
          setReport(event.payload.content)
        } else if (event.type === 'error') {
          setError(event.payload.message)
          setSteps(prev => prev.length > 0
            ? prev.map((s, i) => i === prev.length - 1 ? { ...s, status: 'error' } : s)
            : prev
          )
        }
      }
    } catch (e: unknown) {
      setError((e as Error).message)
    } finally {
      setRunning(false)
    }
  }

  const downloadReport = () => {
    const blob = new Blob([report], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'browser-report.md'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="flex h-screen bg-gray-900 overflow-hidden">
      <Sidebar />
      <div className="flex flex-col flex-1 ml-60 min-w-0">
        <Header title="Browser Agent" isWsConnected={false} />
        <main className="flex flex-1 overflow-hidden">

          {/* Left — task config */}
          <div className="w-80 shrink-0 border-r border-gray-700 flex flex-col p-4 gap-4 overflow-y-auto">
            <div>
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Task Templates</p>
              <div className="space-y-1.5">
                {templates.map(t => (
                  <button key={t.id} onClick={() => setTask(t.task)}
                    className={`w-full text-left px-3 py-2.5 rounded-xl border text-sm transition-colors ${
                      task === t.task
                        ? 'border-brand-600 bg-brand-900/30 text-white'
                        : 'border-gray-700 bg-gray-800/50 text-gray-300 hover:border-gray-600 hover:text-white'
                    }`}>
                    <p className="font-medium text-xs">{t.name}</p>
                    <p className="text-[11px] text-gray-500 mt-0.5 leading-snug">{t.description}</p>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Custom Task</p>
              <textarea
                value={task}
                onChange={e => setTask(e.target.value)}
                placeholder="Describe what the browser agent should do…"
                rows={5}
                className="w-full bg-gray-800 border border-gray-700 rounded-xl px-3 py-2.5 text-sm text-white placeholder-gray-500 resize-none focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>

            <button
              onClick={handleRun}
              disabled={running || !task.trim()}
              className="flex items-center justify-center gap-2 px-4 py-2.5 bg-brand-600 hover:bg-brand-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white text-sm font-medium rounded-xl transition-colors"
            >
              {running ? (
                <>
                  <Globe className="w-4 h-4 animate-pulse" />
                  Browsing…
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  Run Agent
                </>
              )}
            </button>

            <div className="bg-gray-800 border border-gray-700 rounded-xl p-3 text-xs text-gray-500 space-y-1">
              <p className="font-semibold text-gray-400">Requirements</p>
              <p>Run once after pip install:</p>
              <code className="text-brand-300 block">playwright install chromium</code>
            </div>
          </div>

          {/* Right — live feed + results */}
          <div className="flex-1 overflow-y-auto p-5 space-y-4">
            {!running && steps.length === 0 && !report && (
              <div className="flex flex-col items-center justify-center h-full text-center">
                <Globe className="w-12 h-12 text-gray-700 mb-3" />
                <p className="text-gray-500 text-sm">Select a template or write a task, then hit Run</p>
                <p className="text-gray-600 text-xs mt-1">The agent will browse the web autonomously and generate a report</p>
              </div>
            )}

            {/* Error */}
            {error && (
              <div className="bg-red-950/30 border border-red-800 rounded-xl p-4">
                <p className="text-red-400 font-medium text-sm">Error</p>
                <p className="text-red-300 text-xs mt-1 font-mono">{error}</p>
              </div>
            )}

            {/* Steps feed */}
            {steps.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Steps</p>
                {steps.map(s => <StepCard key={s.step} entry={s} />)}
                <div ref={bottomRef} />
              </div>
            )}

            {/* Extracted data */}
            {extractions.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Extracted Data</p>
                {extractions.map((e, i) => (
                  <ExtractedCard key={i} step={e.step} url={e.url} data={e.data} />
                ))}
              </div>
            )}

            {/* Report */}
            {report && (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Generated Report</p>
                  <button onClick={downloadReport}
                    className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-white border border-gray-700 rounded-lg px-2.5 py-1 hover:bg-gray-800 transition-colors">
                    <Download className="w-3.5 h-3.5" />
                    Download .md
                  </button>
                </div>
                <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
                  <pre className="text-sm text-gray-200 whitespace-pre-wrap leading-relaxed font-sans">{report}</pre>
                </div>
              </div>
            )}
          </div>

        </main>
      </div>
    </div>
  )
}
