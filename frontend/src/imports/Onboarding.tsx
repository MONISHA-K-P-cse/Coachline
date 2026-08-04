import { useState, useEffect } from 'react'
import { Nav } from '../components/Nav'
import { useAuth } from '../lib/AuthContext'
import { updateProfile, ApiError } from '../lib/apiClient'

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

const LEARNING_STYLES = [
  { value: 'visual', label: 'Visual', desc: 'Diagrams & comparisons' },
  { value: 'reading_writing', label: 'Reading/Writing', desc: 'Dense written outlines' },
  { value: 'kinesthetic', label: 'Kinesthetic', desc: 'Hands-on exercises' },
] as const

export default function Onboarding({ navigate }: Props) {
  const { user, refreshUser } = useAuth()
  const [targetRole, setTargetRole] = useState(user?.profile?.target_role || '')
  const [targetCompany, setTargetCompany] = useState(user?.profile?.target_company || '')
  const [experienceLevel, setExperienceLevel] = useState(user?.profile?.experience_level || '')
  const [interviewDate, setInterviewDate] = useState(
    user?.profile?.interview_date ? new Date(user.profile.interview_date).toISOString().split('T')[0] : ''
  )
  const [learningStyle, setLearningStyle] = useState<string>(user?.profile?.learning_style || 'reading_writing')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (user?.profile) {
      if (user.profile.target_role) setTargetRole(user.profile.target_role)
      if (user.profile.target_company) setTargetCompany(user.profile.target_company)
      if (user.profile.experience_level) setExperienceLevel(user.profile.experience_level)
      if (user.profile.interview_date) {
        setInterviewDate(new Date(user.profile.interview_date).toISOString().split('T')[0])
      }
      if (user.profile.learning_style) setLearningStyle(user.profile.learning_style)
    }
  }, [user])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      await updateProfile({
        target_role: targetRole || undefined,
        target_company: targetCompany || undefined,
        experience_level: experienceLevel || undefined,
        interview_date: interviewDate ? new Date(interviewDate).toISOString() : undefined,
        learning_style: learningStyle,
      })
      await refreshUser()
      navigate('workspace')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save your profile.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#FAFAF8', fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif" }}>
      <Nav page="workspace" navigate={navigate} />
      <div style={{ maxWidth: 520, margin: '0 auto', padding: '56px clamp(16px, 4vw, 48px)' }}>
        <div style={{ marginBottom: 28 }}>
          <p style={{ fontSize: 13, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: '#B5502E', marginBottom: 8 }}>
            One quick step
          </p>
          <h1 style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 28, fontWeight: 700, color: '#1C1917', margin: '0 0 8px' }}>
            Tell us what you're prepping for.
          </h1>
          <p style={{ fontSize: 14, color: '#7A6B63', margin: 0, lineHeight: 1.6 }}>
            This shapes your roadmap, interview questions, and how your notes are written.
          </p>
        </div>

        <form onSubmit={handleSubmit} style={cardStyle}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
            <div>
              <label style={labelStyle} htmlFor="target_role">Target role</label>
              <input id="target_role" type="text" value={targetRole} onChange={(e) => setTargetRole(e.target.value)} style={inputStyle} placeholder="Backend Engineer" />
            </div>
            <div>
              <label style={labelStyle} htmlFor="target_company">Target company</label>
              <input id="target_company" type="text" value={targetCompany} onChange={(e) => setTargetCompany(e.target.value)} style={inputStyle} placeholder="Stripe" />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 22 }}>
            <div>
              <label style={labelStyle} htmlFor="experience_level">Experience level</label>
              <select id="experience_level" value={experienceLevel} onChange={(e) => setExperienceLevel(e.target.value)} style={inputStyle}>
                <option value="">Select…</option>
                <option value="Entry">Entry</option>
                <option value="Junior">Junior</option>
                <option value="Intermediate">Intermediate</option>
                <option value="Senior">Senior</option>
                <option value="Staff+">Staff+</option>
              </select>
            </div>
            <div>
              <label style={labelStyle} htmlFor="interview_date">Interview date</label>
              <input id="interview_date" type="date" value={interviewDate} onChange={(e) => setInterviewDate(e.target.value)} style={inputStyle} />
            </div>
          </div>

          <div style={{ marginBottom: 24 }}>
            <label style={labelStyle}>Learning style</label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
              {LEARNING_STYLES.map((s) => (
                <button
                  key={s.value}
                  type="button"
                  onClick={() => setLearningStyle(s.value)}
                  style={{
                    textAlign: 'left',
                    padding: '10px 12px',
                    borderRadius: 12,
                    cursor: 'pointer',
                    border: learningStyle === s.value ? '1.5px solid #B5502E' : '1.5px solid rgba(181,80,46,0.16)',
                    background: learningStyle === s.value ? 'rgba(181,80,46,0.07)' : '#FFFFFF',
                    fontFamily: "'Plus Jakarta Sans', sans-serif",
                  }}
                >
                  <div style={{ fontSize: 12.5, fontWeight: 700, color: learningStyle === s.value ? '#B5502E' : '#1C1917' }}>{s.label}</div>
                  <div style={{ fontSize: 10.5, color: '#7A6B63', marginTop: 2 }}>{s.desc}</div>
                </button>
              ))}
            </div>
          </div>

          {error && (
            <div style={{ marginBottom: 16, padding: '10px 14px', borderRadius: 10, background: 'rgba(181,80,46,0.08)', color: '#B5502E', fontSize: 13 }}>
              {error}
            </div>
          )}

          <div style={{ display: 'flex', gap: 12 }}>
            <button
              type="button"
              onClick={() => navigate('workspace')}
              style={{ flex: 1, background: 'none', border: '1.5px solid rgba(181,80,46,0.25)', cursor: 'pointer', color: '#4B3D37', fontSize: 13, fontWeight: 600, padding: '12px 0', borderRadius: 100, fontFamily: "'Plus Jakarta Sans', sans-serif" }}
            >
              Skip for now
            </button>
            <button
              type="submit"
              disabled={submitting}
              style={{
                flex: 2,
                background: submitting ? 'rgba(181,80,46,0.4)' : 'linear-gradient(135deg, #B5502E 0%, #C97350 100%)',
                border: 'none',
                cursor: submitting ? 'not-allowed' : 'pointer',
                color: '#FAFAF8',
                fontSize: 13.5,
                fontWeight: 700,
                padding: '12px 0',
                borderRadius: 100,
                fontFamily: "'Plus Jakarta Sans', sans-serif",
              }}
            >
              {submitting ? 'Saving…' : 'Save & continue →'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
