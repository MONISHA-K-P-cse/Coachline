import { useState, useEffect, useRef, useCallback } from 'react'
import { Nav } from '../components/Nav'
import { OrbitLoader } from '../components/OrbitLoader'
import { useAuth } from '../lib/AuthContext'
import * as api from '../lib/apiClient'
import Editor from '@monaco-editor/react'
import { 
  FileText, Shield, Sparkles, Award, Zap, Activity,
  Briefcase, TrendingUp, AlertTriangle, CheckCircle, 
  ArrowRight, Download, Copy, Play, Upload, Code2, RefreshCw
} from 'lucide-react'

type Page = 'landing' | 'login' | 'register' | 'onboarding' | 'workspace' | 'roadmap' | 'interview' | 'notes' | 'mastery' | 'mentor'
interface Props { navigate: (p: Page) => void }

// ─── Skill Network Graph SVG Component ───────────────────────────────────────
interface SkillNode { id: string; label: string; x: number; y: number; strength: number; missing?: boolean }

function layoutSkillNodes(strengths: string[], improvements: string[]): SkillNode[] {
  const nodes: SkillNode[] = [{ id: 'resume', label: 'Resume', x: 150, y: 110, strength: 0.9 }]
  const sCount = Math.min(strengths.length, 4)
  strengths.slice(0, 4).forEach((s, i) => {
    const angle = -Math.PI + ((i + 1) * Math.PI) / (sCount + 1)
    nodes.push({
      id: `s-${i}`,
      label: s.length > 20 ? s.slice(0, 18) + '…' : s,
      x: 150 + Math.cos(angle) * 95,
      y: 115 + Math.sin(angle) * 75,
      strength: 0.75,
    })
  })
  const mCount = Math.min(improvements.length, 3)
  improvements.slice(0, 3).forEach((s, i) => {
    const angle = ((i + 1) * Math.PI) / (mCount + 1)
    nodes.push({
      id: `m-${i}`,
      label: s.length > 20 ? s.slice(0, 18) + '…' : s,
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
  
  const finalStrengths = strengths.length > 0 ? strengths : ['Python APIs', 'React Design', 'SQL Tuning', 'System Dev']
  const finalImprovements = improvements.length > 0 ? improvements : ['CI/CD Pipeline', 'Redis Caching', 'Thread Safety']
  
  const nodes = layoutSkillNodes(finalStrengths, finalImprovements)
  const root = nodes[0]

  return (
    <svg viewBox="0 0 300 240" className="w-full block select-none">
      <defs>
        <filter id="skill-glow" x="-40%" y="-40%" width="180%" height="180%">
          <feGaussianBlur stdDeviation="3.5" result="blur"/>
          <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
      </defs>
      {nodes.slice(1).map((n) => (
        <path
          key={`edge-${n.id}`}
          d={`M ${root.x} ${root.y} L ${n.x} ${n.y}`}
          fill="none"
          className="transition-all duration-300"
          style={{ stroke: 'var(--rust)' }}
          strokeOpacity={n.missing ? 0.25 : 0.65}
          strokeWidth={n.missing ? 1 : 1.8}
          strokeDasharray={n.missing ? '4 3' : 'none'}
        />
      ))}
      {nodes.map((node) => {
        const isHov = hov === node.id
        const r = node.id === 'resume' ? 14 : isHov ? 12 : 9
        return (
          <g 
            key={node.id} 
            transform={`translate(${node.x},${node.y})`} 
            className="cursor-pointer"
            onMouseEnter={() => setHov(node.id)} 
            onMouseLeave={() => setHov(null)}
          >
            {node.missing ? (
              <>
                <circle r={r} style={{ fill: 'var(--bg)', stroke: 'var(--rust)' }} strokeWidth="1.2" strokeOpacity="0.5" strokeDasharray="3 2" />
                <text textAnchor="middle" dy="3" style={{ fill: 'var(--rust)', fontSize: '8px', fontWeight: 'bold' }} fillOpacity="0.8">+</text>
              </>
            ) : (
              <circle r={r} style={{ fill: 'var(--rust)' }} filter={isHov ? 'url(#skill-glow)' : 'none'} />
            )}
            <text 
              dy={r + 14} 
              textAnchor="middle" 
              style={{ 
                fill: node.missing ? 'var(--text-muted)' : isHov ? 'var(--rust)' : 'var(--text)',
                fontSize: '8.5px', 
                fontWeight: isHov ? 700 : 500 
              }}
              fillOpacity={node.missing ? 0.6 : 0.85}
            >
              {node.label}
            </text>
          </g>
        )
      })}
    </svg>
  )
}

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

  const [activeTab, setActiveTab] = useState<'dashboard' | 'resume' | 'bob'>(() => (localStorage.getItem('active_workspace_tab') as any) || 'dashboard')
  const [dashboard, setDashboard] = useState<api.DashboardSummary | null>(null)
  const [resumes, setResumes] = useState<api.ResumeResponse[]>([])
  const [sessions, setSessions] = useState<api.InterviewSession[]>([])
  const [topicMastery, setTopicMastery] = useState<api.TopicMasteryEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)

  useEffect(() => {
    localStorage.removeItem('active_workspace_tab')
  }, [])


  const [improving, setImproving] = useState(false)
  const [showImproveModal, setShowImproveModal] = useState(false)
  const [improvedResume, setImprovedResume] = useState<api.ResumeImprovementResponse | null>(null)
  const [downloadingPdf, setDownloadingPdf] = useState(false)

  const [bobChallengeId, setBobChallengeId] = useState('sql_injection')
  const [bobCode, setBobCode] = useState('def get_user_data(username):\n    query = f"SELECT * FROM users WHERE username = \'{username}\'"\n    return db.execute(query)')
  const [bobAuditing, setBobAuditing] = useState(false)
  const [bobAuditResult, setBobAuditResult] = useState<api.BobAuditResponse | null>(null)
  const [bobRec, setBobRec] = useState<api.BobRecommendationResponse | null>(null)

  useEffect(() => {
    if (bobChallengeId === 'sql_injection') {
      setBobCode('def get_user_data(username):\n    query = f"SELECT * FROM users WHERE username = \'{username}\'"\n    return db.execute(query)')
    } else if (bobChallengeId === 'concurrency_race') {
      setBobCode('counter = 0\ndef increment_counter():\n    global counter\n    current = counter\n    time.sleep(0.01)\n    counter = current + 1')
    } else if (bobChallengeId === 'cors_security') {
      setBobCode('app.use((req, res, next) => {\n    res.setHeader(\'Access-Control-Allow-Origin\', \'*\');\n    res.setHeader(\'Access-Control-Allow-Methods\', \'GET, POST\');\n    next();\n});')
    } else if (bobChallengeId === 'xss_scripting') {
      setBobCode('const userComment = req.query.comment;\nres.send(`<div>${userComment}</div>`);')
    } else if (bobChallengeId === 'path_traversal') {
      setBobCode('def read_user_file(filename):\n    filepath = f"/var/www/uploads/{filename}"\n    with open(filepath, "r") as f:\n        return f.read()')
    }
  }, [bobChallengeId])

  const handleBobAudit = async () => {
    setBobAuditing(true)
    try {
      const res = await api.auditCode(bobCode, bobChallengeId)
      setBobAuditResult(res)
    } catch (err) {
      alert('IBM Bob Code Audit failed. Please try again.')
    } finally {
      setBobAuditing(false)
    }
  }

  const loadAll = useCallback(async () => {
    const [d, r, s, tm, rec] = await Promise.all([
      api.getDashboard(),
      api.listResumes(),
      api.listInterviewSessions(),
      api.getTopicMastery(),
      api.getBobRecommendation().catch(() => null),
    ])
    setDashboard(d)
    setResumes(r)
    setSessions(s)
    setTopicMastery(tm)
    if (rec) {
      setBobRec(rec)
      setBobChallengeId(rec.challenge_id)
    }
  }, [])

  useEffect(() => {
    loadAll().finally(() => setLoading(false))
  }, [loadAll])

  const renderFormattedResume = (text: string) => {
    return text.split('\n').map((line, idx) => {
      const trimmed = line.trim();
      if (!trimmed) return <div key={idx} className="h-2" />;
      
      if (trimmed.startsWith('###') || trimmed.startsWith('##') || trimmed.startsWith('#')) {
        const cleanHeading = trimmed.replace(/[#*]/g, '').trim();
        return (
          <h3 key={idx} className="font-display text-sm font-bold text-rust mt-4 mb-2 border-b border-border/60 pb-1">
            {cleanHeading}
          </h3>
        )
      }
      if (trimmed.startsWith('**') && trimmed.endsWith('**')) {
        const cleanHeading = trimmed.replace(/\*/g, '').trim();
        return (
          <h4 key={idx} className="font-semibold text-xs text-text mt-3 mb-1">
            {cleanHeading}
          </h4>
        )
      }
      if (trimmed.startsWith('-') || trimmed.startsWith('*')) {
        const cleanBullet = trimmed.substring(1).replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').trim();
        return (
          <li key={idx} className="text-xs text-text-muted leading-relaxed ml-4 list-disc mb-1" dangerouslySetInnerHTML={{ __html: cleanBullet }} />
        )
      }
      const formattedLine = trimmed.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
      return (
        <p key={idx} className="text-xs text-text-muted leading-relaxed my-1" dangerouslySetInnerHTML={{ __html: formattedLine }} />
      )
    })
  }

  const latestResume = resumes[0]

  const handleImproveResume = async () => {
    if (!latestResume) return
    setImproving(true)
    try {
      const res = await api.improveResume(latestResume.id)
      setImprovedResume(res)
      setShowImproveModal(true)
    } catch (err) {
      console.error(err)
      alert("Failed to optimize resume. Please try again.")
    } finally {
      setImproving(false)
    }
  }

  const handleDownloadPDF = async () => {
    if (!improvedResume) return
    setDownloadingPdf(true)
    try {
      await api.downloadImprovedPDF(
        improvedResume.improved_text,
        `optimized_resume_${latestResume?.id || 'doc'}.pdf`
      )
    } catch (err) {
      console.error(err)
      alert("Failed to download PDF. Please try again.")
    } finally {
      setDownloadingPdf(false)
    }
  }

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
      <div className="min-h-screen bg-bg">
        <Nav page="workspace" navigate={navigate} />
        <OrbitLoader label="Syncing your workspace..." size={80} />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-bg text-text transition-colors duration-300 font-sans pb-16">
      <Nav page="workspace" navigate={navigate} />
      <input ref={fileInputRef} type="file" accept=".pdf,.docx" onChange={handleFileSelected} className="hidden" />

      {/* Main Container */}
      <div className="max-w-6xl mx-auto px-6 pt-10">
        
        {/* Welcome Header Banner */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-10 border-b border-border/50 pb-8">
          <div>
            <span className="text-[10px] uppercase font-bold tracking-wider text-rust">Workspace Overview</span>
            <h1 className="font-display text-3xl md:text-4xl font-bold tracking-tight text-text mt-1">
              {user?.full_name ? `Welcome, ${user.full_name.split(' ')[0]}.` : 'Welcome back.'}
            </h1>
            <p className="text-xs text-text-muted mt-2">
              {dashboard?.days_until_interview != null && dashboard.target_company ? (
                <>
                  You have an interview with <span className="text-rust font-bold">{dashboard.target_company}</span> in <span className="text-rust font-bold">{dashboard.days_until_interview} days</span>.
                </>
              ) : (
                'Setup your target role and date in onboarding to begin calculations.'
              )}
            </p>
          </div>

          {/* Sub Navigation Tabs */}
          <div className="flex bg-panel-bg p-1 rounded-xl border border-border/80 w-fit self-start">
            {[
              { id: 'dashboard', label: 'Bento Dashboard', icon: TrendingUp },
              { id: 'resume', label: 'Resume Intelligence', icon: FileText },
              { id: 'bob', label: 'IBM Bob Auditor', icon: Shield }
            ].map((tab) => {
              const Icon = tab.icon
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold tracking-wide transition-all cursor-pointer ${
                    activeTab === tab.id
                      ? 'bg-card-bg text-rust shadow-sm'
                      : 'text-text-muted hover:text-text'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {tab.label}
                </button>
              )
            })}
          </div>
        </div>

        {/* ── BENTO DASHBOARD TAB ─────────────────────────────────────────── */}
        {activeTab === 'dashboard' && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            
            {/* Column 1 & 2: Primary metrics */}
            <div className="md:col-span-2 flex flex-col gap-6">
              
              {/* Overall Readiness Bento Card */}
              <div className="p-6 rounded-2xl border border-border bg-card-bg/60 glass-panel flex flex-col sm:flex-row items-center justify-between gap-6">
                <div>
                  <span className="text-[10px] font-bold tracking-wider uppercase text-text-muted">Target Readiness</span>
                  <h2 className="font-display text-xl font-bold text-text mt-1.5">Your Readiness Rating</h2>
                  <p className="text-xs text-text-muted mt-2 leading-relaxed max-w-sm">
                    Calculated from overall resume score and websocket mock performance metrics.
                  </p>
                  <div className="flex items-center gap-4 mt-6">
                    <button
                      onClick={() => navigate('interview')}
                      className="px-4 py-2 text-xs font-semibold text-white bg-rust hover:bg-rust/90 rounded-lg transition-colors cursor-pointer"
                    >
                      Conduct Simulation
                    </button>
                    <button
                      onClick={() => setActiveTab('resume')}
                      className="px-4 py-2 text-xs font-semibold text-text border border-border bg-bg/40 hover:bg-border/20 rounded-lg transition-colors cursor-pointer"
                    >
                      Audit Resume
                    </button>
                  </div>
                </div>

                {/* Ring Gauge Chart */}
                <div className="relative flex items-center justify-center w-28 h-28">
                  <svg className="w-full h-full transform -rotate-90">
                    <circle cx="56" cy="56" r="46" stroke="var(--border)" strokeWidth="6" fill="transparent" />
                    <circle 
                      cx="56" 
                      cy="56" 
                      r="46" 
                      stroke="var(--rust)" 
                      strokeWidth="6" 
                      fill="transparent" 
                      strokeDasharray="289"
                      strokeDashoffset={289 - (289 * (dashboard?.overall_readiness_score ?? 0)) / 100}
                      strokeLinecap="round"
                    />
                  </svg>
                  <div className="absolute text-center">
                    <span className="font-display text-2xl font-bold text-rust">{dashboard?.overall_readiness_score ?? 0}%</span>
                    <span className="block text-[8px] uppercase tracking-wider font-semibold text-text-muted mt-0.5">Ready</span>
                  </div>
                </div>
              </div>

              {/* Grid bento layout for sessions & targets */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                
                {/* Stats Card: Sessions */}
                <div className="p-6 rounded-2xl border border-border bg-card-bg/60 glass-panel">
                  <span className="text-[10px] font-bold tracking-wider uppercase text-text-muted">Weekly Practice</span>
                  <div className="font-display text-4xl font-bold text-rust mt-3">{sessionsThisWeek}</div>
                  <p className="text-xs text-text-muted mt-2">
                    Sessions conducted in the last 7 days. ({sessions.length} total sessions).
                  </p>
                </div>

                {/* Stats Card: Topics */}
                <div className="p-6 rounded-2xl border border-border bg-card-bg/60 glass-panel">
                  <span className="text-[10px] font-bold tracking-wider uppercase text-text-muted">Topics Mastered</span>
                  <div className="font-display text-4xl font-bold text-rust mt-3">
                    {masteredCount} <span className="text-sm font-sans text-text-muted">/ {topicMastery.length}</span>
                  </div>
                  <p className="text-xs text-text-muted mt-2">
                    Mastered score of 70+ required. {topicMastery.length - masteredCount} topics pending.
                  </p>
                </div>
              </div>

              {/* Recent Sessions list */}
              <div className="p-6 rounded-2xl border border-border bg-card-bg/60 glass-panel">
                <h3 className="font-display text-base font-bold text-text mb-4">Latest Interview Sessions</h3>
                {sessions.length === 0 ? (
                  <p className="text-xs text-text-muted italic">No mock sessions completed yet.</p>
                ) : (
                  <div className="flex flex-col gap-2">
                    {sessions.slice(0, 3).map((s, idx) => {
                      const prev = sessions[idx + 1]
                      const delta = prev ? Math.round(s.average_score - prev.average_score) : null
                      return (
                        <div key={s.id} className="flex items-center justify-between py-3 border-b border-border/40 last:border-0">
                          <div>
                            <span className="text-xs font-bold text-text">{s.role}</span>
                            <div className="text-[10px] text-text-muted mt-0.5">
                              {timeAgo(s.started_at)} · Status: {s.status}
                            </div>
                          </div>
                          <div className="flex items-center gap-3">
                            <span className="font-display text-lg font-bold text-rust">{Math.round(s.average_score)}</span>
                            {delta !== null && (
                              <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${delta >= 0 ? 'bg-green-500/10 text-green-500' : 'bg-red-500/10 text-red-500'}`}>
                                {delta >= 0 ? '+' : ''}{delta}
                              </span>
                            )}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            </div>

            {/* Sidebar Column 3: Recommendations & Weak Areas */}
            <div className="flex flex-col gap-6">
              
              {/* Daily Focus Callout */}
              <div className="p-6 rounded-2xl border border-rust/20 bg-gradient-to-br from-panel-bg to-bg relative overflow-hidden shadow-lg shadow-rust/5">
                <span className="text-[10px] font-bold tracking-wider uppercase text-rust">Target Focus</span>
                <h3 className="font-display text-base font-bold text-text mt-2 leading-tight">
                  {dashboard?.weak_topics[0] || 'Analyze weak topics'}
                </h3>
                <p className="text-xs text-text-muted mt-3 leading-relaxed">
                  Based on recent evaluations, prioritize mock loop simulations on this domain.
                </p>
                <button
                  onClick={() => navigate('interview')}
                  className="w-full mt-6 py-2.5 rounded-xl text-white font-semibold text-xs bg-rust hover:bg-rust/90 transition-colors cursor-pointer flex items-center justify-center gap-1.5"
                >
                  <span>Practice Topic</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>

              {/* Weak spots list */}
              <div className="p-6 rounded-2xl border border-border bg-card-bg/60 glass-panel">
                <span className="text-[10px] font-bold tracking-wider uppercase text-text-muted">Weak Spots</span>
                <div className="flex flex-col gap-3 mt-4">
                  {dashboard?.weak_topics.length ? (
                    dashboard.weak_topics.map((t) => (
                      <div key={t} className="flex items-center gap-2">
                        <AlertTriangle className="w-3.5 h-3.5 text-rust/80 flex-shrink-0" />
                        <span className="text-xs text-text-muted font-medium">{t}</span>
                      </div>
                    ))
                  ) : (
                    <p className="text-xs text-text-muted italic">Complete mock loops to scan weak competencies.</p>
                  )}
                </div>
              </div>

              {/* IBM Bob Dashboard Integration Card */}
              <div className="p-6 rounded-2xl border border-rust/15 bg-card-bg/60 glass-panel flex flex-col gap-4">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold tracking-wider uppercase text-text-muted">IBM Bob Coach</span>
                  <span className="text-[9px] uppercase tracking-wider text-rust bg-rust/10 px-2 py-0.5 rounded-full font-bold">
                    Active
                  </span>
                </div>
                
                {bobRec ? (
                  <div className="flex flex-col gap-3">
                    <h3 className="font-display text-sm font-bold text-text leading-snug">
                      Bob recommends: {bobRec.topic} Practice
                    </h3>
                    <p className="text-xs text-text-muted leading-relaxed">
                      💡 {bobRec.reason}
                    </p>
                    <button
                      onClick={() => setActiveTab('bob')}
                      className="w-full py-2.5 rounded-xl text-white font-semibold text-xs bg-rust hover:bg-rust/90 transition-all flex items-center justify-center gap-1.5 cursor-pointer"
                    >
                      <Shield className="w-3.5 h-3.5" />
                      <span>Launch Bob Labs</span>
                    </button>
                  </div>
                ) : (
                  <div className="flex flex-col gap-2">
                    <p className="text-xs text-text-muted italic">
                      Scan your interview performance to load security recommendations.
                    </p>
                    <button
                      onClick={() => setActiveTab('bob')}
                      className="w-full py-2.5 rounded-xl text-text border border-border bg-bg/40 hover:bg-border/20 transition-all flex items-center justify-center gap-1.5 cursor-pointer"
                    >
                      <Shield className="w-3.5 h-3.5" />
                      <span>Open Auditor</span>
                    </button>
                  </div>
                )}
              </div>

              {/* Quick Navigation Links */}
              <div className="p-6 rounded-2xl border border-border bg-card-bg/60 glass-panel">
                <span className="text-[10px] font-bold tracking-wider uppercase text-text-muted">Navigation Links</span>
                <div className="flex flex-col gap-1.5 mt-4">
                  {(['roadmap', 'notes', 'mastery', 'mentor'] as Page[]).map((p) => (
                    <button
                      key={p}
                      onClick={() => navigate(p)}
                      className="w-full flex items-center justify-between text-left text-xs font-semibold py-2.5 border-b border-border/40 last:border-0 text-text-muted hover:text-text capitalize transition-colors cursor-pointer"
                    >
                      <span>Study {p}</span>
                      <ArrowRight className="w-3.5 h-3.5 opacity-60" />
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── RESUME INTELLIGENCE TAB ────────────────────────────────────── */}
        {activeTab === 'resume' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            {/* Upload Area & Graph representation */}
            <div className="lg:col-span-2 flex flex-col gap-6">
              
              {/* Resume analysis display */}
              <div className="p-6 rounded-2xl border border-border bg-card-bg/60 glass-panel">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h3 className="font-display text-base font-bold text-text">Resume Review & Metrics</h3>
                    <p className="text-xs text-text-muted mt-0.5">Calculated overall scoring, strengths and improvements.</p>
                  </div>
                </div>

                {/* Upload drag-and-drop placeholder */}
                {uploadError && (
                  <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-500 text-xs font-semibold rounded-xl mb-4">
                    {uploadError}
                  </div>
                )}

                {analyzing ? (
                  <OrbitLoader label="Parsing Resume ATS metrics..." size={64} />
                ) : !latestResume ? (
                  <div className="flex flex-col items-center justify-center border-2 border-dashed border-border/80 hover:border-rust/40 rounded-2xl py-12 px-6 text-center cursor-pointer transition-colors" onClick={() => fileInputRef.current?.click()}>
                    <Upload className="w-8 h-8 text-rust/80 mb-3" />
                    <span className="text-xs font-bold text-text">Upload Resume PDF / Word</span>
                    <span className="text-[10px] text-text-muted mt-1">Accepts documents up to 5MB</span>
                  </div>
                ) : (
                  <div className="flex flex-col gap-6">
                    
                    {/* ATS and overall counts */}
                    <div className="grid grid-cols-3 gap-4 border-b border-border/40 pb-5">
                      <div>
                        <div className="font-display text-3xl font-bold text-rust">{latestResume.score}%</div>
                        <span className="text-[9px] uppercase font-bold tracking-wider text-text-muted">Overall Score</span>
                      </div>
                      <div>
                        <div className="font-display text-3xl font-bold text-accent">{latestResume.ats_score}%</div>
                        <span className="text-[9px] uppercase font-bold tracking-wider text-text-muted">ATS Parsing</span>
                      </div>
                      <div>
                        <div className="font-display text-3xl font-bold text-text">{latestResume.keyword_count}</div>
                        <span className="text-[9px] uppercase font-bold tracking-wider text-text-muted">Keywords Count</span>
                      </div>
                    </div>

                    {/* Summary description */}
                    {latestResume.score_details?.summary && (
                      <p className="text-xs text-text-muted italic leading-relaxed">
                        "{latestResume.score_details.summary}"
                      </p>
                    )}

                    {/* Strengths & Improvements */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                      <div>
                        <h4 className="text-[10px] font-bold tracking-wider uppercase text-green-500 mb-3">Strengths</h4>
                        <div className="flex flex-col gap-2">
                          {(latestResume.score_details?.strengths ?? []).map((s, i) => (
                            <div key={i} className="flex items-start gap-2 text-xs text-text-muted">
                              <CheckCircle className="w-3.5 h-3.5 text-green-500/80 mt-0.5 flex-shrink-0" />
                              <span>{s}</span>
                            </div>
                          ))}
                        </div>
                      </div>

                      <div>
                        <h4 className="text-[10px] font-bold tracking-wider uppercase text-rust mb-3">Improvements</h4>
                        <div className="flex flex-col gap-2">
                          {(latestResume.score_details?.improvements ?? []).map((s, i) => (
                            <div key={i} className="flex items-start gap-2 text-xs text-text-muted">
                              <AlertTriangle className="w-3.5 h-3.5 text-rust/80 mt-0.5 flex-shrink-0" />
                              <span>{s}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Upload trigger button bar */}
              {latestResume && !analyzing && (
                <div className="flex items-center justify-between p-4 rounded-xl border border-border bg-card-bg/60 glass-panel">
                  <span className="text-xs text-text-muted">Need a fresh analysis?</span>
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="px-4 py-2 text-xs font-semibold text-white bg-rust hover:bg-rust/90 rounded-lg transition-colors cursor-pointer"
                  >
                    Upload New Version
                  </button>
                </div>
              )}
            </div>

            {/* Sidebar Column: Bullet optimizations */}
            <div className="flex flex-col gap-6">
              
              {/* Bullet Optimizer Card */}
              <div className="p-6 rounded-2xl border border-rust/10 bg-gradient-to-br from-panel-bg to-bg relative overflow-hidden shadow-lg shadow-rust/5">
                <span className="text-[10px] font-bold tracking-wider uppercase text-rust">Resume Tuning</span>
                <h3 className="font-display text-base font-bold text-text mt-2 leading-tight">
                  Bullet Points Optimizer
                </h3>
                <p className="text-xs text-text-muted mt-3 leading-relaxed">
                  Rewrites your bullet points using the STAR method (Situation, Task, Action, Result) to capture metrics and tech indicators Bob scans for.
                </p>
                <button
                  onClick={handleImproveResume}
                  disabled={improving || !latestResume}
                  className={`w-full mt-6 py-2.5 rounded-xl text-white font-semibold text-xs transition-colors flex items-center justify-center gap-1.5 cursor-pointer ${
                    improving || !latestResume ? 'bg-rust/40 cursor-not-allowed' : 'bg-rust hover:bg-rust/90 shadow'
                  }`}
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>{improving ? 'Improving Bullets...' : 'Optimize with AI'}</span>
                </button>
              </div>

              {/* Rewrite Suggestions Preview widget */}
              <div className="p-6 rounded-2xl border border-border bg-card-bg/60 glass-panel">
                <h3 className="font-display text-xs font-bold uppercase tracking-wider text-text-muted mb-4">
                  Sample Suggestions
                </h3>
                {latestResume?.score_details?.rewrite_suggestions?.length ? (
                  <div className="flex flex-col gap-3">
                    {latestResume.score_details.rewrite_suggestions.slice(0, 2).map((s, i) => (
                      <div key={i} className="text-xs border-b border-border/40 pb-3 last:border-0 last:pb-0">
                        <div className="font-bold text-rust text-[10px] uppercase tracking-wide">{s.reason}</div>
                        <p className="text-[11px] text-text-muted mt-1 italic">"{s.original}"</p>
                        <p className="text-[11px] text-text font-medium mt-1">"✓ {s.rewritten}"</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-text-muted italic">Upload a resume to render rewrites.</p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ── IBM BOB CODE AUDITOR TAB ───────────────────────────────────── */}
        {activeTab === 'bob' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            {/* Monaco Editor IDE Layout */}
            <div className="lg:col-span-2 flex flex-col gap-6">
              
              {/* Terminal IDE Frame */}
              <div className="rounded-2xl border border-border bg-terminal-bg shadow-2xl overflow-hidden flex flex-col">
                {/* File Header Tab bar */}
                <div className="bg-bg/90 border-b border-border/80 px-4 py-3 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="flex gap-1.5">
                      <div className="w-2.5 h-2.5 rounded-full bg-red-500/70" />
                      <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/70" />
                      <div className="w-2.5 h-2.5 rounded-full bg-green-500/70" />
                    </div>
                    <span className="text-[10px] text-text-muted/80 font-mono tracking-tight ml-3">
                      auditor_workspace.py
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-[10px] text-rust font-semibold flex items-center gap-1">
                      <Code2 className="w-3.5 h-3.5" />
                      IBM Granite Client
                    </span>
                  </div>
                </div>

                {/* Monaco Editor Container */}
                <div className="p-1 min-h-[220px]">
                  <Editor
                    height="200px"
                    defaultLanguage="python"
                    theme="vs-dark"
                    value={bobCode}
                    onChange={(val) => setBobCode(val || '')}
                    options={{
                      minimap: { enabled: false },
                      fontSize: 12,
                      lineNumbers: 'on',
                      roundedSelection: true,
                      scrollBeyondLastLine: false,
                      readOnly: false,
                      padding: { top: 8, bottom: 8 },
                      backgroundColor: 'transparent'
                    }}
                  />
                </div>

                {/* Execute Bar */}
                <div className="bg-bg/50 border-t border-border/80 px-4 py-3 flex items-center justify-between">
                  <span className="text-[10px] text-text-muted font-semibold">
                    Python Sandbox environment active.
                  </span>
                  <button
                    onClick={handleBobAudit}
                    disabled={bobAuditing}
                    className={`px-4 py-1.5 rounded-lg text-white text-xs font-semibold transition-colors flex items-center gap-1.5 cursor-pointer ${
                      bobAuditing ? 'bg-rust/60 cursor-not-allowed' : 'bg-rust hover:bg-rust/90'
                    }`}
                  >
                    <Play className="w-3.5 h-3.5 fill-current" />
                    <span>{bobAuditing ? 'Auditing Code...' : 'Audit Code'}</span>
                  </button>
                </div>
              </div>

              {/* Secure refactored comparisons */}
              {bobAuditResult && (
                <div className="p-6 rounded-2xl border border-border bg-card-bg/60 glass-panel">
                  <h3 className="font-display text-base font-bold text-text mb-4">IBM Bob Refactored Code Fix</h3>
                  <div className="rounded-xl border border-border bg-terminal-bg p-4 overflow-x-auto text-left">
                    <pre className="text-xs text-accent font-mono leading-relaxed">{bobAuditResult.refactored_code}</pre>
                  </div>
                </div>
              )}
            </div>

            {/* Sidebar Column: Vulnerability list & timeline */}
            <div className="flex flex-col gap-6">
              
              {/* Select Security loop config */}
              <div className="p-6 rounded-2xl border border-border bg-card-bg/60 glass-panel flex flex-col gap-3">
                <div>
                  <span className="text-[10px] font-bold tracking-wider uppercase text-text-muted">Auditing Loop</span>
                  <h3 className="font-display text-base font-bold text-text mt-1.5">Select Vulnerability</h3>
                </div>
                
                {bobRec && (
                  <div className="p-3.5 rounded-xl border border-rust/20 bg-rust/5 text-xs text-text leading-relaxed font-semibold">
                    💡 <span className="text-rust">Bob's Recommendation:</span> {bobRec.reason}
                  </div>
                )}

                <div className="mt-1">
                  <select
                    value={bobChallengeId}
                    onChange={(e) => setBobChallengeId(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl border border-border bg-bg/50 text-xs font-semibold text-text focus:outline-none focus:border-rust/80 transition-colors"
                  >
                    <option value="sql_injection">SQL Injection</option>
                    <option value="concurrency_race">Race Conditions</option>
                    <option value="cors_security">CORS Wildcards</option>
                    <option value="xss_scripting">XSS Scripting</option>
                    <option value="path_traversal">Path Traversal</option>
                  </select>
                </div>
              </div>

              {/* Audit Scan list */}
              {bobAuditResult ? (
                <div className="flex flex-col gap-6">
                  
                  {/* Step audit timeline */}
                  <div className="p-6 rounded-2xl border border-border bg-card-bg/60 glass-panel">
                    <span className="text-[10px] font-bold tracking-wider uppercase text-text-muted">Timeline Audit Plan</span>
                    <div className="flex flex-col gap-4 mt-4">
                      {bobAuditResult.plan.map((step, idx) => (
                        <div key={idx} className="flex gap-3 text-xs leading-relaxed">
                          <span className="font-bold text-rust">{idx + 1}.</span>
                          <span className="text-text-muted">{step}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Flagged logs */}
                  <div className="p-6 rounded-2xl border border-border bg-card-bg/60 glass-panel flex flex-col gap-4">
                    <span className="text-[10px] font-bold tracking-wider uppercase text-text-muted">Flags Details</span>
                    {bobAuditResult.vulnerabilities.map((v, i) => (
                      <div key={i} className="text-xs p-4 rounded-xl bg-red-500/5 border border-red-500/25 flex flex-col gap-2">
                        <div className="flex items-center justify-between font-bold">
                          <span className="text-red-500">[{v.severity} Severity]</span>
                          <span className="text-text-muted">Line {v.line}</span>
                        </div>
                        <p className="text-text font-semibold leading-relaxed">{v.issue}</p>
                        <p className="text-green-500 font-semibold mt-1">💡 Fix: {v.fix}</p>
                      </div>
                    ))}
                  </div>

                </div>
              ) : (
                <div className="p-6 rounded-2xl border border-border bg-card-bg/40 text-center py-10">
                  <p className="text-xs text-text-muted italic leading-relaxed">
                    Choose a challenge, review python templates, and press "Audit Code" to scan security risks.
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* ── MODAL: RESUME IMPROVEMENTS VIEW ──────────────────────────────── */}
      {showImproveModal && improvedResume && (
        <div className="fixed inset-0 w-screen h-screen bg-bg/50 backdrop-blur-md flex items-center justify-center z-50 p-6">
          <div className="w-full max-w-5xl max-h-[85vh] bg-card-bg rounded-2xl border border-border flex flex-col overflow-hidden shadow-2xl glass-panel">
            {/* Header */}
            <div className="p-5 border-b border-border/80 flex items-center justify-between">
              <div>
                <h2 className="font-display text-lg font-bold text-text">Optimized Resume suggestions</h2>
                <p className="text-[10px] text-text-muted mt-0.5">Applied modifications to increase ATS and secure loop readiness.</p>
              </div>
              <button 
                onClick={() => setShowImproveModal(false)}
                className="text-text-muted hover:text-text text-lg cursor-pointer"
              >
                ✕
              </button>
            </div>

            {/* Scrollable Comparison Content */}
            <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-6">
              
              {/* Changes applied callout */}
              <div className="p-4 rounded-xl bg-rust/5 border border-rust/15 text-xs text-text-muted">
                <span className="font-bold text-rust block mb-2 uppercase tracking-wider text-[10px]">Optimizations Applied</span>
                <ul className="list-disc ml-4 flex flex-col gap-1.5">
                  {improvedResume.changes_made.map((c, i) => <li key={i}>{c}</li>)}
                </ul>
              </div>

              {/* Side by side comparison panels */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                
                {/* Original Preview */}
                <div>
                  <span className="text-[10px] uppercase font-bold tracking-wider text-text-muted mb-2 block">Original Document</span>
                  <div className="p-5 rounded-xl border border-border/60 bg-bg/40 text-xs text-text-muted leading-relaxed font-sans overflow-y-auto h-72 white-space-pre">
                    {latestResume?.parsed_text_preview || 'Original parsed text preview.'}
                  </div>
                </div>

                {/* Optimized Render */}
                <div>
                  <span className="text-[10px] uppercase font-bold tracking-wider text-rust mb-2 block">AI Improved Document</span>
                  <div className="p-6 rounded-xl border border-rust/20 bg-card-bg text-xs leading-relaxed font-sans overflow-y-auto h-72 shadow-inner">
                    {renderFormattedResume(improvedResume.improved_text)}
                  </div>
                </div>
              </div>
            </div>

            {/* Footer Action Bar */}
            <div className="bg-bg/40 border-t border-border p-4 flex items-center justify-end gap-3">
              <button
                onClick={() => setShowImproveModal(false)}
                className="px-4 py-2 border border-border hover:bg-border/20 rounded-lg text-xs font-semibold text-text-muted hover:text-text transition-colors cursor-pointer"
              >
                Close View
              </button>
              <button
                onClick={() => {
                  navigator.clipboard.writeText(improvedResume.improved_text)
                  alert('Copied improved text to clipboard!')
                }}
                className="px-4 py-2 border border-rust/35 hover:bg-rust/5 rounded-lg text-xs font-semibold text-rust transition-colors cursor-pointer flex items-center gap-1.5"
              >
                <Copy className="w-3.5 h-3.5" />
                <span>Copy Text</span>
              </button>
              <button
                onClick={handleDownloadPDF}
                disabled={downloadingPdf}
                className="px-4 py-2 bg-rust hover:bg-rust/90 text-white rounded-lg text-xs font-bold transition-colors cursor-pointer flex items-center gap-1.5 shadow"
              >
                <Download className="w-3.5 h-3.5" />
                <span>{downloadingPdf ? 'Downloading PDF...' : 'Download PDF'}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
