import { useEffect, useState, useCallback } from 'react'
import { Nav } from '../components/Nav'
import { useAuth } from '../lib/AuthContext'
import * as api from '../lib/apiClient'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Lock,
  Unlock,
  Play,
  Clock,
  RefreshCw,
  Award,
  BookOpen,
  HelpCircle,
  Send,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'

type Page = 'landing' | 'login' | 'register' | 'onboarding' | 'workspace' | 'roadmap' | 'interview' | 'notes' | 'mastery' | 'mentor'
interface Props { navigate: (p: Page) => void }

export default function Roadmap({ navigate }: Props) {
  const { user } = useAuth()
  const [roadmap, setRoadmap] = useState<api.RoadmapResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [maxUnlockedWeek, setMaxUnlockedWeek] = useState<number>(1)

  // Interactive Practice Questions State
  const [activeQuestionKey, setActiveQuestionKey] = useState<string | null>(null)
  const [userAnswers, setUserAnswers] = useState<Record<string, string>>({})
  const [evaluatingKey, setEvaluatingKey] = useState<string | null>(null)
  const [evalResults, setEvalResults] = useState<Record<string, api.PracticeQuestionEvalResponse>>({})
  const [adaptiveNotice, setAdaptiveNotice] = useState<{ stepNumber: number; newQuestion: string } | null>(null)

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
    const targetRole = user?.profile?.target_role || 'Software Engineer'
    setGenerating(true)
    setError(null)
    setAdaptiveNotice(null)
    setUserAnswers({})
    setEvalResults({})
    setActiveQuestionKey(null)
    try {
      const created = await api.generateRoadmap(targetRole)
      setRoadmap(created)
      setMaxUnlockedWeek(1)
      localStorage.setItem('roadmap_max_unlocked', '1')
    } catch (err) {
      setError(err instanceof api.ApiError ? err.message : 'Could not generate a roadmap right now. Please try again.')
    } finally {
      setGenerating(false)
    }
  }

  const handleEvaluatePractice = async (stepNumber: number, qIdx: number, questionText: string) => {
    if (!roadmap) return
    const key = `step${stepNumber}-q${qIdx}`
    const answer = userAnswers[key]?.trim()
    if (!answer) return

    setEvaluatingKey(key)
    setError(null)
    try {
      const res = await api.evaluatePracticeQuestion(roadmap.id, stepNumber, questionText, answer)
      setEvalResults(prev => ({ ...prev, [key]: res }))

      if (res.generated_new_question) {
        setAdaptiveNotice({
          stepNumber,
          newQuestion: res.generated_new_question
        })
        // Update roadmap state locally so newly generated remediation question is immediately visible in list
        setRoadmap(prev => {
          if (!prev) return null
          const updatedSteps = prev.steps_json.map(s => {
            if (s.step_number === stepNumber) {
              return {
                ...s,
                questions: res.step_questions
              }
            }
            return s
          })
          return { ...prev, steps_json: updatedSteps }
        })
      }
    } catch (err) {
      setError(err instanceof api.ApiError ? err.message : 'Could not evaluate practice answer. Please try again.')
    } finally {
      setEvaluatingKey(null)
    }
  }

  const steps = (roadmap?.steps_json ?? []) as api.RoadmapStep[]
  const completionPercentage = Math.min(100, Math.round(((maxUnlockedWeek - 1) / Math.max(steps.length, 1)) * 100))

  return (
    <div className="min-h-screen bg-bg text-text transition-colors duration-300 font-sans pb-16">
      <Nav page="roadmap" navigate={navigate} />

      <div className="max-w-3xl mx-auto px-6 pt-10">
        
        {/* Header Block */}
        <div className="mb-10">
          <span className="text-[10px] uppercase font-bold tracking-wider text-rust">Study Plan & Adaptive Syllabus</span>
          <h1 className="font-display text-3xl md:text-4xl font-bold tracking-tight text-text mt-1">
            {roadmap ? roadmap.title : 'Your Preparation Roadmap'}
          </h1>
          <p className="text-xs text-text-muted mt-2">
            Dynamic weekly syllabus with at least 5 practice questions per topic. Scoring under 50% automatically triggers adaptive concept questions to build depth.
          </p>
        </div>

        {error && (
          <div className="p-4 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-500 text-xs font-semibold mb-6 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {adaptiveNotice && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-amber-600 dark:text-amber-400 text-xs mb-6 flex items-start gap-3 shadow-sm"
          >
            <Sparkles className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold block text-sm">⚡ Adaptive Question Generated! (Week {adaptiveNotice.stepNumber})</span>
              <p className="mt-1 text-xs opacity-90">
                Because your answer scored below 50%, a new concept question was automatically generated to boost your understandability of Week {adaptiveNotice.stepNumber} concepts:
              </p>
              <div className="mt-2 font-medium italic bg-bg/50 p-2.5 rounded-xl border border-amber-500/20 text-text">
                "{adaptiveNotice.newQuestion}"
              </div>
            </div>
          </motion.div>
        )}

        {loading ? (
          <div className="py-20 text-center">
            <RefreshCw className="w-8 h-8 text-rust/80 animate-spin mx-auto mb-3" />
            <span className="text-xs font-bold text-text-muted">Calculating roadmap & syllabus questions...</span>
          </div>
        ) : !roadmap ? (
          /* Generate Callout */
          <div className="p-8 rounded-2xl border border-border bg-card-bg/60 glass-panel text-center">
            <BookOpen className="w-10 h-10 text-rust/80 mx-auto mb-4" />
            <h3 className="font-display text-lg font-bold text-text">No active timeline</h3>
            <p className="text-xs text-text-muted mt-2 max-w-sm mx-auto leading-relaxed">
              Generate a personalized study roadmap corresponding to your targeted role with syllabus-based practice questions.
            </p>
            <button
              onClick={handleGenerate}
              disabled={generating}
              className={`mt-6 px-6 py-3 rounded-xl text-white text-xs font-semibold transition-all cursor-pointer ${
                generating ? 'bg-rust/60 cursor-not-allowed' : 'bg-rust hover:bg-rust/90'
              }`}
            >
              {generating ? 'Generating milestones...' : 'Generate Roadmap'}
            </button>
          </div>
        ) : (
          <>
            {/* Timeline Progress Bar */}
            <div className="p-5 rounded-2xl border border-border bg-card-bg/60 glass-panel flex items-center justify-between gap-6 mb-10">
              <div className="flex-1">
                <div className="flex justify-between text-xs font-bold text-text mb-2">
                  <span>Overall Progression</span>
                  <span className="text-rust">{completionPercentage}% Completed</span>
                </div>
                <div className="w-full h-2 rounded-full bg-border/40 overflow-hidden">
                  <div 
                    className="h-full bg-rust transition-all duration-500" 
                    style={{ width: `${completionPercentage}%` }} 
                  />
                </div>
              </div>
              <div className="p-3 bg-rust/10 text-rust rounded-xl hidden sm:block">
                <Award className="w-6 h-6" />
              </div>
            </div>

            {/* Vertical Milestones Timeline */}
            <div className="relative border-l border-border/80 ml-4 pl-8 flex flex-col gap-8">
              {steps.map((step, index) => {
                const isLocked = step.step_number > maxUnlockedWeek
                const isCurrent = step.step_number === maxUnlockedWeek

                // Guarantee syllabus and at least 5 practice questions
                const syllabusItems = (step.syllabus && step.syllabus.length > 0)
                  ? step.syllabus
                  : step.description.split(',').map(s => s.trim())

                const questionsList = (step.questions && step.questions.length >= 5)
                  ? step.questions
                  : [
                      ...(step.questions || []),
                      `What are the foundational principles of ${step.title}?`,
                      `How do you design and architect ${step.title} for production?`,
                      `Explain key trade-offs and common pitfalls when working with ${step.title}.`,
                      `How do you measure and optimize performance in ${step.title}?`,
                      `Describe how to troubleshoot failure scenarios in ${step.title}.`
                    ].slice(0, Math.max(5, (step.questions || []).length))

                return (
                  <motion.div
                    key={step.step_number}
                    initial={{ opacity: 0, y: 15 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4, delay: index * 0.05 }}
                    className="relative"
                  >
                    {/* Circle Node Indicator */}
                    <div className={`absolute -left-[41px] top-1.5 w-6 h-6 rounded-full flex items-center justify-center border transition-all ${
                      isLocked
                        ? 'bg-bg border-border/80 text-text-muted/50'
                        : isCurrent
                          ? 'bg-rust border-rust text-white shadow shadow-rust/35 scale-110'
                          : 'bg-rust/10 border-rust text-rust'
                    }`}>
                      {isLocked ? (
                        <Lock className="w-3 h-3" />
                      ) : (
                        <Unlock className="w-3 h-3" />
                      )}
                    </div>

                    {/* Milestone Card */}
                    <div className={`p-6 rounded-2xl border bg-card-bg/75 glass-panel transition-all duration-200 ${
                      isLocked 
                        ? 'opacity-65' 
                        : 'hover:shadow-md'
                    }`}>
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
                        <div>
                          <span className={`text-[9px] uppercase font-bold tracking-wider px-2.5 py-0.5 rounded-full ${
                            isLocked 
                              ? 'bg-border/60 text-text-muted' 
                              : step.title.startsWith("Remedial Practice:")
                                ? 'bg-rust/20 text-rust border border-rust/30 animate-pulse'
                                : 'bg-rust/10 text-rust'
                          }`}>
                            {step.title.startsWith("Remedial Practice:") ? 'AI Remedial Lab' : `Week ${step.step_number}`}
                          </span>
                          <h3 className="font-display text-base font-bold text-text mt-1.5">{step.title}</h3>
                        </div>

                        {/* Action buttons */}
                        <div className="flex items-center gap-4 self-start sm:self-center">
                          <div className="flex items-center gap-1.5 text-xs text-text-muted font-medium">
                            <Clock className="w-3.5 h-3.5 opacity-60" />
                            <span>{step.estimated_hours}h</span>
                          </div>
                          {!isLocked && (
                            step.title.startsWith("Remedial Practice:") ? (
                              <button
                                onClick={() => {
                                  navigate('bob_coach');
                                }}
                                className="px-4 py-1.5 bg-rust hover:bg-rust/90 text-white rounded-lg text-xs font-bold transition-all shadow-sm shadow-rust/10 cursor-pointer flex items-center gap-1.5"
                              >
                                <Play className="w-3 h-3 fill-current" />
                                <span>Launch Bob Lab</span>
                              </button>
                            ) : (
                              <button
                                onClick={() => {
                                  localStorage.setItem('active_roadmap_week', step.step_number.toString())
                                  localStorage.setItem('active_roadmap_topic', step.title)
                                  // Store this week's syllabus so the interview agent can ground questions in these subtopics
                                  localStorage.setItem('active_roadmap_syllabus', JSON.stringify(syllabusItems))
                                  navigate('interview')
                                }}
                                className="px-4 py-1.5 bg-rust hover:bg-rust/90 text-white rounded-lg text-xs font-bold transition-all shadow-sm shadow-rust/10 cursor-pointer flex items-center gap-1"
                              >
                                <Play className="w-3 h-3 fill-current" />
                                <span>Live Interview</span>
                              </button>
                            )
                          )}
                        </div>
                      </div>

                      <p className="text-xs text-text-muted leading-relaxed">
                        {isLocked 
                          ? `Complete Week ${step.step_number - 1} simulation and achieve an overall score of 50+ to unlock this topic.` 
                          : step.description
                        }
                      </p>

                      {!isLocked && (
                        <div className="mt-5 pt-4 border-t border-border/40 flex flex-col gap-5">
                          {/* Syllabus Section */}
                          <div>
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-[10px] uppercase font-bold text-rust tracking-wider block">
                                📖 Weekly Syllabus Topics
                              </span>
                              <span className="text-[10px] font-bold text-text-muted bg-border/40 px-2 py-0.5 rounded-full">
                                {syllabusItems.length} Concepts
                              </span>
                            </div>
                            <ul className="grid grid-cols-1 md:grid-cols-2 gap-2 list-none p-0 m-0">
                              {syllabusItems.map((sub: string, idx: number) => (
                                <li key={idx} className="flex gap-2 items-start text-xs text-text-muted bg-bg/50 p-2 rounded-xl border border-border/40">
                                  <span className="text-rust font-bold">{idx + 1}.</span>
                                  <span className="font-medium text-text">{sub.charAt(0).toUpperCase() + sub.slice(1)}</span>
                                </li>
                              ))}
                            </ul>
                          </div>

                          {/* Study Notes Section */}
                          <div>
                            <span className="text-[10px] uppercase font-bold text-rust tracking-wider mb-1.5 block">
                              📝 Cheat-Sheet Notes
                            </span>
                            <p className="text-xs text-text-muted leading-relaxed italic bg-bg/40 p-3 rounded-xl border border-border/50">
                              {step.notes || `Focus on mastering key concepts of ${step.title}. Understand the theoretical trade-offs, standard architectures, and implementation complexities for interviews.`}
                            </p>
                          </div>

                          {/* Syllabus-Grounded Practice Questions Section (Min 5 Questions) */}
                          <div>
                            <div className="flex items-center justify-between mb-3">
                              <span className="text-[10px] uppercase font-bold text-rust tracking-wider flex items-center gap-1.5">
                                <HelpCircle className="w-3.5 h-3.5" />
                                <span>🎯 Practice Questions</span>
                              </span>
                              <span className="text-[10px] font-bold text-white bg-rust px-2.5 py-0.5 rounded-full">
                                {questionsList.length} Practice Questions (Min 5)
                              </span>
                            </div>

                            <div className="flex flex-col gap-3">
                              {questionsList.map((q: string, qIdx: number) => {
                                const qKey = `step${step.step_number}-q${qIdx}`
                                const isOpen = activeQuestionKey === qKey
                                const evalRes = evalResults[qKey]
                                const isEvaluating = evaluatingKey === qKey
                                const isRemediation = qIdx >= 5 || q.toLowerCase().includes('adaptive') || q.toLowerCase().includes('foundational') || q.toLowerCase().includes('refresher')

                                return (
                                  <div
                                    key={qIdx}
                                    className={`p-3.5 rounded-xl border transition-all ${
                                      isRemediation
                                        ? 'bg-amber-500/5 border-amber-500/30'
                                        : 'bg-card-bg/90 border-border/60'
                                    }`}
                                  >
                                    <div className="flex items-start justify-between gap-3">
                                      <div className="flex gap-2 items-start text-xs text-text flex-1">
                                        <span className={`font-bold shrink-0 px-2 py-0.5 rounded-md text-[10px] ${
                                          isRemediation ? 'bg-amber-500/20 text-amber-500' : 'bg-rust/10 text-rust'
                                        }`}>
                                          {isRemediation ? '⚡ Adaptive Concept Q' : `Q${qIdx + 1}`}
                                        </span>
                                        <span className="font-semibold leading-snug">{q}</span>
                                      </div>

                                      <button
                                        onClick={() => setActiveQuestionKey(isOpen ? null : qKey)}
                                        className="text-xs font-bold text-rust hover:text-rust/80 flex items-center gap-1 cursor-pointer shrink-0"
                                      >
                                        <span>{isOpen ? 'Close' : 'Answer'}</span>
                                        {isOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                                      </button>
                                    </div>

                                    {/* Score display badge if evaluated */}
                                    {evalRes && (
                                      <div className="mt-2.5 flex items-center gap-2">
                                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full flex items-center gap-1 ${
                                          evalRes.passed
                                            ? 'bg-green-500/15 text-green-500 border border-green-500/30'
                                            : 'bg-red-500/15 text-red-500 border border-red-500/30'
                                        }`}>
                                          {evalRes.passed ? <CheckCircle2 className="w-3 h-3" /> : <AlertCircle className="w-3 h-3" />}
                                          <span>Score: {evalRes.score}% {evalRes.passed ? '(Passed)' : '(Score < 50%)'}</span>
                                        </span>
                                      </div>
                                    )}

                                    {/* Expandable Answer Form */}
                                    <AnimatePresence>
                                      {isOpen && (
                                        <motion.div
                                          initial={{ height: 0, opacity: 0 }}
                                          animate={{ height: 'auto', opacity: 1 }}
                                          exit={{ height: 0, opacity: 0 }}
                                          className="mt-3 pt-3 border-t border-border/40 flex flex-col gap-3"
                                        >
                                          <textarea
                                            rows={3}
                                            value={userAnswers[qKey] || ''}
                                            onChange={(e) => setUserAnswers(prev => ({ ...prev, [qKey]: e.target.value }))}
                                            placeholder="Write your explanation or answer to this practice question..."
                                            className="w-full p-3 rounded-xl border border-border/60 bg-bg text-xs text-text focus:outline-none focus:border-rust"
                                          />

                                          <div className="flex items-center justify-between">
                                            <span className="text-[10px] text-text-muted italic">
                                              Scores below 50% automatically generate a new concept question for Week {step.step_number}.
                                            </span>

                                            <button
                                              onClick={() => handleEvaluatePractice(step.step_number, qIdx, q)}
                                              disabled={isEvaluating || !userAnswers[qKey]?.trim()}
                                              className={`px-4 py-1.5 bg-rust hover:bg-rust/90 text-white rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer ${
                                                isEvaluating || !userAnswers[qKey]?.trim() ? 'opacity-50 cursor-not-allowed' : ''
                                              }`}
                                            >
                                              {isEvaluating ? (
                                                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                                              ) : (
                                                <Send className="w-3.5 h-3.5" />
                                              )}
                                              <span>{isEvaluating ? 'Evaluating...' : 'Submit Answer'}</span>
                                            </button>
                                          </div>

                                          {/* Feedback Result Card */}
                                          {evalRes && (
                                            <div className={`p-3.5 rounded-xl border text-xs leading-relaxed ${
                                              evalRes.passed
                                                ? 'bg-green-500/5 border-green-500/20 text-text'
                                                : 'bg-red-500/5 border-red-500/20 text-text'
                                            }`}>
                                              <div className="font-bold mb-1 flex items-center justify-between">
                                                <span>AI Evaluation Feedback:</span>
                                                <span className={evalRes.passed ? 'text-green-500 font-bold' : 'text-red-500 font-bold'}>
                                                  {evalRes.score}%
                                                </span>
                                              </div>
                                              <p className="text-text-muted">{evalRes.feedback}</p>
                                            </div>
                                          )}
                                        </motion.div>
                                      )}
                                    </AnimatePresence>
                                  </div>
                                )
                              })}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  </motion.div>
                )
              })}
            </div>

            {/* Regenerate Button */}
            <div className="mt-12 flex justify-center">
              <button
                onClick={handleGenerate}
                disabled={generating}
                className={`px-5 py-2.5 rounded-xl border border-border bg-card-bg/60 hover:bg-border/20 text-xs font-bold text-text-muted hover:text-text transition-colors flex items-center gap-1.5 cursor-pointer ${
                  generating ? 'opacity-60 cursor-not-allowed' : ''
                }`}
              >
                <RefreshCw className={`w-3.5 h-3.5 ${generating ? 'animate-spin' : ''}`} />
                <span>{generating ? 'Regenerating roadmap...' : 'Regenerate Roadmap & Questions'}</span>
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

