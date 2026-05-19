import { NavLink } from 'react-router-dom'
import { Activity, Bot, Brain, BrainCircuit, FileText, Globe, LayoutDashboard, LogOut, Mic, Network, Settings } from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/agents', icon: Bot, label: 'Agents' },
  { to: '/browser', icon: Globe, label: 'Browser Agent' },
  { to: '/eval', icon: Activity, label: 'Evaluation' },
  { to: '/documents', icon: FileText, label: 'Documents' },
  { to: '/graph', icon: Network, label: 'Knowledge Graph' },
  { to: '/memory', icon: Brain, label: 'Memory' },
  { to: '/voice', icon: Mic, label: 'Voice' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export default function Sidebar() {
  const { user, logout } = useAuth()

  return (
    <aside className="fixed inset-y-0 left-0 w-60 bg-gray-800 border-r border-gray-700 flex flex-col z-10">
      <div className="flex items-center gap-2 px-5 py-5 border-b border-gray-700">
        <BrainCircuit className="w-7 h-7 text-brand-500 shrink-0" />
        <span className="font-semibold text-white text-sm leading-tight">Enterprise AI OS</span>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                isActive
                  ? 'bg-brand-600 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-gray-700'
              }`
            }
          >
            <Icon className="w-4 h-4 shrink-0" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="px-3 py-4 border-t border-gray-700">
        <div className="flex items-center gap-3 px-3 py-2 mb-1">
          <div className="w-7 h-7 rounded-full bg-brand-600 flex items-center justify-center text-xs font-bold text-white shrink-0">
            {user?.username?.[0]?.toUpperCase() ?? '?'}
          </div>
          <div className="min-w-0">
            <p className="text-sm text-white truncate">{user?.username}</p>
            <p className="text-xs text-gray-400 truncate">{user?.email}</p>
          </div>
        </div>
        <button
          onClick={logout}
          className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-gray-700 transition-colors w-full"
        >
          <LogOut className="w-4 h-4 shrink-0" />
          Sign Out
        </button>
      </div>
    </aside>
  )
}
