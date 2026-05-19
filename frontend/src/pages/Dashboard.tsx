import { useCallback, useState } from 'react'
import Sidebar from '../components/layout/Sidebar'
import Header from '../components/layout/Header'
import ChatWindow from '../components/chat/ChatWindow'
import AgentPanel from '../components/agents/AgentPanel'
import VoiceOrb from '../components/voice/VoiceOrb'
import { TONE_COLORS } from '../components/voice/VoiceOrb'
import { useAuth } from '../hooks/useAuth'
import { useWebSocket } from '../hooks/useWebSocket'
import { streamAgent } from '../services/ragApi'
import type { RetrievalTrace } from '../services/ragApi'
import type { AgentStatus, Message } from '../types'

function uid() {
  return Math.random().toString(36).slice(2)
}

const INITIAL_STATUSES: AgentStatus[] = [
  { agent_name: 'Planner',    status: 'idle' },
  { agent_name: 'Researcher', status: 'idle' },
  { agent_name: 'Executor',   status: 'idle' },
  { agent_name: 'Critic',     status: 'idle' },
  { agent_name: 'Memory',     status: 'idle' },
]

export default function Dashboard() {
  const { user } = useAuth()
  const clientId = `user-${user?.id ?? 'anonymous'}`
  const { isConnected } = useWebSocket(clientId)
  const [messages, setMessages] = useState<Message[]>([])
  const [agentStatuses, setAgentStatuses] = useState<AgentStatus[]>(INITIAL_STATUSES)
  const [retrievalTrace, setRetrievalTrace] = useState<RetrievalTrace | null>(null)

  // Voice state
  const [voiceTranscript, setVoiceTranscript] = useState('')
  const [voiceTone, setVoiceTone] = useState('')
  const [voiceResponse, setVoiceResponse] = useState('')

  const handleSendMessage = useCallback(async (content: string) => {
    const userMsg: Message = {
      id: uid(),
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, userMsg])

    const assistantId = uid()
    setMessages((prev) => [
      ...prev,
      { id: assistantId, role: 'assistant', content: '', timestamp: new Date().toISOString() },
    ])

    setAgentStatuses(INITIAL_STATUSES)
    setRetrievalTrace(null)

    try {
      for await (const event of streamAgent(content)) {
        if (event.type === 'agent_status') {
          setAgentStatuses((prev) =>
            prev.map((s) =>
              s.agent_name === event.agent
                ? { ...s, status: event.status, message: event.message }
                : s
            )
          )
        } else if (event.type === 'retrieval_trace') {
          setRetrievalTrace(event.trace)
        } else if (event.type === 'chat_token') {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId ? { ...m, content: m.content + event.token } : m
            )
          )
        } else if (event.type === 'error') {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId ? { ...m, content: `Error: ${event.message}`, role: 'system' } : m
            )
          )
        }
      }
    } catch (e: unknown) {
      const errText = (e as Error).message ?? 'Something went wrong'
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId ? { ...m, content: `Error: ${errText}`, role: 'system' } : m
        )
      )
    }
  }, [])

  const handleVoiceTranscript = useCallback((text: string) => {
    setVoiceTranscript(text)
    setVoiceResponse('')
    // also send through the text pipeline so it appears in chat
    if (text.trim()) handleSendMessage(text)
  }, [handleSendMessage])

  const handleVoiceTone = useCallback((tone: string) => {
    setVoiceTone(tone)
  }, [])

  const handleVoiceToken = useCallback((token: string) => {
    setVoiceResponse(prev => prev + token)
  }, [])

  const toneColor = TONE_COLORS[voiceTone] ?? 'text-gray-400'

  return (
    <div className="flex h-screen bg-gray-900 overflow-hidden">
      <Sidebar />
      <div className="flex flex-col flex-1 ml-60 min-w-0">
        <Header title="AI Assistant" isWsConnected={isConnected} />
        <main className="flex flex-1 overflow-hidden">
          <ChatWindow
            messages={messages}
            onSendMessage={handleSendMessage}
            isConnected={true}
            agentStatuses={agentStatuses}
          />
          <AgentPanel statuses={agentStatuses} retrievalTrace={retrievalTrace} />
        </main>
      </div>

      {/* Voice panel — floating bottom-right */}
      <div className="fixed bottom-6 right-6 flex flex-col items-end gap-3 z-50">
        {/* Live voice feedback card */}
        {(voiceTranscript || voiceResponse) && (
          <div className="bg-gray-800 border border-gray-700 rounded-2xl p-3 w-72 text-xs shadow-xl">
            {voiceTranscript && (
              <div className="mb-2">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-gray-500 font-semibold uppercase tracking-wider">You said</span>
                  {voiceTone && (
                    <span className={`text-[10px] font-medium ${toneColor}`}>
                      {voiceTone}
                    </span>
                  )}
                </div>
                <p className="text-gray-200 leading-relaxed">{voiceTranscript}</p>
              </div>
            )}
            {voiceResponse && (
              <div>
                <p className="text-gray-500 font-semibold uppercase tracking-wider mb-1">Response</p>
                <p className="text-gray-300 leading-relaxed">{voiceResponse}</p>
              </div>
            )}
          </div>
        )}

        <VoiceOrb
          onTranscript={handleVoiceTranscript}
          onTone={handleVoiceTone}
          onToken={handleVoiceToken}
        />
      </div>
    </div>
  )
}
