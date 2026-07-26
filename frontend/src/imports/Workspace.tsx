import { useState, useEffect, useRef, useCallback } from 'react'
import { Nav } from '../components/Nav'
import { OrbitLoader } from '../components/OrbitLoader'
import { useAuth } from '../lib/AuthContext'
import * as api from '../lib/apiClient'

type Page = 'landing' | 'login' | 'register' | 'onboarding' | 'workspace' | 'roadmap' | 'interview' | 'notes' | 'mastery' | 'mentor'
interface Props { navigate: (p: Page) => void }

// ─── Resume Skill Network — driven by the real resume agent's strengths/improvements ──

interface SkillNode { id: string; label: string; x: number; y: number; strength: number; missing?: boolean }

function layoutSkillNodes(strengths: string[], improvements: string[]): SkillNode[] {
  const nodes: SkillNode[] = [{ id: 'resume', label: 'Resume', x: 150, y: 110, strength: 0.9 }]
  const ringAngles = (count: number) => Array.from({ length: count }, (_, i) => (i / Math.max(count, 1)) * Math.PI * 2)

  strengths.slice(0, 4).forEach((s, i, arr) => {
    const angle = ringAngles(arr.length)[i] - Math.PI / 2
    nodes.push({
      id: `s-${i}`,
      label: s.length > 22 ? s.slice(0, 20) + '…' : s,
      x: 150 + Math.cos(angle) * 95,
      y: 115 + Math.sin(angle) * 75,
      strength: 0.75,
    })
  })
  improvements.slice(0, 3).forEach((s, i, arr) => {
    const angle = ringAngles(arr.length)[i] + Math.PI / 2
    nodes.push({
      id: `m-${i}`,
      label: s.length > 22 ? s.slice(0, 20) + '…' : s,
      x: 150 + Math.cos(angle) * 130,
      y: 115 + Math.sin(angle) * 95,
      strength: 0,
      missing: true,
    })
  })
  return nodes
}

function ResumeSkillNetwork({ strengths, improvements }: { strengths: string[]; improvements: string[] }) {
  const [hov, setHov] = useState<string | null>(null)
  const nodes = layoutSkillNodes(strengths, improvements)
  const root = nodes[0]

  return (
    <svg viewBox="0 0 300 240" style={{ width: '100%', display: 'block' }}>
      <defs>
        <filter id="skill-glow" x="-60%" y="-60%" width="220%" height="220%">
          <feGaussianBlur stdDeviation="3.5" result="blur"/>
          <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
      </defs>
      {nodes.slice(1).map((n) => (
        <path
          key={`edge-${n.id}`}
          d={`M ${root.x} ${root.y} L ${n.x} ${n.y}`}
          fill="none"
          stroke={n.missing ? 'rgba(181,80,46,0.35)' : `rgba(181,80,46,${0.12 + n.strength * 0.45})`}
          strokeWidth={n.missing ? 0.8 : 1.4}
          strokeDasharray={n.missing ? '3 3' : 'none'}
        />
      ))}
      {nodes.map((node) => {
        const isHov = hov === node.id
        const r = node.id === 'resume' ? 14 : isHov ? 12 : 9
        return (
          <g key={node.id} transform={`translate(${node.x},${node.y})`} style={{ cursor: 'pointer' }} onMouseEnter={() => setHov(node.id)} onMouseLeave={() => setHov(null)}>
            {node.missing ? (
              <>
                <circle r={r} fill="rgba(181,80,46,0.04)" stroke="rgba(181,80,46,0.40)" strokeWidth="1.2" strokeDasharray="3 2" />
                <text textAnchor="middle" dy="4" fill="rgba(181,80,46,0.55)" fontSize="8" fontWeight="600" fontFamily="'Plus Jakarta Sans', sans-serif">+</text>
              </>
            ) : (
              <circle r={r} fill={`rgba(181,80,46,${0.3 + node.strength * 0.55})`} filter={isHov ? 'url(#skill-glow)' : 'none'} />
            )}
            <text dy={r + 13} textAnchor="middle" fill={node.missing ? 'rgba(181,80,46,0.50)' : isHov ? '#1C1917' : '#7A6B63'} fontSize={8.5} fontWeight={isHov ? 700 : 500} fontFamily="'Plus Jakarta Sans', sans-serif">
              {node.label}
            </text>
          </g>
        )
      })}
    </svg>
  )
}

// ─── Main component ──────────────────────────────────────────────────────────

function timeAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diffMs / 60000)
  if (mins < 60) return `${Math.max(mins, 0)} min ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return days === 1 ? 'Yesterday' : `${days} days ago`
}

export default function Workspace({ navigate }: Props) {
  const { user } = useAuth()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [dashboard, setDashboard] = useState<api.DashboardSummary | null>(null)
  const [resumes, setResumes] = useState<api.ResumeResponse[]>([])
  const [sessions, setSessions] = useState<api.InterviewSession[]>([])
  const [topicMastery, setTopicMastery] = useState<api.TopicMasteryEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [resumeView, setResumeView] = useState<'scores' | 'network'>('scores')

  const loadAll = useCallback(async () => {
    const [d, r, s, tm] = await Promise.all([
      api.getDashboard(),
      api.listResumes(),
      api.listInterviewSessions(),
      api.getTopicMastery(),
    ])
    setDashboard(d)
    setResumes(r)
    setSessions(s)
    setTopicMastery(tm)
  }, [])

  useEffect(() => {
    loadAll().finally(() => setLoading(false))
  }, [loadAll])

  const latestResume = resumes[0]

  const handleFileSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    setAnalyzing(true)
    setUploadError(null)
    try {
      await api.uploadResume(file)
      await loadAll()
    } catch (err) {
      setUploadError(err instanceof api.ApiError ? err.message : 'Resume upload failed.')
    } finally {
      setAnalyzing(false)
    }
  }

  const masteredCount = topicMastery.filter((t) => t.mastery_score >= 70).length
  const sessionsThisWeek = sessions.filter((s) => Date.now() - new Date(s.started_at).getTime() < 7 * 86400000).length

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', backgroundColor: '#FAFAF8' }}>
        <Nav page="workspace" navigate={navigate} />
        <OrbitLoader label="Loading your workspace…" size={72} />
      </div>
    )
  }

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#FAFAF8', fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif" }}>
      <Nav page="workspace" navigate={navigate} />
      <input ref={fileInputRef} type="file" accept=".pdf" onChange={handleFileSelected} style={{ display: 'none' }} />

      <div style={{ maxWidth: 1100, margin: '0 auto', padding: '40px clamp(16px, 4vw, 48px)' }}>
        {/* Header */}
        <div style={{ marginBottom: 40 }}>
          <p style={{ fontSize: 13, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: '#B5502E', marginBottom: 8 }}>
            Your workspace
          </p>
          <h1 style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 'clamp(1.8rem, 3vw, 2.4rem)', fontWeight: 700, color: '#1C1917', letterSpacing: '-0.02em', margin: 0 }}>
            {user?.full_name ? `Welcome back, ${user.full_name.split(' ')[0]}.` : 'Welcome back.'}
          </h1>
          <p style={{ fontSize: 15, color: '#7A6B63', marginTop: 8, lineHeight: 1.6 }}>
            {dashboard?.days_until_interview != null && dashboard.target_company
              ? <>You have an interview with <strong style={{ color: '#B5502E' }}>{dashboard.target_company}</strong> in <strong style={{ color: '#B5502E' }}>{dashboard.days_until_interview} days</strong>. Here's where you stand.</>
              : 'Add your target company and interview date in onboarding to see a countdown here.'}
          </p>
          {dashboard?.panic_mode && (
            <div style={{ marginTop: 14, padding: '10px 16px', background: 'linear-gradient(160deg, #1C1917, #2E1F18)', borderRadius: 12, color: '#E0A458', fontSize: 13, fontWeight: 600 }}>
              ⚠ Panic Mode: {dashboard.recommendations[0]}
            </div>
          )}
        </div>

        {/* Top metrics — all real */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16, marginBottom: 32 }}>
          {[
            { label: 'Readiness Score', value: `${dashboard?.overall_readiness_score ?? 0}%`, sub: dashboard?.total_interviews_conducted ? `${dashboard.total_interviews_conducted} interviews so far` : 'No sessions yet', accent: '#B5502E' },
            { label: 'Sessions This Week', value: String(sessionsThisWeek), sub: `${sessions.length} total`, accent: '#C97350' },
            { label: 'Topics Mastered', value: `${masteredCount} / ${topicMastery.length || 0}`, sub: topicMastery.length ? `${topicMastery.length - masteredCount} in progress` : 'Not tracked yet', accent: '#E0A458' },
            { label: 'Days to Interview', value: dashboard?.days_until_interview != null ? String(dashboard.days_until_interview) : '—', sub: dashboard?.target_role || 'Set in onboarding', accent: '#B5502E' },
          ].map((m) => (
            <div key={m.label} style={{ background: '#FFFFFF', borderRadius: 16, border: '1.5px solid rgba(181,80,46,0.12)', padding: '22px 24px', boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }}>
              <div style={{ fontSize: 12, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#7A6B63', marginBottom: 10 }}>{m.label}</div>
              <div style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 32, fontWeight: 700, color: m.accent, letterSpacing: '-0.02em' }}>{m.value}</div>
              <div style={{ fontSize: 12, color: '#7A6B63', marginTop: 4 }}>{m.sub}</div>
            </div>
          ))}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: 24 }}>
          {/* Left column */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>

            {/* Resume analysis */}
            <div style={{ background: '#FFFFFF', borderRadius: 18, border: '1.5px solid rgba(181,80,46,0.12)', padding: 28, boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 18 }}>
                <h2 style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 18, fontWeight: 700, color: '#1C1917', margin: 0 }}>Resume Analysis</h2>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  {latestResume && (
                    <div style={{ display: 'flex', background: '#F5F2EE', borderRadius: 8, padding: 3, gap: 2 }}>
                      {(['scores', 'network'] as const).map((v) => (
                        <button key={v} onClick={() => setResumeView(v)} style={{ background: resumeView === v ? '#FFFFFF' : 'none', border: 'none', cursor: 'pointer', borderRadius: 6, padding: '5px 10px', fontSize: 11, fontWeight: 700, color: resumeView === v ? '#B5502E' : '#7A6B63', fontFamily: "'Plus Jakarta Sans', sans-serif", boxShadow: resumeView === v ? '0 1px 4px rgba(0,0,0,0.08)' : 'none' }}>
                          {v === 'network' ? 'Skill Map' : 'Scores'}
                        </button>
                      ))}
                    </div>
                  )}
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    disabled={analyzing}
                    style={{ background: 'linear-gradient(135deg, #B5502E, #C97350)', border: 'none', cursor: analyzing ? 'not-allowed' : 'pointer', color: '#FAFAF8', fontSize: 12, fontWeight: 700, padding: '7px 14px', borderRadius: 100, fontFamily: "'Plus Jakarta Sans', sans-serif" }}
                  >
                    {latestResume ? 'Upload new resume' : 'Upload resume'}
                  </button>
                </div>
              </div>

              {uploadError && (
                <div style={{ marginBottom: 14, padding: '10px 14px', borderRadius: 10, background: 'rgba(181,80,46,0.08)', color: '#B5502E', fontSize: 13 }}>{uploadError}</div>
              )}

              {analyzing ? (
                <OrbitLoader label="Analyzing resume…" size={64} />
              ) : !latestResume ? (
                <div style={{ textAlign: 'center', padding: '32px 0', color: '#7A6B63', fontSize: 13 }}>
                  Upload a PDF resume to get a real, content-based readiness score.
                </div>
              ) : resumeView === 'scores' ? (
                <div>
                  <div style={{ display: 'flex', gap: 24, marginBottom: 18 }}>
                    <div>
                      <div style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 32, fontWeight: 700, color: '#B5502E' }}>{latestResume.score}</div>
                      <div style={{ fontSize: 11, color: '#7A6B63', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Overall Score</div>
                    </div>
                    <div>
                      <div style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 32, fontWeight: 700, color: '#C97350' }}>{latestResume.ats_score}</div>
                      <div style={{ fontSize: 11, color: '#7A6B63', textTransform: 'uppercase', letterSpacing: '0.06em' }}>ATS Score</div>
                    </div>
                    <div>
                      <div style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 32, fontWeight: 700, color: '#E0A458' }}>{latestResume.keyword_count}</div>
                      <div style={{ fontSize: 11, color: '#7A6B63', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Keywords</div>
                    </div>
                  </div>
                  {latestResume.score_details?.summary && (
                    <p style={{ fontSize: 13, color: '#4B3D37', lineHeight: 1.6, margin: '0 0 14px', fontStyle: 'italic' }}>{latestResume.score_details.summary}</p>
                  )}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                    <div>
                      <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#15803d', marginBottom: 8 }}>Strengths</div>
                      {(latestResume.score_details?.strengths ?? []).map((s) => (
                        <div key={s} style={{ fontSize: 12.5, color: '#1C1917', marginBottom: 6 }}>✓ {s}</div>
                      ))}
                    </div>
                    <div>
                      <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#B5502E', marginBottom: 8 }}>Improvements</div>
                      {(latestResume.score_details?.improvements ?? []).map((s) => (
                        <div key={s} style={{ fontSize: 12.5, color: '#1C1917', marginBottom: 6 }}>→ {s}</div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <div>
                  <p style={{ fontSize: 12, color: '#7A6B63', margin: '0 0 12px' }}>
                    Nodes are your resume's real strengths (solid) and improvement areas (dotted).
                  </p>
                  <ResumeSkillNetwork
                    strengths={latestResume.score_details?.strengths ?? []}
                    improvements={latestResume.score_details?.improvements ?? []}
                  />
                </div>
              )}
            </div>

            {/* Recent sessions — real */}
            <div style={{ background: '#FFFFFF', borderRadius: 18, border: '1.5px solid rgba(181,80,46,0.12)', padding: 28, boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }}>
              <h2 style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 18, fontWeight: 700, color: '#1C1917', margin: '0 0 18px' }}>Recent Sessions</h2>
              {sessions.length === 0 ? (
                <p style={{ fontSize: 13, color: '#7A6B63', margin: 0 }}>No mock interviews yet — start one to see it here.</p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  {sessions.slice(0, 5).map((s, i) => {
                    const prev = sessions[i + 1]
                    const delta = prev ? Math.round(s.average_score - prev.average_score) : null
                    return (
                      <div key={s.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 0', borderBottom: '1px solid rgba(181,80,46,0.08)' }}>
                        <div>
                          <div style={{ fontSize: 14, fontWeight: 600, color: '#1C1917' }}>{s.role}</div>
                          <div style={{ fontSize: 12, color: '#7A6B63', marginTop: 2 }}>{timeAgo(s.started_at)} · {s.status}</div>
                        </div>
                        <div style={{ textAlign: 'right' }}>
                          <div style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 20, fontWeight: 700, color: '#B5502E' }}>{Math.round(s.average_score)}</div>
                          {delta !== null && (
                            <div style={{ fontSize: 11, color: delta >= 0 ? '#16a34a' : '#dc2626', fontWeight: 600 }}>{delta >= 0 ? '+' : ''}{delta}</div>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Right sidebar */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div style={{ background: 'linear-gradient(160deg, #1C1917, #2E1F18)', borderRadius: 18, border: '1.5px solid rgba(224,164,88,0.20)', padding: 24, boxShadow: '0 4px 20px rgba(0,0,0,0.12)' }}>
              <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.10em', textTransform: 'uppercase', color: '#E0A458', marginBottom: 12 }}>Today's Focus</div>
              <div style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 18, fontWeight: 700, color: '#FAFAF8', lineHeight: 1.35, marginBottom: 16 }}>
                {dashboard?.weak_topics[0] || dashboard?.recommendations[0] || 'Start a mock interview to build your first focus area.'}
              </div>
              <button onClick={() => navigate('interview')} style={{ width: '100%', background: 'linear-gradient(135deg, #B5502E, #E0A458)', border: 'none', cursor: 'pointer', color: '#FAFAF8', fontSize: 13, fontWeight: 700, padding: '11px 0', borderRadius: 10, fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
                Start Session →
              </button>
            </div>

            <div style={{ background: '#FFFFFF', borderRadius: 18, border: '1.5px solid rgba(181,80,46,0.12)', padding: 24, boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }}>
              <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.10em', textTransform: 'uppercase', color: '#B5502E', marginBottom: 14 }}>Weak Spots</div>
              {dashboard?.weak_topics.length ? dashboard.weak_topics.map((t) => (
                <div key={t} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
                  <div style={{ width: 7, height: 7, borderRadius: '50%', background: '#B5502E', flexShrink: 0 }} />
                  <span style={{ fontSize: 13, color: '#4B3D37' }}>{t}</span>
                </div>
              )) : (
                <p style={{ fontSize: 12.5, color: '#7A6B63', margin: 0 }}>None flagged yet — complete a mock interview to surface weak topics.</p>
              )}
            </div>

            <div style={{ background: '#F5F2EE', borderRadius: 18, border: '1.5px solid rgba(181,80,46,0.10)', padding: 24 }}>
              <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.10em', textTransform: 'uppercase', color: '#7A6B63', marginBottom: 14 }}>Quick Nav</div>
              {(['roadmap', 'notes', 'mastery', 'mentor'] as Page[]).map((p) => (
                <button key={p} onClick={() => navigate(p)} style={{ display: 'block', width: '100%', textAlign: 'left', background: 'none', border: 'none', cursor: 'pointer', padding: '9px 0', fontSize: 14, fontWeight: 600, color: '#4B3D37', fontFamily: "'Plus Jakarta Sans', sans-serif", borderBottom: '1px solid rgba(181,80,46,0.08)', textTransform: 'capitalize' }}>
                  {p} →
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
