import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Nav } from '../components/Nav'
import { useAuth } from '../lib/AuthContext'
import { 
  Sparkles, Code, Shield, Activity, FileText, Brain, 
  Volume2, ArrowRight, Check, ChevronDown, Play, Users, 
  Award, Star, Zap, Cpu, Lock, X
} from 'lucide-react'

type Page = 'landing' | 'login' | 'register' | 'onboarding' | 'workspace' | 'roadmap' | 'interview' | 'notes' | 'mastery' | 'mentor'

interface LandingProps {
  navigate: (p: Page) => void
}

const CAROUSEL_CARDS = [
  {
    id: 'resume',
    icon: FileText,
    title: 'Resume Optimizer',
    desc: 'Analyzes your resume against target roles and generates optimized bullet points.',
    badge: 'AI Agent'
  },
  {
    id: 'interview',
    icon: Volume2,
    title: 'Adaptive Mock Interview',
    desc: 'Websocket-powered live session with smart speech-to-text and speech output.',
    badge: 'Real-time'
  },
  {
    id: 'galaxy',
    icon: Brain,
    title: 'Knowledge Constellation',
    desc: 'Visualizes your mastery in a floating node constellation to track prep progress.',
    badge: 'Interactive'
  },
  {
    id: 'bob',
    icon: Shield,
    title: 'IBM Bob Code Auditor',
    desc: 'Hacker-style Monaco workspace executing security scans on your code snippets.',
    badge: 'Security'
  }
]

const BENTO_FEATURES = [
  {
    icon: Zap,
    title: 'Devil\'s Advocate Mode',
    desc: 'The AI actively questions your assumptions, mimicking realistic pressure and cross-examination.',
    size: 'col-span-1 md:col-span-2'
  },
  {
    icon: Cpu,
    title: 'Granite LLM Integration',
    desc: 'Powered by highly optimized enterprise LLM agents for deep technical accuracy.',
    size: 'col-span-1'
  },
  {
    icon: Activity,
    title: 'Live Confidence Tracking',
    desc: 'Real-time speech rate and pause auditing to measure your stress under questioning.',
    size: 'col-span-1'
  },
  {
    icon: Lock,
    title: 'Bob Auditor Scan',
    desc: 'Monaco-based IDE sandbox that flags SQLi, Race Conditions, CORS wildcards, and XSS exploits.',
    size: 'col-span-1 md:col-span-2'
  }
]

const FAQS = [
  {
    q: 'How does the IBM Bob Auditor work?',
    a: 'IBM Bob is an agentic code auditor built into your workspace. When you select a security challenge (like SQL Injection or CORS exploits), Bob runs a multi-step vulnerability scan, flags issues on a severity timeline, and generates secure refactored code for side-by-side comparison.'
  },
  {
    q: 'What is the Knowledge Galaxy?',
    a: 'The Knowledge Galaxy (or Constellation) is a beautiful visual map representing your computer science and behavioral topic mastery. As you answer mock questions, your mastery percentages update dynamically, altering connections and nodes.'
  },
  {
    q: 'Does it support real-time audio and speech?',
    a: 'Yes! CoachLine uses native WebSpeech synthesis for voice questions and recognition for answers. Combined with real-time WebSocket communication, it offers a hands-free, video-call style interview setup.'
  },
  {
    q: 'Can I target specific companies like Adobe, Netflix, or Microsoft?',
    a: 'Yes, inside Onboarding or Settings you can toggle Target Companies. This updates the difficulty parameters and focuses the recommended questions to match their standard hiring patterns.'
  }
]

const TESTIMONIALS = [
  {
    name: 'Sarah Jenkins',
    role: 'Staff Engineer at Stripe',
    image: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=120&h=120&q=80',
    content: 'CoachLine completely transformed my backend system design preparation. The feedback loop is instant, and the Devil\'s Advocate mode mimics actual staff panel loops.'
  },
  {
    name: 'David Chen',
    role: 'L5 Software Engineer at Google',
    image: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=120&h=120&q=80',
    content: 'The IBM Bob code auditor was a highlight for my security rounds. Having a Monaco editor next to vulnerability scan timelines felt exactly like real-world engineering auditing.'
  },
  {
    name: 'Alena Rostova',
    role: 'Solutions Architect at AWS',
    image: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=120&h=120&q=80',
    content: 'The custom study sheets automatically generated from my weak topics saved me weeks of manual tracking. The visual galaxy map made learning addictive.'
  }
]

