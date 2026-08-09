import { useState, useEffect } from 'react'
import { Nav } from '../components/Nav'
import { useAuth } from '../lib/AuthContext'
import { updateProfile, ApiError } from '../lib/apiClient'
import { motion } from 'framer-motion'
import { Briefcase, Calendar, Star, BookOpen, Eye, Award, Sparkles } from 'lucide-react'

type Page = 'landing' | 'login' | 'register' | 'onboarding' | 'workspace' | 'roadmap' | 'interview' | 'notes' | 'mastery' | 'mentor'
interface Props { navigate: (p: Page) => void }

const LEARNING_STYLES = [
  { value: 'visual', label: 'Visual Style', desc: 'CS diagrams & visual networks', icon: Eye },
  { value: 'reading_writing', label: 'Written Summary', desc: 'Outline summaries & documentation', icon: BookOpen },
  { value: 'kinesthetic', label: 'Hands-on Exercises', desc: 'Secure coding challenges & debugging', icon: Award },
] as const

const EXPERIENCE_LEVELS = ['Entry-level', 'Mid-level', 'Senior', 'Staff / Lead']

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
    <div className="min-h-screen bg-bg text-text transition-colors duration-300 font-sans flex flex-col">
      <Nav page="workspace" navigate={navigate} />

      <div className="flex-1 flex flex-col items-center justify-center px-6 py-12">
        <div className="w-full max-w-[540px]">
          {/* Header */}
          <div className="text-center mb-8">
            <span className="text-[11px] font-bold uppercase tracking-wider text-rust">
              Personalized setup
            </span>
            <h1 className="font-display text-3xl font-bold tracking-tight text-text mt-1.5">
              Let's tailor your experience
            </h1>
            <p className="text-xs text-text-muted mt-2">
              CoachLine configures your roadmap milestones and IBM Bob challenges based on your answers.
            </p>
          </div>

          {/* Setup Card */}
          <form 
            onSubmit={handleSubmit}
            className="p-8 rounded-2xl border border-border bg-card-bg/85 backdrop-blur-md shadow-xl flex flex-col gap-6 glass-panel"
          >
            {/* Target Role & Company Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] font-bold uppercase tracking-wider text-text-muted">
                  Target Role
                </label>
                <div className="relative flex items-center">
                  <Briefcase className="w-4 h-4 text-text-muted/60 absolute left-3.5" />
                  <input
                    type="text"
                    required
                    value={targetRole}
                    onChange={(e) => setTargetRole(e.target.value)}
                    placeholder="e.g. Backend Engineer"
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-border/70 bg-bg/50 text-sm focus:outline-none focus:border-rust/80 focus:ring-3 focus:ring-rust/15 transition-all placeholder:text-text-muted/40"
                  />
                </div>
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] font-bold uppercase tracking-wider text-text-muted">
                  Target Company
                </label>
                <div className="relative flex items-center">
                  <Star className="w-4 h-4 text-text-muted/70 absolute left-3.5 pointer-events-none" />
                  <input
                    type="text"
                    required
                    value={targetCompany}
                    onChange={(e) => setTargetCompany(e.target.value)}
                    placeholder="e.g. Stripe"
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-border/70 bg-bg/50 text-sm focus:outline-none focus:border-rust/80 focus:ring-3 focus:ring-rust/15 transition-all placeholder:text-text-muted/40"
                  />
                </div>
              </div>
            </div>

            {/* Experience Level */}
            <div className="flex flex-col gap-2">
              <label className="text-[10px] font-bold uppercase tracking-wider text-text-muted">
                Experience Level
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {EXPERIENCE_LEVELS.map((level) => {
                  const isSelected = experienceLevel === level
                  return (
                    <button
                      key={level}
                      type="button"
                      onClick={() => setExperienceLevel(level)}
                      className={`py-2 px-3 rounded-xl border text-xs font-semibold tracking-wide transition-all duration-200 cursor-pointer ${
                        isSelected 
                          ? 'border-rust bg-rust/10 text-rust shadow-xs shadow-rust/10 font-bold' 
                          : 'border-border/60 bg-bg/40 text-text-muted hover:border-border hover:text-text hover:bg-bg/70'
                      }`}
                    >
                      {level}
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Interview Target Date */}
            <div className="flex flex-col gap-1.5">
              <label className="text-[10px] font-bold uppercase tracking-wider text-text-muted">
                Target Interview Date
              </label>
              <div className="relative flex items-center">
                <Calendar className="w-4 h-4 text-text-muted/70 absolute left-3.5 pointer-events-none" />
                <input
                  type="date"
                  required
                  min={new Date().toISOString().split('T')[0]}
                  value={interviewDate}
                  onChange={(e) => setInterviewDate(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-border/70 bg-bg/50 text-sm focus:outline-none focus:border-rust/80 focus:ring-3 focus:ring-rust/15 transition-all"
                />
              </div>
            </div>

            {/* Learning Style */}
            <div className="flex flex-col gap-2">
              <label className="text-[10px] font-bold uppercase tracking-wider text-text-muted">
                Preferred Study Format
              </label>
              <div className="flex flex-col gap-2">
                {LEARNING_STYLES.map((style) => {
                  const StyleIcon = style.icon
                  const isSelected = learningStyle === style.value
                  return (
                    <button
                      key={style.value}
                      type="button"
                      onClick={() => setLearningStyle(style.value)}
                      className={`flex items-start gap-3.5 p-3 rounded-xl border text-left transition-all duration-200 cursor-pointer ${
                        isSelected 
                          ? 'border-rust/80 bg-rust/5 text-rust shadow-xs shadow-rust/5' 
                          : 'border-border/60 bg-bg/40 text-text-muted hover:border-border hover:text-text hover:bg-bg/70'
                      }`}
                    >
                      <div className={`p-2 rounded-lg mt-0.5 transition-colors ${isSelected ? 'bg-rust/15 text-rust' : 'bg-border/40 text-text-muted/80'}`}>
                        <StyleIcon className="w-4 h-4" />
                      </div>
                      <div>
                        <h4 className="text-xs font-bold">{style.label}</h4>
                        <p className="text-[10px] text-text-muted mt-0.5 leading-relaxed">{style.desc}</p>
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Error logs */}
            {error && (
              <div className="p-3.5 rounded-xl bg-red-500/10 border border-red-500/20 text-red-500 text-xs font-semibold">
                {error}
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={submitting}
              className={`w-full py-3 rounded-xl text-white font-semibold text-sm transition-all duration-200 flex items-center justify-center gap-2 cursor-pointer ${
                submitting 
                  ? 'bg-rust/60 cursor-not-allowed' 
                  : 'bg-rust hover:bg-rust/90 shadow-md shadow-rust/20 hover:shadow-lg hover:shadow-rust/30 active:scale-[0.99]'
              }`}
            >
              {submitting ? (
                <>
                  <Sparkles className="w-4 h-4 animate-spin" />
                  <span>Saving setup...</span>
                </>
              ) : (
                <span>Save and Continue</span>
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
