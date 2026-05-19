import { useAuthStore } from '../../store/authStore'

interface HeaderProps {
  title: string
  isWsConnected: boolean
}

export default function Header({ title, isWsConnected }: HeaderProps) {
  const user = useAuthStore((s) => s.user)

  return (
    <header className="h-14 bg-gray-800 border-b border-gray-700 flex items-center justify-between px-6 shrink-0">
      <h2 className="font-semibold text-white">{title}</h2>
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-xs">
          <span className={`w-2 h-2 rounded-full ${isWsConnected ? 'bg-green-400' : 'bg-red-500'}`} />
          <span className={isWsConnected ? 'text-green-400' : 'text-red-400'}>
            {isWsConnected ? 'Live' : 'Offline'}
          </span>
        </div>
        <div className="w-7 h-7 rounded-full bg-brand-600 flex items-center justify-center text-xs font-bold text-white">
          {user?.username?.[0]?.toUpperCase() ?? '?'}
        </div>
      </div>
    </header>
  )
}
