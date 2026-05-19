import { useCallback, useEffect, useRef, useState } from 'react'
import { Mic, Upload, Trash2, RefreshCw, ExternalLink } from 'lucide-react'
import Sidebar from '../components/layout/Sidebar'
import Header from '../components/layout/Header'
import { meetingsApi } from '../services/meetingsApi'
import type { MeetingRecord, JiraIssue } from '../services/meetingsApi'

const PRIORITY_COLORS = {
  high: 'text-red-400 bg-red-900/30 border-red-800',
  medium: 'text-yellow-400 bg-yellow-900/30 border-yellow-800',
  low: 'text-green-400 bg-green-900/30 border-green-800',
}

function duration(secs: number | null): string {
  if (!secs) return '—'
  const m = Math.floor(secs / 60), s = Math.floor(secs % 60)
  return `${m}m ${s}s`
}

function StatusBadge({ status }: { status: MeetingRecord['status'] }) {
  const map = {
    processing: 'bg-blue-900/50 text-blue-300 border-blue-700',
    ready: 'bg-green-900/50 text-green-300 border-green-700',
    error: 'bg-red-900/50 text-red-300 border-red-700',
  }
  return (
    <span className={`text-[10px] px-2 py-0.5 rounded-full border font-medium ${map[status]}`}>
      {status}
    </span>
  )
}

