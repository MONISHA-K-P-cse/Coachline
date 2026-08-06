import { useEffect, useState, useCallback } from 'react'
import { Nav } from '../components/Nav'
import { useAuth } from '../lib/AuthContext'
import * as api from '../lib/apiClient'

type Page = 'landing' | 'login' | 'register' | 'onboarding' | 'workspace' | 'roadmap' | 'interview' | 'notes' | 'mastery' | 'mentor'
interface Props { navigate: (p: Page) => void }

export default function Roadmap({ navigate }: Props) {
  const { user } = useAuth()
  const [roadmap, setRoadmap] = useState<api.RoadmapResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [maxUnlockedWeek, setMaxUnlockedWeek] = useState<number>(1)

  const load = useCallback(async () => {
    setError(null)
    const existing = await api.listRoadmaps()
    const latest = existing.length
      ? existing.reduce((a, b) => (new Date(b.created_at) > new Date(a.created_at) ? b : a))
      : null
    setRoadmap(latest)
  }, [])

  useEffect(() => {
    load().finally(() => setLoading(false))
    const val = localStorage.getItem('roadmap_max_unlocked')
    if (val) {
      setMaxUnlockedWeek(parseInt(val))
    }
  }, [load])

  const handleGenerate = async () => {
    if (!user?.profile?.target_role) {
      setError('Set your target role in onboarding before generating a roadmap.')
      return
    }
    setGenerating(true)
    setError(null)
    try {
      const created = await api.generateRoadmap(user.profile.target_role)
      setRoadmap(created)
    } catch (err) {
      setError(err instanceof api.ApiError ? err.message : 'Could not generate a roadmap right now. Please try again.')
    } finally {
      setGenerating(false)
    }
  }

  const steps = (roadmap?.steps_json ?? []) as api.RoadmapStep[]

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#FAFAF8', fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif" }}>
      <Nav page="roadmap" navigate={navigate} />
      <div style={{ maxWidth: 800, margin: '0 auto', padding: '40px clamp(16px, 4vw, 48px)' }}>
        <p style={{ fontSize: 13, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: '#B5502E', marginBottom: 8 }}>Study plan</p>
        <h1 style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 'clamp(1.8rem, 3vw, 2.4rem)', fontWeight: 700, color: '#1C1917', letterSpacing: '-0.02em', margin: '0 0 8px' }}>
          {roadmap ? roadmap.title : 'Your Roadmap'}
        </h1>
        <p style={{ fontSize: 15, color: '#7A6B63', margin: '0 0 28px', lineHeight: 1.6 }}>
          Generated for your target role, company, experience level, and interview date from onboarding.
        </p>

        {error && (
          <div style={{ marginBottom: 20, padding: '10px 14px', borderRadius: 10, background: 'rgba(181,80,46,0.08)', color: '#B5502E', fontSize: 13 }}>{error}</div>
        )}

        {loading ? (
          <p style={{ fontSize: 14, color: '#7A6B63' }}>Loading your roadmap…</p>
        ) : !roadmap ? (
          <div style={{ background: '#FFFFFF', borderRadius: 18, border: '1.5px solid rgba(181,80,46,0.12)', padding: 32, textAlign: 'center' }}>
            <p style={{ fontSize: 14, color: '#7A6B63', marginBottom: 18 }}>
              You don't have a roadmap yet. Generate one tailored to your profile.
            </p>
            <button
              onClick={handleGenerate}
              disabled={generating}
              style={{
                background: '#B5502E', color: '#fff', border: 'none', borderRadius: 10,
                padding: '10px 22px', fontSize: 14, fontWeight: 600, cursor: generating ? 'default' : 'pointer',
                opacity: generating ? 0.6 : 1, fontFamily: "'Plus Jakarta Sans', sans-serif",
              }}
            >
              {generating ? 'Generating… this can take a couple minutes' : 'Generate Roadmap'}
            </button>
          </div>
        ) : (
          <>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
              <div style={{ flex: 1, height: 8, borderRadius: 100, background: 'rgba(181,80,46,0.1)', overflow: 'hidden' }}>
                <div style={{ width: `${Math.min(100, Math.round(((maxUnlockedWeek - 1) / (steps.length || 1)) * 100))}%`, height: '100%', background: '#B5502E', transition: 'width 0.3s ease' }} />
              </div>
              <span style={{ fontSize: 12, color: '#7A6B63', whiteSpace: 'nowrap' }}>
                {Math.min(100, Math.round(((maxUnlockedWeek - 1) / (steps.length || 1)) * 100))}% complete
              </span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {steps.map((step) => {
                const isLocked = step.step_number > maxUnlockedWeek
                return (
                  <div
                    key={step.step_number}
                    style={{
                      background: isLocked ? '#F5F5F4' : '#FFFFFF',
                      borderRadius: 18,
                      border: isLocked ? '1.5px dashed rgba(120,107,99,0.2)' : '1.5px solid rgba(181,80,46,0.12)',
                      padding: '18px 24px',
                      boxShadow: isLocked ? 'none' : '0 2px 8px rgba(0,0,0,0.04)',
                      opacity: isLocked ? 0.65 : 1,
                      position: 'relative'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                      <span style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 16, fontWeight: 700, color: isLocked ? '#7A6B63' : '#1C1917', display: 'flex', alignItems: 'center', gap: 6 }}>
                        Week {step.step_number}: {step.title} {isLocked && '🔒'}
                      </span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <span style={{ fontSize: 11, color: '#7A6B63' }}>{step.estimated_hours}h</span>
                        {isLocked ? (
                          <span style={{ fontSize: 11, fontWeight: 600, color: '#7A6B63', background: 'rgba(120,107,99,0.1)', padding: '4px 10px', borderRadius: 8 }}>
                            Locked
                          </span>
                        ) : (
                          <button
                            onClick={() => {
                              localStorage.setItem('active_roadmap_week', step.step_number.toString())
                              localStorage.setItem('active_roadmap_topic', step.title)
                              navigate('interview')
                            }}
                            style={{
                              background: '#B5502E',
                              border: 'none',
                              borderRadius: 8,
                              cursor: 'pointer',
                              padding: '5px 12px',
                              fontSize: 11,
                              fontWeight: 700,
                              color: '#FFFFFF',
                              fontFamily: "'Plus Jakarta Sans', sans-serif",
                              boxShadow: '0 2px 6px rgba(181,80,46,0.2)'
                            }}
                          >
                            Practice
                          </button>
                        )}
                      </div>
                    </div>
                    <p style={{ fontSize: 13, color: isLocked ? '#8C827D' : '#57534E', lineHeight: 1.6, margin: 0 }}>
                      {isLocked ? `Practice Week ${step.step_number - 1} and get an overall score of 50+ to unlock this topic.` : step.description}
                    </p>
                  </div>
                )
              })}
            </div>

            <button
              onClick={handleGenerate}
              disabled={generating}
              style={{
                marginTop: 24, background: 'none', border: '1px solid rgba(181,80,46,0.25)', borderRadius: 10,
                padding: '8px 18px', fontSize: 13, fontWeight: 600, color: '#B5502E', cursor: generating ? 'default' : 'pointer',
                opacity: generating ? 0.6 : 1, fontFamily: "'Plus Jakarta Sans', sans-serif",
              }}
            >
              {generating ? 'Regenerating…' : 'Regenerate Roadmap'}
            </button>
          </>
        )}
      </div>
    </div>
  )
}
