import { useEffect, useState, useCallback } from 'react'
import { Nav } from '../components/Nav'
import { useAuth } from '../lib/AuthContext'
import * as api from '../lib/apiClient'
import { motion } from 'framer-motion'
import { Lock, Unlock, Play, Clock, RefreshCw, Award, BookOpen } from 'lucide-react'

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
  const completionPercentage = Math.min(100, Math.round(((maxUnlockedWeek - 1) / Math.max(steps.length, 1)) * 100))

  return (
    <div className="min-h-screen bg-bg text-text transition-colors duration-300 font-sans pb-16">
      <Nav page="roadmap" navigate={navigate} />

      <div className="max-w-3xl mx-auto px-6 pt-10">
        
        {/* Header Block */}
        <div className="mb-10">
          <span className="text-[10px] uppercase font-bold tracking-wider text-rust">Study Plan</span>
          <h1 className="font-display text-3xl md:text-4xl font-bold tracking-tight text-text mt-1">
            {roadmap ? roadmap.title : 'Your Preparation Roadmap'}
          </h1>
          <p className="text-xs text-text-muted mt-2">
            Dynamic timeline generated for your targeted experience level and company loops.
          </p>
        </div>

        {error && (
          <div className="p-4 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-500 text-xs font-semibold mb-6">
            {error}
          </div>
        )}

        {loading ? (
          <div className="py-20 text-center">
            <RefreshCw className="w-8 h-8 text-rust/80 animate-spin mx-auto mb-3" />
            <span className="text-xs font-bold text-text-muted">Calculating roadmap steps...</span>
          </div>
        ) : !roadmap ? (
          /* Generate Callout */
          <div className="p-8 rounded-2xl border border-border bg-card-bg/60 glass-panel text-center">
            <BookOpen className="w-10 h-10 text-rust/80 mx-auto mb-4" />
            <h3 className="font-display text-lg font-bold text-text">No active timeline</h3>
            <p className="text-xs text-text-muted mt-2 max-w-sm mx-auto leading-relaxed">
              Generate a personalized study roadmap corresponding to your targeted company questions and profile strengths.
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
                          <span className={`text-[9px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full ${
                            isLocked 
                              ? 'bg-border/60 text-text-muted' 
                              : 'bg-rust/10 text-rust'
                          }`}>
                            Week {step.step_number}
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
                            <button
                              onClick={() => {
                                localStorage.setItem('active_roadmap_week', step.step_number.toString())
                                localStorage.setItem('active_roadmap_topic', step.title)
                                navigate('interview')
                              }}
                              className="px-4 py-1.5 bg-rust hover:bg-rust/90 text-white rounded-lg text-xs font-bold transition-all shadow-sm shadow-rust/10 cursor-pointer flex items-center gap-1"
                            >
                              <Play className="w-3 h-3 fill-current" />
                              <span>Practice</span>
                            </button>
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
                        <div className="mt-5 pt-4 border-t border-border/40 flex flex-col gap-4">
                          {/* Syllabus Section */}
                          <div>
                            <span className="text-[10px] uppercase font-bold text-rust tracking-wider mb-2 block">
                              📖 Course Syllabus
                            </span>
                            <ul className="flex flex-col gap-1.5 list-none p-0 m-0 pl-1">
                              {((step as any).syllabus && (step as any).syllabus.length > 0
                                ? (step as any).syllabus
                                : step.description.split(',').map((s: string) => s.trim())
                              ).map((sub: string, idx: number) => (
                                <li key={idx} className="flex gap-2 items-start text-xs text-text-muted">
                                  <span className="text-rust/60 font-semibold">{idx + 1}.</span>
                                  <span>{sub.charAt(0).toUpperCase() + sub.slice(1)}</span>
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
                              {(step as any).notes || `Focus on mastering key concepts of ${step.title}. Understand the theoretical trade-offs, standard architectures, and implementation complexities for interviews.`}
                            </p>
                          </div>

                          {/* FAQs Section */}
                          {((step as any).questions && (step as any).questions.length > 0) && (
                            <div>
                              <span className="text-[10px] uppercase font-bold text-rust tracking-wider mb-2 block">
                                🎯 Frequently Asked Qs
                              </span>
                              <ul className="flex flex-col gap-2 list-none p-0 m-0 pl-1">
                                {(step as any).questions.map((q: string, idx: number) => (
                                  <li key={idx} className="flex gap-2 items-start text-xs text-text-muted">
                                    <span className="text-rust font-bold">&#9679;</span>
                                    <span>{q}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
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
                <span>{generating ? 'Regenerating roadmap...' : 'Regenerate Roadmap'}</span>
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
