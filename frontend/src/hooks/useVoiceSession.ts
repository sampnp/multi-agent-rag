/**
 * Manages the full voice session lifecycle:
 *  - WebSocket connection to /ws/voice
 *  - MediaRecorder audio capture (WebM/Opus)
 *  - Silence detection via AnalyserNode (auto-stop after 1.5s silence)
 *  - AudioContext playback of TTS MP3 chunks (base64 → ArrayBuffer)
 *  - Barge-in: stops TTS and restarts recording
 */
import { useCallback, useEffect, useRef, useState } from 'react'

const WS_URL = (import.meta.env.VITE_WS_URL ?? `ws://${window.location.host}`) + '/ws/voice'

export type VoiceState = 'idle' | 'connecting' | 'listening' | 'processing' | 'speaking' | 'error'

export interface VoiceSessionHandlers {
  onTranscript?: (text: string) => void
  onTone?: (tone: string) => void
  onToken?: (token: string) => void
}

export function useVoiceSession(handlers: VoiceSessionHandlers = {}) {
  const [voiceState, setVoiceState] = useState<VoiceState>('idle')
  const [error, setError] = useState<string | null>(null)

  const wsRef = useRef<WebSocket | null>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])
  const audioCtxRef = useRef<AudioContext | null>(null)
  const ttsBufferRef = useRef<Uint8Array[]>([])
  const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const silenceRafRef = useRef<number | null>(null)
  const isRecordingRef = useRef(false)

  const handlersRef = useRef(handlers)
  handlersRef.current = handlers

  // ---------- WebSocket helpers ----------

  const sendJson = useCallback((data: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
    }
  }, [])

  // ---------- TTS playback ----------

  const playTtsChunk = useCallback(async (base64: string) => {
    if (!audioCtxRef.current) {
      audioCtxRef.current = new AudioContext()
    }
    const ctx = audioCtxRef.current
    if (ctx.state === 'suspended') await ctx.resume()

    const bytes = Uint8Array.from(atob(base64), c => c.charCodeAt(0))
    ttsBufferRef.current.push(bytes)
  }, [])

  const flushTtsBuffer = useCallback(async () => {
    if (!audioCtxRef.current || ttsBufferRef.current.length === 0) return
    const ctx = audioCtxRef.current
    const combined = new Uint8Array(
      ttsBufferRef.current.reduce((acc, c) => acc + c.length, 0)
    )
    let offset = 0
    for (const chunk of ttsBufferRef.current) {
      combined.set(chunk, offset)
      offset += chunk.length
    }
    ttsBufferRef.current = []
    try {
      const buffer = await ctx.decodeAudioData(combined.buffer)
      const source = ctx.createBufferSource()
      source.buffer = buffer
      source.connect(ctx.destination)
      source.start()
    } catch {
      // MP3 streaming may produce partial decode errors — ignore
    }
  }, [])

  // ---------- Silence detection ----------

  const stopSilenceDetection = useCallback(() => {
    if (silenceRafRef.current) {
      cancelAnimationFrame(silenceRafRef.current)
      silenceRafRef.current = null
    }
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current)
      silenceTimerRef.current = null
    }
  }, [])

  const startSilenceDetection = useCallback((stream: MediaStream) => {
    if (!audioCtxRef.current) audioCtxRef.current = new AudioContext()
    const ctx = audioCtxRef.current
    const source = ctx.createMediaStreamSource(stream)
    const analyser = ctx.createAnalyser()
    analyser.fftSize = 512
    source.connect(analyser)
    analyserRef.current = analyser
    const data = new Uint8Array(analyser.frequencyBinCount)

    const check = () => {
      if (!isRecordingRef.current) return
      analyser.getByteFrequencyData(data)
      const avg = data.reduce((a, b) => a + b, 0) / data.length

      if (avg < 8) {
        if (!silenceTimerRef.current) {
          silenceTimerRef.current = setTimeout(() => {
            stopRecording()
          }, 1500)
        }
      } else {
        if (silenceTimerRef.current) {
          clearTimeout(silenceTimerRef.current)
          silenceTimerRef.current = null
        }
      }
      silenceRafRef.current = requestAnimationFrame(check)
    }
    silenceRafRef.current = requestAnimationFrame(check)
  }, []) // eslint-disable-line

  // ---------- Recording ----------

  const stopRecording = useCallback(() => {
    isRecordingRef.current = false
    stopSilenceDetection()
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop()
    }
  }, [stopSilenceDetection])

  const startRecording = useCallback(async () => {
    if (isRecordingRef.current) return
    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch {
      setError('Microphone access denied')
      setVoiceState('error')
      return
    }

    audioChunksRef.current = []
    const mr = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' })
    mediaRecorderRef.current = mr
    isRecordingRef.current = true

    mr.ondataavailable = (e) => {
      if (e.data.size > 0) audioChunksRef.current.push(e.data)
    }

    mr.onstop = async () => {
      stream.getTracks().forEach(t => t.stop())
      isRecordingRef.current = false

      const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
      const arrayBuffer = await blob.arrayBuffer()
      const bytes = new Uint8Array(arrayBuffer)
      const base64 = btoa(String.fromCharCode(...bytes))
      sendJson({ type: 'audio_chunk', data: base64, is_last: true })
    }

    mr.start(100)
    startSilenceDetection(stream)
  }, [sendJson, startSilenceDetection])

  // ---------- Barge-in ----------

  const bargeIn = useCallback(() => {
    sendJson({ type: 'barge_in' })
    ttsBufferRef.current = []
  }, [sendJson])

  // ---------- Toggle ----------

  const toggle = useCallback(() => {
    if (voiceState === 'idle') {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        // connect then start
        setVoiceState('connecting')
        const ws = new WebSocket(WS_URL)
        wsRef.current = ws

        ws.onopen = () => {
          setVoiceState('idle')
          startRecording()
        }

        ws.onmessage = async (e) => {
          let msg: Record<string, unknown>
          try { msg = JSON.parse(e.data as string) } catch { return }

          const type = msg.type as string
          if (type === 'state') {
            setVoiceState(msg.state as VoiceState)
          } else if (type === 'transcript') {
            handlersRef.current.onTranscript?.(msg.text as string)
          } else if (type === 'tone') {
            handlersRef.current.onTone?.(msg.tone as string)
          } else if (type === 'agent_token') {
            handlersRef.current.onToken?.(msg.token as string)
          } else if (type === 'tts_chunk') {
            await playTtsChunk(msg.data as string)
          } else if (type === 'tts_done') {
            await flushTtsBuffer()
          } else if (type === 'error') {
            setError(msg.message as string)
          }
        }

        ws.onerror = () => {
          setError('WebSocket error')
          setVoiceState('error')
        }

        ws.onclose = () => {
          setVoiceState(prev => prev === 'error' ? 'error' : 'idle')
          wsRef.current = null
        }
      } else {
        startRecording()
      }
    } else if (voiceState === 'listening') {
      stopRecording()
    } else if (voiceState === 'speaking') {
      bargeIn()
    }
  }, [voiceState, startRecording, stopRecording, bargeIn, playTtsChunk, flushTtsBuffer])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      wsRef.current?.close()
      if (audioCtxRef.current) audioCtxRef.current.close()
      stopSilenceDetection()
    }
  }, [stopSilenceDetection])

  return { voiceState, error, toggle, bargeIn }
}