export default function Voice() {
  const [meetings, setMeetings] = useState<MeetingRecord[]>([])
  const [selected, setSelected] = useState<MeetingRecord | null>(null)
  const [uploading, setUploading] = useState(false)
  const [loading, setLoading] = useState(false)
  const [jiraResults, setJiraResults] = useState<JiraIssue[]>([])
  const [jiraPushing, setJiraPushing] = useState(false)
  const [tab, setTab] = useState<'transcript' | 'actions' | 'decisions' | 'speakers'>('actions')
  const fileRef = useRef<HTMLInputElement>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const loadList = useCallback(async () => {
    setLoading(true)
    try { setMeetings(await meetingsApi.list()) } catch { /* empty */ }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { loadList() }, [loadList])

  // Poll processing meetings every 5 s
  useEffect(() => {
    const hasProcessing = meetings.some(m => m.status === 'processing')
    if (hasProcessing && !pollRef.current) {
      pollRef.current = setInterval(loadList, 5000)
    } else if (!hasProcessing && pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [meetings, loadList])

  const handleUpload = async (file: File) => {
    setUploading(true)
    try {
      await meetingsApi.upload(file)
      await loadList()
    } catch (e: unknown) {
      alert((e as Error).message)
    } finally {
      setUploading(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (file) handleUpload(file)
  }

  const handleSelect = async (m: MeetingRecord) => {
    if (m.status === 'ready') {
      const detail = await meetingsApi.get(m.id).catch(() => m)
      setSelected(detail)
    } else {
      setSelected(m)
    }
    setJiraResults([])
    setTab('actions')
  }

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    await meetingsApi.delete(id).catch(() => {})
    setMeetings(prev => prev.filter(m => m.id !== id))
    if (selected?.id === id) setSelected(null)
  }

  const handleJira = async () => {
    if (!selected) return
    setJiraPushing(true)
    try {
      const res = await meetingsApi.pushToJira(selected.id)
      setJiraResults(res.issues)
    } catch { /* empty */ }
    finally { setJiraPushing(false) }
  }

  return (
    <div className="flex h-screen bg-gray-900 overflow-hidden">
      <Sidebar />
      <div className="flex flex-col flex-1 ml-60 min-w-0">
        <Header title="Meeting Intelligence" isWsConnected={false} />
        <main className="flex flex-1 overflow-hidden">

          {/* Left — upload + list */}
          <div className="w-72 shrink-0 border-r border-gray-700 flex flex-col">
            {/* Drop zone */}
            <div
              onDrop={handleDrop}
              onDragOver={e => e.preventDefault()}
              onClick={() => fileRef.current?.click()}
              className="m-3 border-2 border-dashed border-gray-600 hover:border-brand-500 rounded-xl p-4 text-center cursor-pointer transition-colors"
            >
              {uploading
                ? <p className="text-sm text-blue-400">Uploading…</p>
                : <>
                    <Upload className="w-6 h-6 text-gray-500 mx-auto mb-1" />
                    <p className="text-xs text-gray-400">Drop audio or click to upload</p>
                    <p className="text-[10px] text-gray-600 mt-0.5">mp3 · mp4 · wav · m4a · webm</p>
                  </>
              }
              <input ref={fileRef} type="file" className="hidden"
                accept=".mp3,.mp4,.wav,.m4a,.ogg,.flac,.webm"
                onChange={e => { const f = e.target.files?.[0]; if (f) handleUpload(f) }} />
            </div>

            {/* List header */}
            <div className="flex items-center justify-between px-4 py-2 border-b border-gray-700">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Meetings</p>
              <button onClick={loadList} disabled={loading} className="text-gray-500 hover:text-gray-300">
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              </button>
            </div>

            {/* Meeting list */}
            <div className="flex-1 overflow-y-auto divide-y divide-gray-800">
              {meetings.length === 0 && (
                <p className="text-xs text-gray-500 text-center py-8">No meetings yet.</p>
              )}
              {meetings.map(m => (
                <div key={m.id} onClick={() => handleSelect(m)}
                  className={`flex items-start justify-between gap-2 px-3 py-3 cursor-pointer hover:bg-gray-800/60 transition-colors ${selected?.id === m.id ? 'bg-gray-800' : ''}`}>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <Mic className="w-3 h-3 text-brand-400 shrink-0" />
                      <p className="text-xs text-white truncate">{m.original_name}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <StatusBadge status={m.status} />
                      <span className="text-[10px] text-gray-500">{duration(m.duration_seconds)}</span>
                    </div>
                  </div>
                  <button onClick={(e) => handleDelete(m.id, e)}
                    className="text-gray-600 hover:text-red-400 transition-colors shrink-0 mt-0.5">
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Right — meeting detail */}
          <div className="flex-1 overflow-y-auto p-6">
            {!selected && (
              <div className="flex flex-col items-center justify-center h-full text-center">
                <Mic className="w-12 h-12 text-gray-700 mb-3" />
                <p className="text-gray-500 text-sm">Upload an audio recording to get started</p>
                <p className="text-gray-600 text-xs mt-1">Transcription, speaker diarization, and analysis run locally</p>
              </div>
            )}

            {selected && selected.status === 'processing' && (
              <div className="flex flex-col items-center justify-center h-full text-center gap-3">
                <RefreshCw className="w-8 h-8 text-brand-400 animate-spin" />
                <p className="text-white text-sm font-medium">Processing {selected.original_name}</p>
                <p className="text-gray-400 text-xs">Transcribing → Analysing → Extracting…</p>
              </div>
            )}

            {selected && selected.status === 'error' && (
              <div className="bg-red-950/30 border border-red-800 rounded-xl p-4">
                <p className="text-red-400 font-medium text-sm">Processing failed</p>
                <p className="text-red-300 text-xs mt-1">{selected.error_message}</p>
              </div>
            )}

            {selected && selected.status === 'ready' && (
              <div className="space-y-5 max-w-3xl">
                {/* Header */}
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h2 className="text-lg font-semibold text-white">{selected.original_name}</h2>
                    <p className="text-sm text-gray-400 mt-0.5">
                      Duration: {duration(selected.duration_seconds)} ·{' '}
                      {selected.speakers.length} speaker turns
                    </p>
                  </div>
                  <button onClick={handleJira} disabled={jiraPushing}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-700 hover:bg-blue-600 disabled:bg-gray-700 text-white text-xs rounded-lg transition-colors shrink-0">
                    <ExternalLink className="w-3.5 h-3.5" />
                    {jiraPushing ? 'Pushing…' : 'Push to Jira'}
                  </button>
                </div>

                {/* Topics */}
                {selected.topics.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {selected.topics.map((t, i) => (
                      <span key={i} className="text-xs bg-brand-900/40 text-brand-300 border border-brand-800 px-2.5 py-1 rounded-full">{t}</span>
                    ))}
                  </div>
                )}

                {/* Tabs */}
                <div className="flex gap-1 bg-gray-800 border border-gray-700 rounded-lg p-1 w-fit">
                  {(['actions', 'decisions', 'speakers', 'transcript'] as const).map(t => (
                    <button key={t} onClick={() => setTab(t)}
                      className={`px-3 py-1.5 rounded-md text-xs capitalize transition-colors ${tab === t ? 'bg-brand-600 text-white' : 'text-gray-400 hover:text-white'}`}>
                      {t === 'actions' ? `Actions (${selected.action_items.length})` :
                       t === 'decisions' ? `Decisions (${selected.decisions.length})` :
                       t === 'speakers' ? `Speakers (${new Set(selected.speakers.map(s => s.speaker)).size})` :
                       'Transcript'}
                    </button>
                  ))}
                </div>

                {/* Jira results */}
                {jiraResults.length > 0 && (
                  <div className="bg-gray-800 border border-gray-700 rounded-xl p-3 space-y-1.5">
                    <p className="text-xs font-semibold text-gray-400">Jira Issues Created</p>
                    {jiraResults.map((r, i) => (
                      <div key={i} className="flex items-center justify-between text-xs">
                        <span className="text-gray-300 truncate flex-1">{r.task}</span>
                        <span className="text-brand-400 font-mono ml-3 shrink-0">{r.key}</span>
                        <span className="text-gray-500 ml-2 shrink-0">{r.status}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Tab content */}
                {tab === 'actions' && (
                  <div className="space-y-2">
                    {selected.action_items.length === 0
                      ? <p className="text-sm text-gray-500">No action items extracted.</p>
                      : selected.action_items.map((a, i) => (
                          <div key={i} className="bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 flex items-start justify-between gap-3">
                            <div className="min-w-0">
                              <p className="text-sm text-white">{a.task}</p>
                              <p className="text-xs text-gray-400 mt-0.5">
                                {a.owner && <span className="mr-3">👤 {a.owner}</span>}
                                {a.due && <span>📅 {a.due}</span>}
                              </p>
                            </div>
                            <span className={`text-[10px] px-2 py-0.5 rounded-full border shrink-0 ${PRIORITY_COLORS[a.priority] ?? PRIORITY_COLORS.medium}`}>
                              {a.priority}
                            </span>
                          </div>
                        ))}
                  </div>
                )}

                {tab === 'decisions' && (
                  <div className="space-y-2">
                    {selected.decisions.length === 0
                      ? <p className="text-sm text-gray-500">No decisions extracted.</p>
                      : selected.decisions.map((d, i) => (
                          <div key={i} className="bg-gray-800 border border-gray-700 rounded-xl px-4 py-3">
                            <p className="text-sm text-white font-medium">{d.decision}</p>
                            {d.rationale && <p className="text-xs text-gray-400 mt-1">{d.rationale}</p>}
                          </div>
                        ))}
                    {selected.blockers.length > 0 && (
                      <>
                        <p className="text-xs font-semibold text-red-400 uppercase tracking-wider mt-4">Blockers</p>
                        {selected.blockers.map((b, i) => (
                          <div key={i} className="bg-red-950/30 border border-red-800 rounded-xl px-4 py-3">
                            <p className="text-sm text-red-300 font-medium">{b.issue}</p>
                            <p className="text-xs text-gray-400 mt-1">
                              {b.owner && <span className="mr-3">👤 {b.owner}</span>}
                              {b.blocks && <span>🔒 Blocks: {b.blocks}</span>}
                            </p>
                          </div>
                        ))}
                      </>
                    )}
                  </div>
                )}

                {tab === 'speakers' && (
                  <div className="space-y-2">
                    {selected.speakers.map((s, i) => (
                      <div key={i} className="flex gap-3">
                        <span className="text-xs font-semibold text-brand-400 w-20 shrink-0 pt-0.5">{s.speaker}</span>
                        <div className="flex-1 bg-gray-800 border border-gray-700 rounded-xl px-3 py-2">
                          <p className="text-xs text-gray-300 leading-relaxed">{s.text}</p>
                          <p className="text-[10px] text-gray-600 mt-1">{s.start.toFixed(1)}s – {s.end.toFixed(1)}s</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {tab === 'transcript' && (
                  <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">
                    <p className="text-sm text-gray-300 leading-relaxed whitespace-pre-wrap">
                      {selected.transcript ?? 'No transcript available.'}
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}
