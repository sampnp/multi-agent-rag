/**
 * Floating animated mic button that drives the voice session.
 * States:
 *   idle        — pulsing ring, dark background, Mic icon
 *   connecting  — spinner
 *   listening   — bright ring, animated "breath"
 *   processing  — rotating arc
 *   speaking    — sound-wave animation, click = barge-in
 *   error       — red, MicOff icon
 */
import { Mic, MicOff, Loader2 } from 'lucide-react'
import { useVoiceSession } from '../../hooks/useVoiceSession'
import type { VoiceSessionHandlers } from '../../hooks/useVoiceSession'

const TONE_COLORS: Record<string, string> = {
  neutral: 'text-gray-300',
  positive: 'text-green-400',
  frustrated: 'text-red-400',
  confused: 'text-yellow-400',
  excited: 'text-brand-400',
  concerned: 'text-orange-400',
}

interface VoiceOrbProps extends VoiceSessionHandlers {
  className?: string
}

export default function VoiceOrb({ className = '', onTranscript, onTone, onToken }: VoiceOrbProps) {
  const { voiceState, error, toggle } = useVoiceSession({ onTranscript, onTone, onToken })

  const isActive = voiceState !== 'idle' && voiceState !== 'error'

  const orbClass = (() => {
    switch (voiceState) {
      case 'listening':
        return 'bg-brand-600 shadow-[0_0_24px_4px_rgba(99,102,241,0.6)]'
      case 'processing':
        return 'bg-indigo-700'
      case 'speaking':
        return 'bg-violet-700 shadow-[0_0_20px_4px_rgba(139,92,246,0.5)]'
      case 'error':
        return 'bg-red-800'
      case 'connecting':
        return 'bg-gray-700'
      default:
        return 'bg-gray-800 hover:bg-gray-700 border border-gray-600'
    }
  })()

  const ringClass = (() => {
    if (voiceState === 'listening') return 'animate-ping bg-brand-500'
    if (voiceState === 'speaking') return 'animate-pulse bg-violet-500'
    return ''
  })()

  const label = (() => {
    switch (voiceState) {
      case 'connecting': return 'Connecting…'
      case 'listening': return 'Listening… (click to stop)'
      case 'processing': return 'Processing…'
      case 'speaking': return 'Speaking (click to interrupt)'
      case 'error': return error ?? 'Error'
      default: return 'Click to speak'
    }
  })()

  return (
    <div className={`flex flex-col items-center gap-2 ${className}`}>
      <div className="relative">
        {/* Animated ring behind orb */}
        {ringClass && (
          <span className={`absolute inset-0 rounded-full opacity-40 ${ringClass}`} />
        )}

        <button
          onClick={toggle}
          title={label}
          className={`relative z-10 w-14 h-14 rounded-full flex items-center justify-center transition-all duration-200 ${orbClass}`}
        >
          {voiceState === 'connecting' ? (
            <Loader2 className="w-6 h-6 text-gray-300 animate-spin" />
          ) : voiceState === 'processing' ? (
            <Loader2 className="w-6 h-6 text-indigo-200 animate-spin" />
          ) : voiceState === 'error' ? (
            <MicOff className="w-6 h-6 text-red-300" />
          ) : (
            <Mic className={`w-6 h-6 ${isActive ? 'text-white' : 'text-gray-400'}`} />
          )}
        </button>
      </div>

      <p className="text-[11px] text-gray-500 text-center max-w-[120px] leading-snug">
        {label}
      </p>
    </div>
  )
}

export { TONE_COLORS }
