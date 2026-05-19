export interface User {
  id: string
  email: string
  username: string
  is_active: boolean
  created_at: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
}

export interface AgentStatus {
  agent_name: string
  status: 'idle' | 'running' | 'done' | 'error'
  message?: string
}

export interface WSMessage {
  type: 'chat' | 'agent_status' | 'system' | 'echo' | 'error'
  payload: Record<string, unknown>
}
