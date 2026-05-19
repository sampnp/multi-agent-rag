import { useCallback, useEffect, useRef, useState } from 'react'
import type { WSMessage } from '../types'

type Status = 'connecting' | 'connected' | 'disconnected' | 'error'

const WS_URL = import.meta.env.VITE_WS_URL ?? `ws://${window.location.host}`
const MAX_RETRIES = 5

export function useWebSocket(clientId: string) {
  const [messages, setMessages] = useState<WSMessage[]>([])
  const [status, setStatus] = useState<Status>('disconnected')
  const wsRef = useRef<WebSocket | null>(null)
  const retriesRef = useRef(0)
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    setStatus('connecting')
    const ws = new WebSocket(`${WS_URL}/ws/${clientId}`)
    wsRef.current = ws

    ws.onopen = () => {
      setStatus('connected')
      retriesRef.current = 0
    }

    ws.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data)
        setMessages((prev) => [...prev, msg])
      } catch {
        // ignore malformed frames
      }
    }

    ws.onerror = () => setStatus('error')

    ws.onclose = () => {
      setStatus('disconnected')
      if (retriesRef.current < MAX_RETRIES) {
        const delay = Math.min(1000 * 2 ** retriesRef.current, 30000)
        retriesRef.current += 1
        timeoutRef.current = setTimeout(connect, delay)
      }
    }
  }, [clientId])

  useEffect(() => {
    connect()
    return () => {
      timeoutRef.current && clearTimeout(timeoutRef.current)
      wsRef.current?.close()
    }
  }, [connect])

  const sendMessage = useCallback((msg: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg))
    }
  }, [])

  return { messages, sendMessage, isConnected: status === 'connected', status }
}
