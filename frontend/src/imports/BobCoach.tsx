import { useState, useEffect, useRef, useCallback } from 'react'
import { Nav } from '../components/Nav'
import { OrbitLoader } from '../components/OrbitLoader'
import { useAuth } from '../lib/AuthContext'
import * as api from '../lib/apiClient'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Shield, MessageSquare, Send, Award, Play, AlertTriangle, 
  ArrowRight, ShieldCheck, HelpCircle, ChevronRight, Zap, RefreshCw 
} from 'lucide-react'

type Page = 'landing' | 'login' | 'register' | 'onboarding' | 'workspace' | 'roadmap' | 'interview' | 'notes' | 'mastery' | 'mentor' | 'bob_coach'
const MAX_CANDIDATE_TURNS = 5
interface Props { navigate: (p: Page) => void }

export default function BobCoach({ navigate }: Props) {
  const { user } = useAuth()
  const [history, setHistory] = useState<api.BobCoachHistoryEntry[]>([])
  const [activeSession, setActiveSession] = useState<api.BobCoachSessionDetails | null>(null)
  const [loading, setLoading] = useState(true)
  const [starting, setStarting] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // Scenario state
  const [selectedLanguage, setSelectedLanguage] = useState('Python')
  const [responseText, setResponseText] = useState('')
  const chatEndRef = useRef<HTMLDivElement>(null)

  const loadHistory = useCallback(async () => {
    try {
      const data = await api.getBobCoachHistory()
      setHistory(data || [])
    } catch (err) {
      console.error(err)
      setHistory([])
    }
  }, [])

  useEffect(() => {
    Promise.all([loadHistory()]).finally(() => setLoading(false))
  }, [loadHistory])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [activeSession?.conversation])

  const handleStart = async (roleOverride?: string, languageOverride?: string) => {
    setStarting(true)
    setError(null)
    setActiveSession(null)
    try {
      const targetRole = roleOverride || user?.profile?.target_role || "Software Engineer"
      const lang = languageOverride || selectedLanguage
      const res = await api.startBobCoachScenario(targetRole, lang)
      // Immediately fetch session details to load standard conversation structure
      const details = await api.getBobCoachSessionDetails(res.session_id)
      setActiveSession(details)
      loadHistory()
    } catch (err) {
      setError(err instanceof api.ApiError ? err.message : 'Could not initialize scenario coach.')
    } finally {
      setStarting(false)
    }
  }

  const handleRespond = async () => {
    if (!activeSession || !responseText.trim() || submitting) return
    const text = responseText.trim()
    setResponseText('')
    setSubmitting(true)
    setError(null)

    // Optimistically update conversation
    const optConversation = [...activeSession.conversation, { sender: 'candidate', text }]
    setActiveSession({
      ...activeSession,
      conversation: optConversation
    })

    try {
      const res = await api.respondToBobCoachScenario(activeSession.id, text)
      // Retrieve fully updated session details (which will include Bob's response or evaluation results)
      const details = await api.getBobCoachSessionDetails(activeSession.id)
      setActiveSession(details)
      if (res.completed) {
        loadHistory()
      }
    } catch (err) {
      setError(err instanceof api.ApiError ? err.message : 'Failed to send response.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleSelectSession = async (id: number) => {
    setLoading(true)
    setError(null)
    try {
      const details = await api.getBobCoachSessionDetails(id)
      setActiveSession(details)
    } catch (err) {
      setError('Could not load session details.')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-bg">
        <Nav page="bob_coach" navigate={navigate} />
        <OrbitLoader label="Loading scenario history..." size={72} />
      </div>
    )
  }

  const candidateTurns = activeSession && activeSession.conversation
    ? (activeSession.conversation || []).filter(c => c.sender === 'candidate').length
    : 0

  return (
    <div className="min-h-screen bg-bg text-text transition-colors duration-300 font-sans pb-16">
      <Nav page="bob_coach" navigate={navigate} />

      <div className="max-w-5xl mx-auto px-6 pt-10">
        {/* Header Block */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-10 border-b border-border/50 pb-8">
          <div>
            <span className="text-[10px] uppercase font-bold tracking-wider text-rust flex items-center gap-1.5">
              <Shield className="w-3.5 h-3.5 animate-pulse" />
              IBM Bob Adaptive Coach
            </span>
            <h1 className="font-display text-3xl font-bold tracking-tight text-text mt-1">
              Engineering Scenario Coach
            </h1>
            <p className="text-xs text-text-muted mt-2 max-w-xl">
              Practice real engineering decisions, defend your choices under pressure, and learn to reason like a software architect.
            </p>
          </div>
          
          {activeSession && (
            <button
              onClick={() => setActiveSession(null)}
              className="px-4 py-2 border border-border bg-card-bg/60 hover:bg-border/20 text-xs font-semibold text-text rounded-xl transition-all cursor-pointer"
            >
              Back to Dashboard
            </button>
          )}
        </div>

        {error && (
          <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-500 text-xs font-semibold mb-6 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* ── HOME SCREEN (NO ACTIVE SESSION) ────────────────────────────── */}
        {!activeSession ? (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            
            {/* Launch Module */}
            <div className="lg:col-span-2 flex flex-col gap-6">
              <div className="p-8 rounded-2xl border border-border bg-card-bg/60 glass-panel relative overflow-hidden">
                <div className="absolute top-0 right-0 p-6 opacity-5 pointer-events-none">
                  <Shield className="w-44 h-44" />
                </div>
                
                <h2 className="font-display text-xl font-bold text-text mb-2">Start a New Engineering Dialogue</h2>
                <p className="text-xs text-text-muted leading-relaxed mb-6">
                  IBM Bob will read your mock interview performance, weaknesses, and profile target role. It will generate a system-wide engineering challenge custom-built for your profile.
                </p>

                <div className="mb-6 text-left">
                  <label className="text-[10px] font-bold tracking-wider uppercase text-text-muted block mb-2.5">
                    Select Coding Language
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {["Python", "JavaScript", "Java", "C++", "Go"].map((lang) => (
                      <button
                        key={lang}
                        type="button"
                        onClick={() => setSelectedLanguage(lang)}
                        className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold border transition-all cursor-pointer ${
                          selectedLanguage === lang
                            ? 'bg-rust border-rust text-white shadow-sm shadow-rust/10'
                            : 'border-border/60 bg-bg/40 text-text-muted hover:text-text hover:border-rust/40'
                        }`}
                      >
                        {lang}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="flex flex-col sm:flex-row items-center gap-4">
                  <button
                    onClick={() => handleStart()}
                    disabled={starting}
                    className="w-full sm:w-auto px-6 py-3 rounded-xl bg-rust hover:bg-rust/90 text-white font-semibold text-xs transition-all shadow-md shadow-rust/10 flex items-center justify-center gap-2 cursor-pointer"
                  >
                    {starting ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        <span>Initializing Coach...</span>
                      </>
                    ) : (
                      <>
                        <Play className="w-3.5 h-3.5 fill-current" />
                        <span>Launch Scenario Session</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Informational Guidelines card */}
              <div className="p-6 rounded-2xl border border-border bg-card-bg/60 glass-panel">
                <span className="text-[10px] font-bold tracking-wider uppercase text-text-muted">How Bob Evaluates You</span>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-4">
                  {[
                    { title: "Devil's Advocate", desc: "Bob will challenge your choices and ask WHY you selected specific patterns." },
                    { title: "Dynamic Scaling", desc: "Strong technical justification increases difficulty and adds constraints." },
                    { title: "Syllabus Linked", desc: "Completed results update mastery levels and adapt roadmap priorities." }
                  ].map((x, idx) => (
                    <div key={idx} className="p-4 rounded-xl bg-bg/50 border border-border/40 text-left">
                      <span className="text-xs font-bold text-rust block mb-1.5">{x.title}</span>
                      <p className="text-[11px] text-text-muted leading-relaxed">{x.desc}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* History Sidebar */}
            <div className="flex flex-col gap-6">
              <div className="p-6 rounded-2xl border border-border bg-card-bg/60 glass-panel flex flex-col gap-4">
                <div>
                  <h3 className="font-display text-sm font-bold text-text">Past Dialectics</h3>
                  <span className="text-[10px] text-text-muted">Previous evaluations and scores</span>
                </div>

                {history.length === 0 ? (
                  <p className="text-xs text-text-muted italic py-4">No completed scenario sessions yet.</p>
                ) : (
                  <div className="flex flex-col gap-2.5 max-h-72 overflow-y-auto pr-1">
                    {history.map((s) => (
                      <div 
                        key={s.id}
                        onClick={() => handleSelectSession(s.id)}
                        className="p-3 rounded-xl border border-border/60 hover:border-rust/40 bg-bg/40 hover:bg-rust/5 transition-all cursor-pointer flex items-center justify-between gap-3 text-left"
                      >
                        <div className="min-w-0">
                          <span className="text-[10px] font-bold text-text-muted uppercase block">{s.topic}</span>
                          <span className="text-xs font-bold text-text block truncate mt-0.5">{s.target_role}</span>
                          <span className="text-[9px] text-text-muted block mt-0.5">
                            {new Date(s.created_at).toLocaleDateString()} · Diff: {s.difficulty}
                          </span>
                        </div>
                        <div className="flex items-center gap-1 shrink-0">
                          <span className="font-display text-base font-bold text-rust">
                            {s.overall_score != null ? `${s.overall_score}%` : 'TBD'}
                          </span>
                          <ChevronRight className="w-3.5 h-3.5 text-text-muted opacity-50" />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

          </div>
        ) : (
          /* ── ACTIVE SESSION SCREEN ────────────────────────────────────── */
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            
            {/* Conversation Flow Area */}
            <div className="lg:col-span-2 flex flex-col gap-6">
              
              <div className="p-6 rounded-2xl border border-border bg-card-bg/60 glass-panel flex flex-col h-[520px]">
                {/* Chat Header */}
                <div className="flex items-center justify-between border-b border-border/40 pb-4 mb-4 shrink-0">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-xl bg-rust/10 flex items-center justify-center text-rust">
                      <Shield className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="font-display text-sm font-bold text-text">{activeSession.topic}</h3>
                      <span className="text-[10px] text-text-muted block mt-0.5">
                        Difficulty: <span className="text-rust font-bold uppercase">{activeSession.difficulty}</span>
                      </span>
                    </div>
                  </div>
                  
                  {/* Progress gauge */}
                  <div className="text-right">
                    <span className="text-[10px] uppercase font-bold text-text-muted tracking-wider block">Dialogue Progress</span>
                    <span className="text-xs font-bold text-text mt-0.5 block">
                      Turn {candidateTurns} of {MAX_CANDIDATE_TURNS}
                    </span>
                  </div>
                </div>

                {/* Dialog Messages list */}
                <div className="flex-1 overflow-y-auto flex flex-col gap-4 pr-2 [scrollbar-width:thin]">
                  {(activeSession.conversation || []).map((msg, idx) => {
                    const isBob = msg.sender === 'bob'
                    return (
                      <div 
                        key={idx} 
                        className={`flex gap-3 max-w-[85%] ${isBob ? 'self-start text-left' : 'self-end flex-row-reverse text-right'}`}
                      >
                        {isBob && (
                          <div className="w-7 h-7 rounded-lg bg-rust/10 border border-rust/15 flex items-center justify-center text-rust shrink-0 self-start mt-0.5">
                            <Shield className="w-3.5 h-3.5" />
                          </div>
                        )}
                        <div className={`p-4 rounded-2xl text-xs leading-relaxed font-medium ${
                          isBob 
                            ? 'bg-panel-bg/40 border border-border text-text rounded-tl-none' 
                            : 'bg-rust text-white rounded-tr-none shadow-md shadow-rust/10'
                        }`}>
                          {msg.text}
                        </div>
                      </div>
                    )
                  })}
                  {submitting && (
                    <div className="flex gap-3 max-w-[85%] self-start text-left">
                      <div className="w-7 h-7 rounded-lg bg-rust/10 border border-rust/15 flex items-center justify-center text-rust shrink-0 mt-0.5 animate-pulse">
                        <Shield className="w-3.5 h-3.5" />
                      </div>
                      <div className="p-4 rounded-2xl text-xs bg-panel-bg/40 border border-border text-text-muted rounded-tl-none flex items-center gap-2">
                        <RefreshCw className="w-3.5 h-3.5 animate-spin text-rust" />
                        <span>Bob is analyzing your reasoning...</span>
                      </div>
                    </div>
                  )}
                  <div ref={chatEndRef} />
                </div>

                {/* Chat Input form */}
                {!activeSession.completed && (
                  <div className="mt-4 pt-4 border-t border-border/40 shrink-0">
                    <form 
                      onSubmit={(e) => { e.preventDefault(); handleRespond(); }}
                      className="flex gap-3"
                    >
                      <textarea
                        value={responseText}
                        onChange={(e) => setResponseText(e.target.value)}
                        placeholder="Explain your technical decisions and trade-offs..."
                        disabled={submitting}
                        rows={2}
                        className="flex-1 px-4 py-3 rounded-xl border border-border bg-bg/50 text-xs font-semibold text-text placeholder-text-muted focus:outline-none focus:border-rust/80 transition-colors resize-none"
                      />
                      <button
                        type="submit"
                        disabled={!responseText.trim() || submitting}
                        className="px-5 rounded-xl bg-rust hover:bg-rust/90 disabled:bg-border/60 text-white flex items-center justify-center transition-all cursor-pointer shrink-0 shadow-md shadow-rust/10"
                      >
                        <Send className="w-4 h-4" />
                      </button>
                    </form>
                  </div>
                )}
              </div>

            </div>

            {/* Evaluation Details Sidebar / Summary */}
            <div className="flex flex-col gap-6">
              {activeSession.completed && activeSession.evaluation ? (
                /* ── COMPLETED EVALUATION DETAILS PANELS ─────────────────── */
                <div className="flex flex-col gap-6">
                  
                  {/* Gauge Card */}
                  <div className="p-6 rounded-2xl border border-border bg-card-bg/60 glass-panel flex flex-col items-center gap-4 text-center">
                    <span className="text-[10px] font-bold tracking-wider uppercase text-text-muted">Scenario Score</span>
                    
                    {/* Ring gauge */}
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
                          strokeDashoffset={289 - (289 * (activeSession.overall_score ?? 70)) / 100}
                          strokeLinecap="round"
                        />
                      </svg>
                      <div className="absolute text-center">
                        <span className="font-display text-2xl font-bold text-rust">{activeSession.overall_score}%</span>
                        <span className="block text-[8px] uppercase tracking-wider font-semibold text-text-muted mt-0.5">Rating</span>
                      </div>
                    </div>

                    <h4 className="font-display text-base font-bold text-text mt-1">Evaluation Completed</h4>
                    <p className="text-[11px] text-text-muted leading-relaxed">
                      Bob has updated your topic mastery. Practice recommendations have been synced.
                    </p>
                  </div>

                  {/* Attributes Score list */}
                  <div className="p-6 rounded-2xl border border-border bg-card-bg/60 glass-panel flex flex-col gap-4">
                    <span className="text-[10px] font-bold tracking-wider uppercase text-text-muted">Skill Metrics</span>
                    <div className="flex flex-col gap-3">
                      {activeSession.evaluation?.evaluation && Object.entries(activeSession.evaluation.evaluation).map(([attr, score]) => {
                        if (attr === 'overall') return null
                        return (
                          <div key={attr} className="text-left">
                            <div className="flex justify-between text-[10px] font-semibold text-text-muted uppercase mb-1">
                              <span>{attr.replace('_', ' ')}</span>
                              <span className="text-rust font-bold">{score}%</span>
                            </div>
                            <div className="w-full h-1.5 rounded-full bg-border/40 overflow-hidden">
                              <div className="h-full bg-rust rounded-full" style={{ width: `${score}%` }} />
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>

                  {/* Strengths & Weaknesses */}
                  <div className="p-6 rounded-2xl border border-border bg-card-bg/60 glass-panel flex flex-col gap-4 text-left">
                    <div>
                      <span className="text-[10px] font-bold tracking-wider uppercase text-text-muted block">Strengths</span>
                      <ul className="list-disc list-inside text-xs text-text-muted mt-2 flex flex-col gap-1">
                        {(activeSession.evaluation?.strengths || []).map((s, idx) => (
                          <li key={idx}>{s}</li>
                        ))}
                      </ul>
                    </div>

                    <div className="border-t border-border/40 pt-4">
                      <span className="text-[10px] font-bold tracking-wider uppercase text-text-muted block">Weaknesses</span>
                      <ul className="list-disc list-inside text-xs text-text-muted mt-2 flex flex-col gap-1">
                        {(activeSession.evaluation?.weaknesses || []).map((w, idx) => (
                          <li key={idx}>{w}</li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  {/* Recommendations */}
                  <div className="p-6 rounded-2xl border border-border bg-card-bg/60 glass-panel flex flex-col gap-4 text-left">
                    {activeSession.evaluation?.better_approach && (
                      <div>
                        <span className="text-[10px] font-bold tracking-wider uppercase text-text-muted block">Better Approach</span>
                        <p className="text-xs text-text mt-1.5 leading-relaxed font-semibold">
                          {activeSession.evaluation.better_approach}
                        </p>
                      </div>
                    )}

                    <div className="border-t border-border/40 pt-4">
                      <span className="text-[10px] font-bold tracking-wider uppercase text-text-muted block">Concepts to Revise</span>
                      <div className="flex flex-wrap gap-1.5 mt-2">
                        {(activeSession.evaluation?.concepts_to_revise || []).map((c, idx) => (
                          <span 
                            key={idx}
                            onClick={() => {
                              localStorage.setItem('active_notes_concept', c)
                              navigate('notes')
                            }}
                            className="text-[9px] font-bold px-2 py-1 rounded-lg bg-rust/10 border border-rust/15 text-rust cursor-pointer hover:bg-rust/20 transition-all uppercase tracking-wide"
                          >
                            {c}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>

                </div>
              ) : (
                /* ── DOCK PANEL WHILE ACTIVE SCENARIO IN DIALOGUE ────────── */
                <div className="p-6 rounded-2xl border border-border bg-card-bg/60 glass-panel flex flex-col gap-4 text-left">
                  <span className="text-[10px] font-bold tracking-wider uppercase text-text-muted">Scenario Guide</span>
                  <div className="flex flex-col gap-3">
                    <div className="p-3 bg-bg/50 border border-border/40 rounded-xl">
                      <span className="text-[9px] uppercase font-bold text-rust">Target Role</span>
                      <p className="text-xs font-bold text-text mt-0.5">{activeSession.target_role}</p>
                    </div>
                    <div className="p-3 bg-bg/50 border border-border/40 rounded-xl">
                      <span className="text-[9px] uppercase font-bold text-rust">Scrutiny Focus</span>
                      <p className="text-xs font-bold text-text mt-0.5">Devil's Advocate reasoning check</p>
                    </div>
                  </div>
                  <p className="text-[11px] text-text-muted leading-relaxed pt-2 border-t border-border/40">
                    💡 **Tip**: Don't just say *what* database or service you will use. Explain **why** it fits the specific scaling or budget limits!
                  </p>
                </div>
              )}
            </div>

          </div>
        )}

      </div>
    </div>
  )
}
