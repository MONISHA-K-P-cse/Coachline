import { useState } from 'react'
import { Nav } from '../components/Nav'
import { useAuth } from '../lib/AuthContext'

type Page = 'landing' | 'login' | 'register' | 'onboarding' | 'workspace' | 'roadmap' | 'interview' | 'notes' | 'mastery' | 'mentor'
interface Props { navigate: (p: Page) => void }

const cardStyle: React.CSSProperties = {
  background: '#FFFFFF',
  borderRadius: 20,
  border: '1.5px solid rgba(181,80,46,0.12)',
  padding: 36,
  boxShadow: '0 2px 16px rgba(0,0,0,0.05)',
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '12px 14px',
  borderRadius: 12,
  border: '1.5px solid rgba(181,80,46,0.20)',
  background: '#FFFFFF',
  fontSize: 14,
  color: '#1C1917',
  fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif",
  outline: 'none',
  boxSizing: 'border-box',
}

const labelStyle: React.CSSProperties = {
  display: 'block',
  fontSize: 12,
  fontWeight: 600,
  color: '#4B3D37',
  marginBottom: 6,
}

export default function Register({ navigate }: Props) {
  const { register, error } = useAuth()
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [localError, setLocalError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setLocalError(null)
    try {
      await register({ email, password, full_name: fullName || undefined })
      navigate('onboarding')
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : 'Registration failed.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#FAFAF8', fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif" }}>
      <Nav page="landing" navigate={navigate} />
      <div style={{ maxWidth: 420, margin: '0 auto', padding: '64px clamp(16px, 4vw, 48px)' }}>
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <h1 style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 28, fontWeight: 700, color: '#1C1917', margin: '0 0 8px' }}>
            Start your journey.
          </h1>
          <p style={{ fontSize: 14, color: '#7A6B63', margin: 0 }}>Two minutes, then Coachline does the rest.</p>
        </div>

        <form onSubmit={handleSubmit} style={cardStyle}>
          <div style={{ marginBottom: 16 }}>
            <label style={labelStyle} htmlFor="full_name">Full name</label>
            <input
              id="full_name"
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              style={inputStyle}
              placeholder="Alex Rivera"
            />
          </div>
          <div style={{ marginBottom: 16 }}>
            <label style={labelStyle} htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              style={inputStyle}
              placeholder="you@example.com"
            />
          </div>
          <div style={{ marginBottom: 22 }}>
            <label style={labelStyle} htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={inputStyle}
              placeholder="At least 8 characters"
            />
          </div>

          {(localError || error) && (
            <div style={{ marginBottom: 16, padding: '10px 14px', borderRadius: 10, background: 'rgba(181,80,46,0.08)', color: '#B5502E', fontSize: 13 }}>
              {localError || error}
            </div>
          )}

          <button
            type="submit"
            disabled={submitting}
            style={{
              width: '100%',
              background: submitting ? 'rgba(181,80,46,0.4)' : 'linear-gradient(135deg, #B5502E 0%, #C97350 100%)',
              border: 'none',
              cursor: submitting ? 'not-allowed' : 'pointer',
              color: '#FAFAF8',
              fontSize: 14,
              fontWeight: 700,
              padding: '13px 0',
              borderRadius: 100,
              fontFamily: "'Plus Jakarta Sans', sans-serif",
            }}
          >
            {submitting ? 'Creating account…' : 'Create account'}
          </button>
        </form>

        <p style={{ textAlign: 'center', fontSize: 13, color: '#7A6B63', marginTop: 20 }}>
          Already have an account?{' '}
          <button
            onClick={() => navigate('login')}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#B5502E', fontWeight: 700, fontSize: 13, padding: 0 }}
          >
            Sign in
          </button>
        </p>
      </div>
    </div>
  )
}