export default function Landing({ navigate }: LandingProps) {
  const { user } = useAuth()
  const [activeFaq, setActiveFaq] = useState<number | null>(null)
  const [activeCarouselIndex, setActiveCarouselIndex] = useState(0)
  const [showDemoModal, setShowDemoModal] = useState(false)

  useEffect(() => {
    const interval = setInterval(() => {
      setActiveCarouselIndex((prev) => (prev + 1) % CAROUSEL_CARDS.length)
    }, 4000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="min-h-screen bg-bg text-text selection:bg-rust/20 overflow-x-hidden font-sans">
      <Nav page="landing" navigate={navigate} />

      {/* ── HERO SECTION ────────────────────────────────────────────────── */}
      <section className="relative pt-32 pb-20 md:pt-40 md:pb-28 flex flex-col items-center justify-center px-6">
        {/* Glowing backdrop elements */}
        <div className="absolute top-20 left-1/2 -translate-x-1/2 w-full max-w-7xl h-[450px] bg-gradient-to-tr from-rust/10 via-accent/5 to-transparent blur-3xl pointer-events-none -z-10 rounded-full" />
        <div className="absolute top-40 left-1/4 w-[250px] h-[250px] bg-accent/5 blur-3xl pointer-events-none -z-10 rounded-full animate-pulse" />

        {/* Floating 3D Carousel Widget */}
        <div className="w-full max-w-lg h-[240px] flex items-center justify-center relative mb-12 select-none perspective-1000">
          <AnimatePresence mode="wait">
            {CAROUSEL_CARDS.map((card, idx) => {
              if (idx !== activeCarouselIndex) return null
              const Icon = card.icon
              return (
                <motion.div
                  key={card.id}
                  initial={{ opacity: 0, rotateY: 45, translateZ: -60, scale: 0.9 }}
                  animate={{ opacity: 1, rotateY: 0, translateZ: 0, scale: 1 }}
                  exit={{ opacity: 0, rotateY: -45, translateZ: -60, scale: 0.9 }}
                  transition={{ duration: 0.5, ease: 'easeOut' }}
                  className="absolute w-full max-w-[380px] p-6 rounded-2xl border border-border bg-card-bg/90 backdrop-blur-md shadow-2xl flex flex-col gap-4 text-left glass-panel cursor-pointer"
                  onClick={() => navigate(user ? 'workspace' : 'register')}
                >
                  <div className="flex items-center justify-between">
                    <div className="p-2.5 rounded-xl bg-rust/10 text-rust">
                      <Icon className="w-5 h-5" />
                    </div>
                    <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-border/40 text-text-muted">
                      {card.badge}
                    </span>
                  </div>
                  <div>
                    <h3 className="font-display text-lg font-bold text-text">{card.title}</h3>
                    <p className="text-xs text-text-muted mt-1.5 leading-relaxed">{card.desc}</p>
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-rust font-semibold mt-1">
                    <span>Try Feature</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </div>
                </motion.div>
              )
            })}
          </AnimatePresence>
        </div>

        {/* Hero Copy */}
        <div className="text-center max-w-3xl mt-4">
          <motion.div 
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-border/80 bg-panel-bg/60 text-xs font-semibold text-text-muted mb-6"
          >
            <Sparkles className="w-3.5 h-3.5 text-accent animate-spin" style={{ animationDuration: '3s' }} />
            <span>AI-Powered Interview Simulation Workspace</span>
          </motion.div>

          <motion.h1 
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="font-display text-4xl sm:text-5xl md:text-6xl font-bold tracking-tight leading-[1.1] text-text"
          >
            Land your dream engineering role with <span className="bg-gradient-to-r from-rust to-accent bg-clip-text text-transparent">agentic evaluation</span>
          </motion.h1>

          <motion.p 
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="text-base sm:text-lg text-text-muted mt-6 max-w-2xl mx-auto leading-relaxed"
          >
            Simulate interactive mock interviews, scan challenges with the IBM Bob Agentic Auditor, optimize resume scoring, and track mastery maps designed for FAANG.
          </motion.p>

          <motion.div 
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="flex flex-col sm:flex-row items-center justify-center gap-4 mt-10"
          >
            <button
              onClick={() => navigate(user ? 'workspace' : 'register')}
              className="w-full sm:w-auto px-7 py-3.5 rounded-xl font-semibold text-white bg-rust hover:bg-rust/90 shadow-md shadow-rust/20 hover:shadow-lg hover:shadow-rust/30 transition-all duration-200 cursor-pointer flex items-center justify-center gap-2 active:scale-[0.99]"
            >
              <span>Start Interview Journey</span>
              <ArrowRight className="w-4 h-4" />
            </button>
            <button
              onClick={() => setShowDemoModal(true)}
              className="w-full sm:w-auto px-7 py-3.5 rounded-xl font-semibold text-text-muted border border-border/80 bg-card-bg/60 hover:bg-border/30 hover:text-text transition-all duration-200 cursor-pointer flex items-center justify-center gap-2 shadow-xs active:scale-[0.99]"
            >
              <Play className="w-4 h-4 text-rust" />
              <span>Interactive Demo</span>
            </button>
          </motion.div>
        </div>
      </section>

      {/* ── BENTO FEATURES GRID ─────────────────────────────────────────── */}
      <section className="py-20 bg-panel-bg/30 border-y border-border/60 px-6">
        <div className="max-w-5xl mx-auto">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <h2 className="font-display text-3xl font-bold text-text">Intelligent interview ecosystem</h2>
            <p className="text-sm text-text-muted mt-3">
              Explore advanced systems engineered specifically to help you stand out under technical examinations.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {BENTO_FEATURES.map((feat, idx) => {
              const Icon = feat.icon
              return (
                <motion.div
                  key={idx}
                  whileHover={{ y: -4 }}
                  className={`p-6 rounded-2xl border border-border/80 bg-card-bg/80 glass-panel glass-panel-hover ${feat.size} flex flex-col justify-between min-h-[180px] transition-all`}
                >
                  <div className="p-3 w-fit rounded-xl bg-rust/10 text-rust shadow-xs">
                    <Icon className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="font-display text-base font-bold text-text mt-6">{feat.title}</h3>
                    <p className="text-xs text-text-muted mt-2 leading-relaxed">{feat.desc}</p>
                  </div>
                </motion.div>
              )
            })}
          </div>
        </div>
      </section>

      {/* ── TESTIMONIALS SECTION ───────────────────────────────────────── */}
      <section className="py-20 px-6">
        <div className="max-w-5xl mx-auto">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <div className="flex justify-center gap-1 mb-3 text-accent">
              {[...Array(5)].map((_, i) => <Star key={i} className="w-4 h-4 fill-current" />)}
            </div>
            <h2 className="font-display text-3xl font-bold text-text">Endorsed by engineering veterans</h2>
            <p className="text-sm text-text-muted mt-2">
              See how modern software engineers are using CoachLine to crush complex panel loops.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {TESTIMONIALS.map((t, idx) => (
              <div key={idx} className="p-6 rounded-2xl border border-border bg-card-bg/40 flex flex-col justify-between gap-6 relative">
                <p className="text-xs text-text-muted italic leading-relaxed">"{t.content}"</p>
                <div className="flex items-center gap-3 mt-4">
                  <img src={t.image} alt={t.name} className="w-9 h-9 rounded-full object-cover border border-border/80" />
                  <div>
                    <h4 className="text-xs font-bold text-text">{t.name}</h4>
                    <span className="text-[10px] text-text-muted">{t.role}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── FAQ SECTION ────────────────────────────────────────────────── */}
      <section className="py-20 bg-panel-bg/30 border-t border-border/60 px-6">
        <div className="max-w-3xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="font-display text-3xl font-bold text-text">Frequently Asked Questions</h2>
            <p className="text-sm text-text-muted mt-3">Everything you need to know about the platforms capabilities.</p>
          </div>

          <div className="flex flex-col gap-4">
            {FAQS.map((faq, idx) => {
              const isOpen = activeFaq === idx
              return (
                <div 
                  key={idx}
                  className="rounded-2xl border border-border bg-card-bg/60 overflow-hidden transition-all duration-300"
                >
                  <button
                    onClick={() => setActiveFaq(isOpen ? null : idx)}
                    className="w-full flex items-center justify-between p-5 text-left font-semibold text-sm text-text focus:outline-none cursor-pointer hover:bg-border/10 transition-colors"
                  >
                    <span>{faq.q}</span>
                    <ChevronDown className={`w-4 h-4 text-text-muted transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
                  </button>
                  <AnimatePresence initial={false}>
                    {isOpen && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.25, ease: 'easeInOut' }}
                      >
                        <p className="px-5 pb-5 text-xs text-text-muted leading-relaxed border-t border-border/30 pt-3">
                          {faq.a}
                        </p>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              )
            })}
          </div>
        </div>
      </section>

      {/* ── FINAL CTA SECTION ─────────────────────────────────────────── */}
      <section className="relative py-28 overflow-hidden text-center px-6">
        {/* Glow backdrop */}
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-rust/5 to-transparent pointer-events-none" />
        
        <div className="max-w-2xl mx-auto relative z-10">
          <h2 className="font-display text-3xl sm:text-4xl font-bold text-text">Unlock your career constellation</h2>
          <p className="text-sm text-text-muted mt-4 max-w-md mx-auto leading-relaxed">
            Get personalized roadmap milestones, evaluate real voice answers, and secure your systems with IBM Bob.
          </p>
          <div className="mt-8 flex justify-center">
            <button
              onClick={() => navigate(user ? 'workspace' : 'register')}
              className="px-8 py-3.5 rounded-xl font-semibold text-white bg-rust hover:bg-rust/90 shadow-md shadow-rust/10 hover:shadow-lg transition-all duration-150 cursor-pointer flex items-center gap-2"
            >
              <span>Get Started Now</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </section>

      {/* ── FOOTER ────────────────────────────────────────────────────── */}
      <footer className="py-12 border-t border-border/80 bg-bg px-6">
        <div className="max-w-5xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-lg bg-gradient-to-tr from-rust to-accent" />
            <span className="font-display font-bold text-base text-text">Coachline</span>
          </div>
          <p className="text-xs text-text-muted">
            © {new Date().getFullYear()} Coachline AI. Built with Google Gemini & IBM Granite.
          </p>
          <div className="flex items-center gap-6">
            <a href="#" className="text-xs text-text-muted hover:text-text">Privacy Policy</a>
            <a href="#" className="text-xs text-text-muted hover:text-text">Terms of Service</a>
            <a href="#" className="text-xs text-text-muted hover:text-text">Contact Support</a>
          </div>
        </div>
      </footer>

      {/* ── INTERACTIVE MOCK DEMO MODAL ─────────────────────────────────── */}
      <AnimatePresence>
        {showDemoModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-bg/65 backdrop-blur-md flex items-center justify-center z-50 p-6"
          >
            <motion.div
              initial={{ scale: 0.95, y: 15 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.95, y: 15 }}
              className="w-full max-w-xl bg-card-bg border border-border rounded-2xl p-6 shadow-2xl flex flex-col gap-5 relative glass-panel text-left"
            >
              <button
                onClick={() => setShowDemoModal(false)}
                className="absolute top-4 right-4 text-text-muted hover:text-text cursor-pointer p-1"
                aria-label="Close demo"
              >
                <X className="w-4 h-4" />
              </button>

              <div>
                <span className="text-[10px] uppercase font-bold tracking-wider text-rust">Live Simulation Demo</span>
                <h3 className="font-display text-lg font-bold text-text mt-1">Adaptive Dialogue Example</h3>
              </div>

              {/* Chat script mock */}
              <div className="flex flex-col gap-4 max-h-[300px] overflow-y-auto p-3.5 bg-panel-bg/30 rounded-xl border border-border/40">
                {/* Turn 1 */}
                <div className="flex flex-col items-start gap-1">
                  <div className="p-3 rounded-xl bg-card-bg border border-border text-xs text-text leading-relaxed">
                    <span className="font-bold text-rust block mb-1">CoachLine AI (Interviewer)</span>
                    "Let's dive into system design. How would you design a scalable notification service that handles millions of requests during peak traffic?"
                  </div>
                </div>

                {/* Turn 2 */}
                <div className="flex flex-col items-end gap-1">
                  <div className="p-3 rounded-xl bg-rust text-white text-xs leading-relaxed max-w-[90%] shadow-sm">
                    <span className="font-bold text-white/90 block mb-1">Candidate Response</span>
                    "I'd use a message queue like RabbitMQ or Kafka to buffer incoming requests. A worker pool would consume tasks from the queue and throttle dispatch rates according to external provider limits (APNS, Firebase). User settings and rate limits would be cached in Redis to minimize database lookups."
                  </div>
                </div>

                {/* Turn 3 */}
                <div className="flex flex-col items-start gap-1">
                  <div className="p-3 rounded-xl bg-card-bg border border-border text-xs text-text-muted leading-relaxed">
                    <span className="font-bold text-rust block mb-1">CoachLine AI (Evaluation Agent)</span>
                    "Analyzing response structure... Score: 93%. Communication: Excellent choice of caching and queue systems. Suggestion: elaborate on dead-letter queues (DLQ) for failed notification retries."
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-3 border-t border-border pt-4">
                <button
                  onClick={() => setShowDemoModal(false)}
                  className="px-4 py-2 border border-border hover:bg-border/20 rounded-lg text-xs font-semibold text-text-muted cursor-pointer"
                >
                  Close Demo
                </button>
                <button
                  onClick={() => {
                    setShowDemoModal(false)
                    navigate(user ? 'workspace' : 'register')
                  }}
                  className="px-5 py-2 bg-rust hover:bg-rust/90 text-white rounded-lg text-xs font-bold transition-all shadow cursor-pointer"
                >
                  Sign up & Practice
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
