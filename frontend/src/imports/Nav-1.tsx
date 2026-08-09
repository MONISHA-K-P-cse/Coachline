import { useEffect, useState } from 'react'
import { useAuth } from '../lib/AuthContext'
import { Sun, Moon, LogOut, Settings, Briefcase, Map, Video, BookOpen, Compass, MessageSquare, Sparkles, Shield } from 'lucide-react'

type Page = 'landing' | 'login' | 'register' | 'onboarding' | 'workspace' | 'roadmap' | 'interview' | 'notes' | 'mastery' | 'mentor' | 'bob_coach'

interface NavProps {
  page: Page
  navigate: (p: Page) => void
}

const appLinks = [
  { label: 'Workspace', page: 'workspace' as Page, icon: Briefcase },
  { label: 'Roadmap', page: 'roadmap' as Page, icon: Map },
  { label: 'Interview', page: 'interview' as Page, icon: Video },
  { label: 'Notes', page: 'notes' as Page, icon: BookOpen },
  { label: 'Mastery', page: 'mastery' as Page, icon: Compass },
  { label: 'Mentor', page: 'mentor' as Page, icon: MessageSquare },
  { label: 'IBM Bob', page: 'bob_coach' as Page, icon: Shield },
]

const AUTH_PAGES: Page[] = ['login', 'register', 'onboarding']

export function Nav({ page, navigate }: NavProps) {
  const { user, logout } = useAuth()
  const [darkMode, setDarkMode] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('theme') === 'dark' || 
        (!localStorage.getItem('theme') && window.matchMedia('(prefers-color-scheme: dark)').matches)
    }
    return false
  })

  useEffect(() => {
    const root = document.documentElement
    if (darkMode) {
      root.classList.add('dark')
      localStorage.setItem('theme', 'dark')
    } else {
      root.classList.remove('dark')
      localStorage.setItem('theme', 'light')
    }
  }, [darkMode])

  const toggleTheme = () => setDarkMode(!darkMode)

  const isLanding = page === 'landing'
  const isAuthPage = AUTH_PAGES.includes(page)
  const isApp = !isLanding && !isAuthPage

  return (
    <nav className={`w-full z-50 transition-all duration-300 ${
      isLanding 
        ? 'absolute top-0 left-0 right-0 bg-transparent py-6 px-6 md:px-12' 
        : 'sticky top-0 bg-bg/85 backdrop-blur-xl border-b border-border/60 px-6 py-3 shadow-xs'
    } flex items-center justify-between`}>
      
      {/* Brand Logo */}
      <button
        onClick={() => navigate('landing')}
        className="flex items-center gap-2.5 focus:outline-none cursor-pointer group"
      >
        <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-rust via-rust to-accent flex items-center justify-center shadow-md shadow-rust/15 group-hover:scale-105 transition-all duration-200">
          <Sparkles className="w-4 h-4 text-white animate-pulse" />
        </div>
        <span className="font-display font-bold text-xl tracking-tight text-text group-hover:text-rust transition-colors duration-150">
          Coachline
        </span>
      </button>

      {/* Navigation tabs */}
      {isApp && (
        <div className="flex items-center gap-1 bg-panel-bg/60 p-1 rounded-xl border border-border/50 overflow-x-auto max-w-[280px] sm:max-w-none whitespace-nowrap [scrollbar-width:none] [&::-webkit-scrollbar]:hidden backdrop-blur-sm shadow-inner">
          {appLinks.map((link) => {
            const Icon = link.icon
            const isActive = page === link.page
            return (
              <button
                key={link.page}
                onClick={() => navigate(link.page)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10px] sm:text-xs font-semibold tracking-wide uppercase transition-all duration-200 cursor-pointer ${
                  isActive
                    ? 'bg-rust text-white shadow-xs shadow-rust/20 font-bold'
                    : 'text-text-muted hover:text-text hover:bg-border/30'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-white' : 'text-text-muted/80'}`} />
                {link.label}
              </button>
            )
          })}
        </div>
      )}

      {/* Landing Link Items */}
      {isLanding && (
        <div className="hidden md:flex items-center gap-8">
          {['How it works', 'Features', 'Pricing'].map((label) => (
            <a
              key={label}
              href="#"
              onClick={(e) => e.preventDefault()}
              className="text-sm font-medium text-text-muted hover:text-text transition-colors duration-150"
            >
              {label}
            </a>
          ))}
        </div>
      )}

      {/* Action Area & Theme Toggle */}
      <div className="flex items-center gap-3">
        {/* Theme Toggle Button */}
        <button
          onClick={toggleTheme}
          className="p-2.5 rounded-xl border border-border/80 bg-card-bg hover:bg-border/30 text-text-muted hover:text-text transition-all duration-200 cursor-pointer shadow-xs active:scale-95"
          aria-label="Toggle dark mode"
        >
          {darkMode ? <Sun className="w-4 h-4 text-accent" /> : <Moon className="w-4 h-4 text-text" />}
        </button>

        {isLanding && !user && (
          <button
            onClick={() => navigate('login')}
            className="text-sm font-semibold text-text-muted hover:text-text px-4 py-2 transition-colors cursor-pointer"
          >
            Sign in
          </button>
        )}

        {isApp && user && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => navigate('onboarding')}
              className="flex items-center gap-1.5 text-xs font-semibold text-text-muted hover:text-text px-3 py-2 rounded-xl border border-border/50 hover:bg-border/20 transition-all cursor-pointer"
            >
              <Settings className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Settings</span>
            </button>
            <button
              onClick={() => {
                logout()
                navigate('landing')
              }}
              className="flex items-center gap-1.5 text-xs font-semibold text-text-muted/80 hover:text-red-500 px-3 py-2 rounded-xl hover:bg-red-500/10 transition-all cursor-pointer"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Log out</span>
            </button>
          </div>
        )}

        {!isAuthPage && (
          <button
            onClick={() => navigate(user ? 'workspace' : 'register')}
            className="bg-rust text-white font-semibold text-sm px-5 py-2.5 rounded-xl shadow-sm shadow-rust/20 hover:shadow-md hover:shadow-rust/30 cursor-pointer hover:-translate-y-0.5 active:translate-y-0 transition-all duration-150 active:scale-[0.98]"
          >
            {isLanding ? (user ? 'Dashboard' : 'Get started') : 'Dashboard'}
          </button>
        )}
      </div>
    </nav>
  )
}
