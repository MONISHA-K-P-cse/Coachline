import { useState } from 'react'
import { Nav } from '../components/Nav'
import { useAuth } from '../lib/AuthContext'
import { KeyRound, Mail, User, Sparkles } from 'lucide-react'

type Page = 'landing' | 'login' | 'register' | 'onboarding' | 'workspace' | 'roadmap' | 'interview' | 'notes' | 'mastery' | 'mentor'
interface Props { navigate: (p: Page) => void }

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
    <div className="min-h-screen bg-bg text-text transition-colors duration-300 font-sans flex flex-col">
      <Nav page="landing" navigate={navigate} />
      
      <div className="flex-1 flex flex-col items-center justify-center px-6 py-12">
        <div className="w-full max-w-[420px]">
          {/* Header */}
          <div className="text-center mb-8">
            <h1 className="font-display text-3xl font-bold tracking-tight text-text">
              Create your account
            </h1>
            <p className="text-xs text-text-muted mt-2">
              Start optimizing your engineering preparation today.
            </p>
          </div>

          {/* Form Card */}
          <form 
            onSubmit={handleSubmit} 
            className="p-8 rounded-2xl border border-border/80 bg-card-bg/90 backdrop-blur-xl shadow-lg flex flex-col gap-5 glass-panel"
          >
            {/* Full Name field */}
            <div className="flex flex-col gap-1.5">
              <label className="text-[11px] font-bold uppercase tracking-wider text-text-muted" htmlFor="full_name">
                Full Name
              </label>
              <div className="relative flex items-center">
                <User className="w-4 h-4 text-text-muted/70 absolute left-3.5 pointer-events-none" />
                <input
                  id="full_name"
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-border/70 bg-bg/50 text-sm focus:outline-none focus:border-rust/80 focus:ring-3 focus:ring-rust/15 transition-all placeholder:text-text-muted/40"
                  placeholder="Alex Rivera"
                />
              </div>
            </div>

            {/* Email field */}
            <div className="flex flex-col gap-1.5">
              <label className="text-[11px] font-bold uppercase tracking-wider text-text-muted" htmlFor="email">
                Email Address
              </label>
              <div className="relative flex items-center">
                <Mail className="w-4 h-4 text-text-muted/70 absolute left-3.5 pointer-events-none" />
                <input
                  id="email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-border/70 bg-bg/50 text-sm focus:outline-none focus:border-rust/80 focus:ring-3 focus:ring-rust/15 transition-all placeholder:text-text-muted/40"
                  placeholder="name@example.com"
                />
              </div>
            </div>

            {/* Password field */}
            <div className="flex flex-col gap-1.5">
              <label className="text-[11px] font-bold uppercase tracking-wider text-text-muted" htmlFor="password">
                Password
              </label>
              <div className="relative flex items-center">
                <KeyRound className="w-4 h-4 text-text-muted/70 absolute left-3.5 pointer-events-none" />
                <input
                  id="password"
                  type="password"
                  required
                  minLength={8}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-border/70 bg-bg/50 text-sm focus:outline-none focus:border-rust/80 focus:ring-3 focus:ring-rust/15 transition-all placeholder:text-text-muted/40"
                  placeholder="At least 8 characters"
                />
              </div>
            </div>

            {/* Error alerts */}
            {(localError || error) && (
              <div className="p-3.5 rounded-xl bg-red-500/10 border border-red-500/20 text-red-500 text-xs font-semibold leading-relaxed">
                {localError || error}
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
                  <span>Creating account...</span>
                </>
              ) : (
                <span>Create account</span>
              )}
            </button>
          </form>

          {/* Sign in footer link */}
          <p className="text-center text-xs text-text-muted mt-6">
            Already have an account?{' '}
            <button
              onClick={() => navigate('login')}
              className="text-rust font-semibold hover:underline cursor-pointer bg-transparent border-none p-0"
            >
              Sign in
            </button>
          </p>
        </div>
      </div>
    </div>
  )
}
