import { useAuth } from '../lib/AuthContext'

type Page = 'landing' | 'login' | 'register' | 'onboarding' | 'workspace' | 'roadmap' | 'interview' | 'notes' | 'mastery' | 'mentor'

interface NavProps {
  page: Page
  navigate: (p: Page) => void
}

const appLinks: { label: string; page: Page }[] = [
  { label: 'Workspace', page: 'workspace' },
  { label: 'Roadmap', page: 'roadmap' },
  { label: 'Interview', page: 'interview' },
  { label: 'Notes', page: 'notes' },
  { label: 'Mastery', page: 'mastery' },
  { label: 'Mentor', page: 'mentor' },
]

const AUTH_PAGES: Page[] = ['login', 'register', 'onboarding']

export function Nav({ page, navigate }: NavProps) {
  const { user, logout } = useAuth()
  const isLanding = page === 'landing'
  const isAuthPage = AUTH_PAGES.includes(page)
  const isApp = !isLanding && !isAuthPage

  return (
    <nav
      style={{
        position: isLanding ? 'absolute' : 'relative',
        top: 0,
        left: 0,
        right: 0,
        zIndex: 100,
        padding: '0 32px',
        height: 64,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        borderBottom: isApp ? '1px solid rgba(181,80,46,0.12)' : 'none',
        backgroundColor: isApp ? 'rgba(250,250,248,0.97)' : 'transparent',
        backdropFilter: isApp ? 'blur(12px)' : 'none',
      }}
    >
      {/* Logo */}
      <button
        onClick={() => navigate('landing')}
        style={{
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: 0,
        }}
      >
        <span
          style={{
            width: 28,
            height: 28,
            borderRadius: '50%',
            background: 'linear-gradient(135deg, #B5502E 0%, #E0A458 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M7 2L11 7L7 12M3 7h8" stroke="white" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </span>
        <span
          style={{
            fontFamily: "'Fraunces', Georgia, serif",
            fontSize: 18,
            fontWeight: 700,
            color: '#1C1917',
            letterSpacing: '-0.02em',
          }}
        >
          Coachline
        </span>
      </button>

      {/* App page links */}
      {isApp && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          {appLinks.map((link) => (
            <button
              key={link.page}
              onClick={() => navigate(link.page)}
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                padding: '6px 12px',
                borderRadius: 8,
                fontSize: 13.5,
                fontWeight: page === link.page ? 600 : 400,
                color: page === link.page ? '#B5502E' : '#4B3D37',
                backgroundColor: page === link.page ? 'rgba(181,80,46,0.08)' : 'transparent',
                fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif",
                transition: 'all 0.15s ease',
              }}
            >
              {link.label}
            </button>
          ))}
        </div>
      )}

      {/* Landing nav links */}
      {isLanding && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
          {['How it works', 'Features', 'Pricing'].map((label) => (
            <a
              key={label}
              href="#"
              onClick={(e) => e.preventDefault()}
              style={{
                fontSize: 14,
                fontWeight: 500,
                color: '#4B3D37',
                textDecoration: 'none',
                transition: 'color 0.15s ease',
              }}
            >
              {label}
            </a>
          ))}
        </div>
      )}

      {/* Right action */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        {isLanding && !user && (
          <button
            onClick={() => navigate('login')}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              fontSize: 14,
              fontWeight: 500,
              color: '#4B3D37',
              padding: '6px 12px',
              fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif",
            }}
          >
            Sign in
          </button>
        )}
        {isApp && user && (
          <button
            onClick={() => { logout(); navigate('landing') }}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              fontSize: 13,
              fontWeight: 500,
              color: '#7A6B63',
              padding: '6px 10px',
              fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif",
            }}
          >
            Log out
          </button>
        )}
        {!isAuthPage && (
          <button
            onClick={() => navigate(user ? 'workspace' : 'register')}
            style={{
              background: 'linear-gradient(135deg, #B5502E 0%, #C97350 100%)',
              border: 'none',
              cursor: 'pointer',
              color: '#FAFAF8',
              fontSize: 13.5,
              fontWeight: 600,
              padding: '8px 18px',
              borderRadius: 100,
              fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif",
              boxShadow: '0 2px 12px rgba(181,80,46,0.30)',
              transition: 'transform 0.15s ease, box-shadow 0.15s ease',
            }}
            onMouseEnter={(e) => {
              ;(e.currentTarget as HTMLButtonElement).style.transform = 'translateY(-1px)'
              ;(e.currentTarget as HTMLButtonElement).style.boxShadow =
                '0 4px 18px rgba(181,80,46,0.40)'
            }}
            onMouseLeave={(e) => {
              ;(e.currentTarget as HTMLButtonElement).style.transform = 'translateY(0)'
              ;(e.currentTarget as HTMLButtonElement).style.boxShadow =
                '0 2px 12px rgba(181,80,46,0.30)'
            }}
          >
            {isLanding ? (user ? 'Dashboard' : 'Get started') : 'Dashboard'}
          </button>
        )}
      </div>
    </nav>
  )
}
