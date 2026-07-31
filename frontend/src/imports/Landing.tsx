import { useState, useEffect, useRef, type CSSProperties } from 'react'
import { Nav } from '../components/Nav'
import { useAuth } from '../lib/AuthContext'

type Page = 'landing' | 'login' | 'register' | 'onboarding' | 'workspace' | 'roadmap' | 'interview' | 'notes' | 'mastery' | 'mentor'

interface LandingProps {
  navigate: (p: Page) => void
}

// ─── Scroll reveal hook ──────────────────────────────────────────────────────

function useReveal(threshold = 0.14) {
  const ref = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(false)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setVisible(true) },
      { threshold }
    )
    obs.observe(el)
    return () => obs.disconnect()
  }, [threshold])
  return { ref, visible }
}

// ─── Feature card data ───────────────────────────────────────────────────────

const FEATURES = [
  {
    id: 'adaptive',
    icon: (
      <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
        <circle cx="11" cy="11" r="9" stroke="#B5502E" strokeWidth="1.6" />
        <circle cx="11" cy="11" r="5" stroke="#C97350" strokeWidth="1.6" />
        <circle cx="11" cy="11" r="2" fill="#B5502E" />
      </svg>
    ),
    label: 'Adaptive Interview',
    title: 'Adaptive Mock Interview',
    desc: 'Questions get harder or easier in real time based on how you\'re actually answering — not a fixed script.',
    bg: '#FFF8F5',
    tag: 'Core',
  },
  {
    id: 'notes',
    icon: (
      <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
        <rect x="3" y="3" width="16" height="16" rx="3" stroke="#C97350" strokeWidth="1.6" />
        <path d="M7 8h8M7 11h5" stroke="#C97350" strokeWidth="1.6" strokeLinecap="round" />
        <path d="M14 14.5c1-1 2.5-.5 2.5 1" stroke="#B5502E" strokeWidth="1.4" strokeLinecap="round" />
      </svg>
    ),
    label: 'Auto Notes',
    title: 'Auto-Regenerating Notes',
    desc: 'A weak answer instantly triggers new, targeted study notes for that exact gap — no action needed from you.',
    bg: '#FDF6EE',
    tag: 'Automatic',
  },
  {
    id: 'score',
    icon: (
      <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
        <path d="M4 17L8 11L12 14L16 7L19 10" stroke="#E0A458" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="4" cy="17" r="1.5" fill="#B5502E" />
        <circle cx="19" cy="10" r="1.5" fill="#E0A458" />
      </svg>
    ),
    label: 'Readiness Score',
    title: 'Resume-to-Readiness Score',
    desc: 'A real percentage tied to your actual resume content, with specific gaps called out — not a generic checklist.',
    bg: '#FFFBF3',
    tag: 'Personalized',
  },
  {
    id: 'map',
    icon: (
      <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
        <path d="M3 6l5-2 6 3 5-2v11l-5 2-6-3-5 2V6z" stroke="#B5502E" strokeWidth="1.6" strokeLinejoin="round" />
        <path d="M8 4v11M14 7v11" stroke="#C97350" strokeWidth="1.2" />
      </svg>
    ),
    label: 'Mastery Map',
    title: 'Mastery Map',
    desc: 'A visual map of every topic you\'re building toward — showing where you\'re strong and where you\'re not.',
    bg: '#FFF5F0',
    tag: 'Visual',
  },
  {
    id: 'company',
    icon: (
      <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
        <rect x="3" y="7" width="16" height="12" rx="2" stroke="#C97350" strokeWidth="1.6" />
        <path d="M7 7V5a4 4 0 018 0v2" stroke="#C97350" strokeWidth="1.6" />
        <circle cx="11" cy="13" r="2" stroke="#B5502E" strokeWidth="1.4" />
      </svg>
    ),
    label: 'Company-Aware',
    title: 'Company-Aware Prep',
    desc: 'Prep material shaped around your actual target role and company — not one-size-fits-all questions.',
    bg: '#FFF8F5',
    tag: 'Targeted',
  },
  {
    id: 'countdown',
    icon: (
      <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
        <circle cx="11" cy="12" r="8" stroke="#E0A458" strokeWidth="1.6" />
        <path d="M11 8v4l3 2" stroke="#B5502E" strokeWidth="1.6" strokeLinecap="round" />
        <path d="M8 3h6" stroke="#C97350" strokeWidth="1.4" strokeLinecap="round" />
      </svg>
    ),
    label: 'Countdown',
    title: 'Readiness Countdown',
    desc: 'A running plan that recalculates itself daily based on your interview date and what\'s still weak.',
    bg: '#FFFAF3',
    tag: 'Live',
  },
]

// ─── Heatmap data ────────────────────────────────────────────────────────────

const HEATMAP_COLORS = [
  'rgba(181,80,46,0.08)',
  'rgba(224,164,88,0.28)',
  'rgba(201,115,80,0.50)',
  '#C97350',
  '#B5502E',
]

const HEATMAP_DATA = [
  0, 0, 1, 0, 0, 2, 1,
  0, 1, 2, 1, 2, 3, 2,
  1, 2, 3, 2, 3, 4, 3,
  2, 3, 4, 3, 4, 4, 3,
  3, 4, 4, 4, 3, 4, 4,
]

// ─── Card position helper ────────────────────────────────────────────────────

const OFFSETS: { tx: number; tz: number; ry: number; scale: number; op: number; zi: number }[] = [
  { tx: -70,  tz:  22, ry:  3,  scale: 0.99, op: 1.00, zi: 6 }, // offset 0 — front-left
  { tx:  80,  tz:  22, ry: -3,  scale: 0.99, op: 1.00, zi: 6 }, // offset 1 — front-right
  { tx: 210,  tz: -42, ry: -16, scale: 0.87, op: 0.75, zi: 3 }, // offset 2
  { tx: 330,  tz:-110, ry: -28, scale: 0.72, op: 0.38, zi: 1 }, // offset 3 — far right
  { tx:-330,  tz:-110, ry:  28, scale: 0.72, op: 0.38, zi: 1 }, // offset 4 — far left
  { tx:-210,  tz: -42, ry:  16, scale: 0.87, op: 0.75, zi: 3 }, // offset 5
]

function getCardStyle(i: number, active: number): CSSProperties {
  const n = OFFSETS.length
  const offset = ((i - active) % n + n) % n
  const p = OFFSETS[offset]
  return {
    position: 'absolute',
    left: '50%',
    top: 0,
    width: 198,
    transition: 'all 0.85s cubic-bezier(0.4, 0, 0.2, 1)',
    transform: `translateX(calc(-50% + ${p.tx}px)) translateZ(${p.tz}px) rotateY(${p.ry}deg) scale(${p.scale})`,
    opacity: p.op,
    zIndex: p.zi,
    pointerEvents: 'none',
  }
}

const FLOAT_ANIMS = ['floatA', 'floatB', 'floatC', 'floatA', 'floatB', 'floatC']
const FLOAT_DURS  = ['4.0s',  '5.2s',  '3.7s',  '4.8s',  '3.5s',  '5.0s']

// ─── Feature card component ──────────────────────────────────────────────────

function FeatureCard({ card, active }: { card: (typeof FEATURES)[number]; active: boolean }) {
  return (
    <div
      style={{
        width: 198,
        background: card.bg,
        borderRadius: 16,
        border: active
          ? '1.5px solid rgba(181,80,46,0.45)'
          : '1.5px solid rgba(181,80,46,0.13)',
        boxShadow: active
          ? '0 12px 40px rgba(181,80,46,0.22), 0 2px 8px rgba(0,0,0,0.06)'
          : '0 6px 24px rgba(0,0,0,0.06), 0 1px 4px rgba(0,0,0,0.04)',
        padding: '20px 18px 18px',
        transition: 'border-color 0.5s ease, box-shadow 0.5s ease',
        userSelect: 'none',
      }}
    >
      <div
        style={{
          display: 'inline-flex',
          padding: '7px 10px 6px 10px',
          borderRadius: 10,
          background: 'rgba(181,80,46,0.08)',
          marginBottom: 12,
        }}
      >
        {card.icon}
      </div>
      <div
        style={{
          fontSize: 10,
          fontWeight: 600,
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
          color: '#B5502E',
          marginBottom: 6,
          fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif",
        }}
      >
        {card.label}
      </div>
      <div
        style={{
          fontSize: 14,
          fontWeight: 700,
          color: '#1C1917',
          lineHeight: 1.35,
          marginBottom: 8,
          fontFamily: "'Fraunces', Georgia, serif",
        }}
      >
        {card.title}
      </div>
      <p
        style={{
          fontSize: 12,
          color: '#7A6B63',
          lineHeight: 1.6,
          margin: 0,
          fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif",
        }}
      >
        {card.desc}
      </p>
      <div
        style={{
          marginTop: 14,
          height: 2,
          borderRadius: 2,
          background: active
            ? 'linear-gradient(90deg, #B5502E 0%, #E0A458 100%)'
            : 'rgba(181,80,46,0.15)',
          transition: 'background 0.5s ease',
        }}
      />
    </div>
  )
}

// ─── Testimonials ────────────────────────────────────────────────────────────

const TESTIMONIALS = [
  {
    quote:
      "I went from bombing every system design question to landing my offer at Stripe. The adaptive interviews caught exactly what I was glossing over.",
    name: 'Priya S.',
    role: 'Software Engineer → Stripe',
    initials: 'PS',
  },
  {
    quote:
      "The notes that regenerated after my weak answers were better than anything I could have written myself. It felt like having a coach watching in real time.",
    name: 'Marcus T.',
    role: 'Backend Engineer → Airbnb',
    initials: 'MT',
  },
  {
    quote:
      "The Mastery Map made it obvious where my gaps were. I stopped wasting hours on topics I already knew and focused on what actually mattered.",
    name: 'Lena W.',
    role: 'ML Engineer → DeepMind',
    initials: 'LW',
  },
]

// ─── How-it-works steps ──────────────────────────────────────────────────────

const HOW_STEPS = [
  {
    n: '01',
    title: 'Upload your resume',
    body: 'Coachline reads your actual experience to build a personalized readiness baseline — not a generic quiz.',
  },
  {
    n: '02',
    title: 'Practice, then watch it adapt',
    body: 'Every answer you give reshapes the next question and triggers targeted notes where your gaps are.',
  },
  {
    n: '03',
    title: 'Walk in knowing you\'re ready',
    body: 'Your Mastery Map and Readiness Countdown tell you exactly where you stand, every single day.',
  },
]

// ─── Main component ──────────────────────────────────────────────────────────

export default function Landing({ navigate }: LandingProps) {
  const { user } = useAuth()
  const goToApp = () => navigate(user ? 'workspace' : 'register')
  const [activeCard, setActiveCard] = useState(0)

  useEffect(() => {
    const id = setInterval(() => setActiveCard((p) => (p + 1) % FEATURES.length), 3200)
    return () => clearInterval(id)
  }, [])

  const r1 = useReveal()
  const r2 = useReveal()
  const r3 = useReveal()
  const r4 = useReveal()
  const r5 = useReveal()
  const r6 = useReveal()

  return (
    <div style={{ fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif", backgroundColor: '#FAFAF8', color: '#1C1917' }}>
      <Nav page="landing" navigate={navigate} />

      {/* ── HERO ─────────────────────────────────────────────────────────── */}
      <section
        style={{
          position: 'relative',
          minHeight: '100svh',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'flex-end',
          paddingTop: 'clamp(96px, 16vh, 160px)',
          paddingBottom: '9vh',
        }}
      >
        {/* Particle background placeholder — reserved for future ember/dust mote system */}
        <div
          aria-hidden
          style={{
            position: 'absolute',
            inset: 0,
            zIndex: 0,
            background: [
              'radial-gradient(ellipse at 78% 12%, rgba(201,115,80,0.30) 0%, transparent 52%)',
              'radial-gradient(ellipse at 12% 88%, rgba(224,164,88,0.22) 0%, transparent 50%)',
              'radial-gradient(ellipse at 52% 55%, rgba(243,228,210,0.55) 0%, transparent 62%)',
              '#FAFAF8',
            ].join(', '),
          }}
        />
        {/* Subtle grain texture — placeholder layer for particle animation */}
        <div
          aria-hidden
          style={{
            position: 'absolute',
            inset: 0,
            zIndex: 1,
            opacity: 0.025,
            backgroundImage:
              'url("data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' width=\'300\' height=\'300\'%3E%3Cfilter id=\'n\'%3E%3CfeTurbulence type=\'fractalNoise\' baseFrequency=\'0.75\' numOctaves=\'4\' stitchTiles=\'stitch\'/%3E%3C/filter%3E%3Crect width=\'300\' height=\'300\' filter=\'url(%23n)\'/%3E%3C/svg%3E")',
            backgroundSize: '300px 300px',
          }}
        />

        {/* 3D Carousel — kept in normal document flow (not absolutely
            positioned) so it reserves real space in the hero's flex column
            and the headline below it can never overlap it, regardless of
            viewport height. Height is sized generously above the tallest
            card's rendered content (~230px) plus its float-animation
            travel (±9px) so nothing clips. */}
        <div
          aria-label="Coachline features"
          style={{
            position: 'relative',
            width: '100%',
            height: 300,
            flexShrink: 0,
            zIndex: 2,
            perspective: '1200px',
            perspectiveOrigin: '50% 60%',
          }}
        >
          <div style={{ position: 'relative', width: '100%', height: '100%' }}>
            {FEATURES.map((card, i) => (
              <div key={card.id} style={getCardStyle(i, activeCard)}>
                <div
                  style={{
                    animation: `${FLOAT_ANIMS[i]} ${FLOAT_DURS[i]} ease-in-out infinite`,
                  }}
                >
                  <FeatureCard card={card} active={((i - activeCard + 6) % 6) < 2} />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Carousel indicator dots — normal flow, directly below the
            carousel so spacing to the headline below stays consistent. */}
        <div
          style={{
            position: 'relative',
            display: 'flex',
            gap: 6,
            zIndex: 3,
            marginTop: 16,
            marginBottom: 32,
            flexShrink: 0,
          }}
        >
          {FEATURES.map((_, i) => (
            <button
              key={i}
              onClick={() => setActiveCard(i)}
              style={{
                width: ((i - activeCard + 6) % 6) < 2 ? 20 : 6,
                height: 6,
                borderRadius: 3,
                background: ((i - activeCard + 6) % 6) < 2 ? '#B5502E' : 'rgba(181,80,46,0.25)',
                border: 'none',
                cursor: 'pointer',
                transition: 'all 0.4s ease',
                padding: 0,
              }}
              aria-label={`Show ${FEATURES[i].title}`}
            />
          ))}
        </div>

        {/* Hero text */}
        <div
          style={{
            position: 'relative',
            zIndex: 3,
            textAlign: 'center',
            padding: '0 24px',
            maxWidth: 640,
          }}
        >
          <h1
            style={{
              fontFamily: "'Fraunces', Georgia, serif",
              fontSize: 'clamp(2.6rem, 5.8vw, 4.6rem)',
              fontWeight: 700,
              lineHeight: 1.08,
              color: '#1C1917',
              letterSpacing: '-0.02em',
              marginBottom: 18,
            }}
          >
            Every interview changes
            <br />
            <em style={{ fontStyle: 'italic', color: '#B5502E' }}>what you learn next.</em>
          </h1>
          <p
            style={{
              fontSize: 'clamp(1rem, 1.8vw, 1.15rem)',
              color: '#7A6B63',
              lineHeight: 1.7,
              maxWidth: 500,
              margin: '0 auto 36px',
            }}
          >
            Coachline watches your answers, spots the cracks, and rebuilds your study plan —
            automatically, after every session.
          </p>
          <button
            onClick={goToApp}
            style={{
              background: 'linear-gradient(135deg, #B5502E 0%, #C97350 100%)',
              border: 'none',
              cursor: 'pointer',
              color: '#FAFAF8',
              fontSize: 15,
              fontWeight: 700,
              padding: '14px 32px',
              borderRadius: 100,
              fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif",
              boxShadow: '0 4px 20px rgba(181,80,46,0.38)',
              letterSpacing: '0.01em',
              transition: 'transform 0.15s ease, box-shadow 0.15s ease',
            }}
            onMouseEnter={(e) => {
              ;(e.currentTarget as HTMLButtonElement).style.transform = 'translateY(-2px)'
              ;(e.currentTarget as HTMLButtonElement).style.boxShadow =
                '0 8px 28px rgba(181,80,46,0.46)'
            }}
            onMouseLeave={(e) => {
              ;(e.currentTarget as HTMLButtonElement).style.transform = 'translateY(0)'
              ;(e.currentTarget as HTMLButtonElement).style.boxShadow =
                '0 4px 20px rgba(181,80,46,0.38)'
            }}
          >
            Start Your Journey
          </button>
        </div>
      </section>

      {/* ── BUILT DIFFERENT ──────────────────────────────────────────────── */}
      <section
        style={{
          padding: 'clamp(64px, 9vw, 100px) clamp(24px, 6vw, 80px)',
          backgroundColor: '#FAFAF8',
        }}
      >
        <div
          ref={r6.ref}
          className={`reveal ${r6.visible ? 'visible' : ''}`}
          style={{ textAlign: 'center', maxWidth: 580, margin: '0 auto 56px' }}
        >
          <div
            style={{
              display: 'inline-block',
              fontSize: 11,
              fontWeight: 700,
              letterSpacing: '0.12em',
              textTransform: 'uppercase',
              color: '#B5502E',
              background: 'rgba(181,80,46,0.09)',
              padding: '5px 14px',
              borderRadius: 100,
              marginBottom: 20,
            }}
          >
            Beyond mock interviews
          </div>
          <h2
            style={{
              fontFamily: "'Fraunces', Georgia, serif",
              fontSize: 'clamp(1.9rem, 3.8vw, 2.8rem)',
              fontWeight: 700,
              color: '#1C1917',
              letterSpacing: '-0.02em',
              lineHeight: 1.15,
              margin: 0,
            }}
          >
            Built different.
            <br />
            <em style={{ fontStyle: 'italic', color: '#C97350' }}>Not assembled from templates.</em>
          </h2>
        </div>

        <div
          style={{
            display: 'flex',
            gap: 18,
            alignItems: 'flex-start',
            maxWidth: 1100,
            margin: '0 auto',
            flexWrap: 'wrap',
          }}
        >
          {/* ── Card 1: Replay Diff ──────────────────────────────────────── */}
          <div
            className={`reveal reveal-d1 ${r6.visible ? 'visible' : ''}`}
            style={{
              flex: '1 1 230px',
              background: '#FFFFFF',
              borderRadius: 20,
              border: '1.5px solid rgba(181,80,46,0.12)',
              padding: '28px 22px 24px',
              boxShadow: '0 2px 16px rgba(0,0,0,0.04)',
              display: 'flex',
              flexDirection: 'column',
              gap: 18,
            }}
          >
            <div>
              <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: '#B5502E' }}>
                Replay Diff
              </span>
              <h3 style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 20, fontWeight: 700, color: '#1C1917', margin: '8px 0 8px', lineHeight: 1.25 }}>
                See yourself improve.
              </h3>
              <p style={{ fontSize: 13, color: '#7A6B63', lineHeight: 1.65, margin: 0 }}>
                Compare any two sessions side by side. Watch the gap close in real numbers.
              </p>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div style={{ background: '#FFF5F0', borderRadius: 12, padding: '11px 13px', border: '1px solid rgba(181,80,46,0.14)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 7 }}>
                  <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#B5502E', opacity: 0.65 }}>Session 1</span>
                  <span style={{ fontSize: 15, fontWeight: 800, color: '#B5502E', fontFamily: "'Fraunces', Georgia, serif" }}>62%</span>
                </div>
                <p style={{ fontSize: 11.5, color: '#7A6B63', lineHeight: 1.6, margin: 0 }}>
                  "I'd probably use Redis? I'm not sure about the consistency tradeoff here."
                </p>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div style={{ height: 1, flex: 1, background: 'rgba(181,80,46,0.15)' }} />
                <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                  <path d="M9 3v12M3 9l6 6 6-6" stroke="#C97350" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <div style={{ height: 1, flex: 1, background: 'rgba(181,80,46,0.15)' }} />
              </div>
              <div style={{ background: 'rgba(181,80,46,0.07)', borderRadius: 12, padding: '11px 13px', border: '1.5px solid rgba(181,80,46,0.26)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 7 }}>
                  <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#B5502E', opacity: 0.65 }}>Session 4</span>
                  <span style={{ fontSize: 15, fontWeight: 800, color: '#B5502E', fontFamily: "'Fraunces', Georgia, serif" }}>84%</span>
                </div>
                <p style={{ fontSize: 11.5, color: '#4B3D37', lineHeight: 1.6, margin: 0 }}>
                  "Read replicas for scale, primary for writes. Quorum reads handle consistency without sacrificing availability."
                </p>
              </div>
            </div>
          </div>

          {/* ── Card 2: Devil's Advocate Mode ────────────────────────────── */}
          <div
            className={`reveal reveal-d2 ${r6.visible ? 'visible' : ''}`}
            style={{
              flex: '1 1 265px',
              background: '#FFFFFF',
              borderRadius: 20,
              border: '1.5px solid rgba(181,80,46,0.12)',
              padding: '28px 22px 24px',
              boxShadow: '0 2px 16px rgba(0,0,0,0.04)',
              display: 'flex',
              flexDirection: 'column',
              gap: 18,
            }}
          >
            <div>
              <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: '#B5502E' }}>
                {"Devil's Advocate Mode"}
              </span>
              <h3 style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 20, fontWeight: 700, color: '#1C1917', margin: '8px 0 8px', lineHeight: 1.25 }}>
                {"We don't let you off easy."}
              </h3>
              <p style={{ fontSize: 13, color: '#7A6B63', lineHeight: 1.65, margin: 0 }}>
                Every strong answer gets challenged. Real interviewers push back. So do we.
              </p>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
              <div style={{ alignSelf: 'flex-end', maxWidth: '90%', background: '#FFF8F5', borderRadius: '14px 14px 4px 14px', padding: '10px 13px', border: '1px solid rgba(181,80,46,0.14)' }}>
                <p style={{ fontSize: 12, color: '#1C1917', lineHeight: 1.6, margin: 0 }}>
                  "I'd use microservices to keep teams decoupled and services independently scalable."
                </p>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                <div style={{ height: 1, flex: 1, background: 'rgba(201,115,80,0.18)' }} />
                <span style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#C97350', flexShrink: 0 }}>Escalating</span>
                <div style={{ height: 1, flex: 1, background: 'rgba(201,115,80,0.18)' }} />
              </div>
              <div style={{ alignSelf: 'flex-start', maxWidth: '92%', background: 'rgba(181,80,46,0.07)', borderRadius: '14px 14px 14px 4px', padding: '10px 13px', border: '1.5px solid rgba(181,80,46,0.20)' }}>
                <p style={{ fontSize: 12, color: '#4B3D37', lineHeight: 1.6, margin: 0 }}>
                  "Your team has 3 engineers and ships weekly. How do you handle distributed transactions without a shared DB?"
                </p>
              </div>
              <div style={{ alignSelf: 'flex-start', maxWidth: '86%', background: 'rgba(181,80,46,0.13)', borderRadius: '14px 14px 14px 4px', padding: '10px 13px', border: '1.5px solid rgba(181,80,46,0.30)' }}>
                <p style={{ fontSize: 12, color: '#3D2419', lineHeight: 1.6, margin: 0, fontWeight: 600 }}>
                  "Walk me through a failure scenario. What breaks first?"
                </p>
              </div>
            </div>
          </div>

          {/* ── Card 3: Panic Mode ────────────────────────────────────────── */}
          <div
            className={`reveal reveal-d3 ${r6.visible ? 'visible' : ''}`}
            style={{
              flex: '1 1 195px',
              background: 'linear-gradient(160deg, #1C1917 0%, #2E1F18 100%)',
              borderRadius: 20,
              border: '1.5px solid rgba(224,164,88,0.18)',
              padding: '28px 22px 24px',
              boxShadow: '0 2px 24px rgba(0,0,0,0.14)',
              display: 'flex',
              flexDirection: 'column',
              gap: 16,
            }}
          >
            <div>
              <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: '#E0A458' }}>
                Panic Mode
              </span>
              <h3 style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 20, fontWeight: 700, color: '#FAFAF8', margin: '8px 0 8px', lineHeight: 1.25 }}>
                48 hours out? We adapt.
              </h3>
              <p style={{ fontSize: 13, color: 'rgba(250,250,248,0.60)', lineHeight: 1.65, margin: 0 }}>
                Zero fluff. Pure triage. The three things that move your score.
              </p>
            </div>
            <div style={{ textAlign: 'center', padding: '10px 0 4px' }}>
              <div style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 52, fontWeight: 700, color: '#E0A458', lineHeight: 1, letterSpacing: '-0.03em' }}>
                48h
              </div>
              <div style={{ fontSize: 10.5, color: 'rgba(250,250,248,0.38)', letterSpacing: '0.10em', textTransform: 'uppercase', marginTop: 5 }}>
                Until your interview
              </div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
              {[
                { label: 'System design narrative', done: true },
                { label: 'STAR stories ×2', done: true },
                { label: 'Failure question answer', done: false },
              ].map((item) => (
                <div key={item.label} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <div
                    style={{
                      width: 18, height: 18, borderRadius: 5, flexShrink: 0,
                      background: item.done ? 'linear-gradient(135deg, #B5502E 0%, #E0A458 100%)' : 'rgba(255,255,255,0.08)',
                      border: item.done ? 'none' : '1.5px solid rgba(255,255,255,0.18)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}
                  >
                    {item.done && (
                      <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                        <path d="M2 5l2.5 2.5L8 3" stroke="#FAFAF8" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    )}
                  </div>
                  <span style={{ fontSize: 12.5, color: item.done ? 'rgba(250,250,248,0.75)' : 'rgba(250,250,248,0.45)', textDecoration: item.done ? 'line-through' : 'none' }}>
                    {item.label}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* ── Card 4: Consistency Heatmap ───────────────────────────────── */}
          <div
            className={`reveal reveal-d4 ${r6.visible ? 'visible' : ''}`}
            style={{
              flex: '1 1 215px',
              background: '#FFFFFF',
              borderRadius: 20,
              border: '1.5px solid rgba(181,80,46,0.12)',
              padding: '28px 22px 24px',
              boxShadow: '0 2px 16px rgba(0,0,0,0.04)',
              display: 'flex',
              flexDirection: 'column',
              gap: 18,
            }}
          >
            <div>
              <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: '#B5502E' }}>
                Consistency Heatmap
              </span>
              <h3 style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 20, fontWeight: 700, color: '#1C1917', margin: '8px 0 8px', lineHeight: 1.25 }}>
                Watch your streak build.
              </h3>
              <p style={{ fontSize: 13, color: '#7A6B63', lineHeight: 1.65, margin: 0 }}>
                Daily practice, logged. The habit compounds faster than you think.
              </p>
            </div>
            <div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 4 }}>
                {HEATMAP_DATA.map((intensity, idx) => (
                  <div
                    key={idx}
                    style={{
                      aspectRatio: '1',
                      borderRadius: 3,
                      background: HEATMAP_COLORS[intensity],
                    }}
                  />
                ))}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginTop: 10, justifyContent: 'flex-end' }}>
                <span style={{ fontSize: 10, color: '#A89088' }}>Less</span>
                {[0, 1, 2, 3, 4].map((i) => (
                  <div key={i} style={{ width: 10, height: 10, borderRadius: 2, background: HEATMAP_COLORS[i] }} />
                ))}
                <span style={{ fontSize: 10, color: '#A89088' }}>More</span>
              </div>
            </div>
            <div style={{ marginTop: 'auto', padding: '10px 14px', background: 'rgba(181,80,46,0.06)', borderRadius: 10 }}>
              <span style={{ fontSize: 13, fontWeight: 700, color: '#B5502E' }}>19-day streak</span>
              <span style={{ fontSize: 12, color: '#7A6B63' }}> · Best: 31 days</span>
            </div>
          </div>
        </div>
      </section>

      {/* ── LOGO BAR ─────────────────────────────────────────────────────── */}
      <div
        ref={r1.ref}
        className={`reveal ${r1.visible ? 'visible' : ''}`}
        style={{
          borderTop: '1px solid rgba(181,80,46,0.10)',
          borderBottom: '1px solid rgba(181,80,46,0.10)',
          padding: '22px 40px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 40,
          flexWrap: 'wrap',
          backgroundColor: '#F5F2EE',
        }}
      >
        <span style={{ fontSize: 12, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#7A6B63' }}>
          Used by candidates targeting
        </span>
        {['Google', 'Meta', 'Stripe', 'Airbnb', 'DeepMind', 'Notion'].map((co) => (
          <span
            key={co}
            style={{
              fontSize: 14,
              fontWeight: 700,
              color: '#4B3D37',
              opacity: 0.6,
              letterSpacing: '-0.01em',
              fontFamily: "'Fraunces', Georgia, serif",
            }}
          >
            {co}
          </span>
        ))}
      </div>

      {/* ── HOW IT WORKS ─────────────────────────────────────────────────── */}
      <section
        style={{
          padding: 'clamp(72px, 10vw, 120px) clamp(24px, 6vw, 80px)',
          maxWidth: 1100,
          margin: '0 auto',
        }}
      >
        <div
          ref={r2.ref}
          className={`reveal ${r2.visible ? 'visible' : ''}`}
          style={{ textAlign: 'center', marginBottom: 64 }}
        >
          <div
            style={{
              display: 'inline-block',
              fontSize: 11,
              fontWeight: 700,
              letterSpacing: '0.12em',
              textTransform: 'uppercase',
              color: '#B5502E',
              background: 'rgba(181,80,46,0.09)',
              padding: '5px 14px',
              borderRadius: 100,
              marginBottom: 20,
            }}
          >
            How it works
          </div>
          <h2
            style={{
              fontFamily: "'Fraunces', Georgia, serif",
              fontSize: 'clamp(2rem, 4vw, 3rem)',
              fontWeight: 700,
              color: '#1C1917',
              letterSpacing: '-0.02em',
              lineHeight: 1.15,
            }}
          >
            Prep that rebuilds itself
            <br />
            <em style={{ fontStyle: 'italic', color: '#B5502E' }}>around you.</em>
          </h2>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: 40,
          }}
        >
          {HOW_STEPS.map((step, i) => (
            <div
              key={step.n}
              ref={i === 0 ? r2.ref : undefined}
              className={`reveal reveal-d${i + 1} ${r2.visible ? 'visible' : ''}`}
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: 16,
              }}
            >
              <div
                style={{
                  width: 44,
                  height: 44,
                  borderRadius: 12,
                  background: 'linear-gradient(135deg, #B5502E 0%, #E0A458 100%)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                }}
              >
                <span
                  style={{
                    fontFamily: "'Fraunces', Georgia, serif",
                    fontSize: 16,
                    fontWeight: 700,
                    color: '#FAFAF8',
                    letterSpacing: '-0.01em',
                  }}
                >
                  {step.n}
                </span>
              </div>
              <h3
                style={{
                  fontFamily: "'Fraunces', Georgia, serif",
                  fontSize: 21,
                  fontWeight: 700,
                  color: '#1C1917',
                  margin: 0,
                  lineHeight: 1.25,
                }}
              >
                {step.title}
              </h3>
              <p
                style={{
                  fontSize: 15,
                  color: '#7A6B63',
                  lineHeight: 1.7,
                  margin: 0,
                }}
              >
                {step.body}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* ── FEATURES ─────────────────────────────────────────────────────── */}
      <section
        style={{
          background: '#F5F2EE',
          padding: 'clamp(72px, 10vw, 120px) clamp(24px, 6vw, 80px)',
        }}
      >
        <div
          ref={r3.ref}
          className={`reveal ${r3.visible ? 'visible' : ''}`}
          style={{ textAlign: 'center', marginBottom: 64, maxWidth: 600, margin: '0 auto 64px' }}
        >
          <div
            style={{
              display: 'inline-block',
              fontSize: 11,
              fontWeight: 700,
              letterSpacing: '0.12em',
              textTransform: 'uppercase',
              color: '#B5502E',
              background: 'rgba(181,80,46,0.09)',
              padding: '5px 14px',
              borderRadius: 100,
              marginBottom: 20,
            }}
          >
            Platform features
          </div>
          <h2
            style={{
              fontFamily: "'Fraunces', Georgia, serif",
              fontSize: 'clamp(1.9rem, 3.8vw, 2.8rem)',
              fontWeight: 700,
              color: '#1C1917',
              letterSpacing: '-0.02em',
              lineHeight: 1.15,
            }}
          >
            Six things that set this apart
            <br />
            <em style={{ fontStyle: 'italic', color: '#C97350' }}>from every other prep tool.</em>
          </h2>
        </div>

        {/* Magazine layout: 1 large + 2 medium + 1 large + 2 medium */}
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>

          {/* Row 1: large left + 2 stacked right */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gridTemplateRows: 'auto auto',
              gap: 20,
              marginBottom: 20,
            }}
          >
            {/* Large card */}
            <div
              className={`reveal ${r3.visible ? 'visible' : ''}`}
              style={{
                gridRow: '1 / 3',
                background: '#FFFFFF',
                borderRadius: 20,
                border: '1.5px solid rgba(181,80,46,0.12)',
                padding: 36,
                display: 'flex',
                flexDirection: 'column',
                gap: 20,
                boxShadow: '0 2px 16px rgba(0,0,0,0.04)',
              }}
            >
              <div
                style={{
                  width: 52,
                  height: 52,
                  borderRadius: 14,
                  background: 'rgba(181,80,46,0.10)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                {FEATURES[0].icon}
              </div>
              <div>
                <span
                  style={{
                    fontSize: 10,
                    fontWeight: 700,
                    letterSpacing: '0.12em',
                    textTransform: 'uppercase',
                    color: '#B5502E',
                  }}
                >
                  {FEATURES[0].tag}
                </span>
                <h3
                  style={{
                    fontFamily: "'Fraunces', Georgia, serif",
                    fontSize: 26,
                    fontWeight: 700,
                    color: '#1C1917',
                    margin: '8px 0 12px',
                    lineHeight: 1.2,
                  }}
                >
                  {FEATURES[0].title}
                </h3>
                <p style={{ fontSize: 15, color: '#7A6B63', lineHeight: 1.7, margin: 0 }}>
                  {FEATURES[0].desc}
                </p>
              </div>
              <div
                style={{
                  marginTop: 'auto',
                  padding: '16px 20px',
                  background: 'rgba(181,80,46,0.05)',
                  borderRadius: 12,
                  fontSize: 13,
                  color: '#4B3D37',
                  fontStyle: 'italic',
                  fontFamily: "'Fraunces', Georgia, serif",
                  lineHeight: 1.5,
                }}
              >
                "The question after my weak system design answer was harder and more targeted — exactly where I'd slipped up."
              </div>
            </div>

            {/* Two smaller cards stacked */}
            {[1, 2].map((fi, di) => (
              <div
                key={fi}
                className={`reveal reveal-d${di + 2} ${r3.visible ? 'visible' : ''}`}
                style={{
                  background: '#FFFFFF',
                  borderRadius: 20,
                  border: '1.5px solid rgba(181,80,46,0.12)',
                  padding: 28,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 14,
                  boxShadow: '0 2px 16px rgba(0,0,0,0.04)',
                }}
              >
                <div
                  style={{
                    width: 44,
                    height: 44,
                    borderRadius: 12,
                    background: 'rgba(181,80,46,0.08)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  {FEATURES[fi].icon}
                </div>
                <div>
                  <span
                    style={{
                      fontSize: 10,
                      fontWeight: 700,
                      letterSpacing: '0.12em',
                      textTransform: 'uppercase',
                      color: '#B5502E',
                    }}
                  >
                    {FEATURES[fi].tag}
                  </span>
                  <h3
                    style={{
                      fontFamily: "'Fraunces', Georgia, serif",
                      fontSize: 20,
                      fontWeight: 700,
                      color: '#1C1917',
                      margin: '6px 0 10px',
                      lineHeight: 1.25,
                    }}
                  >
                    {FEATURES[fi].title}
                  </h3>
                  <p style={{ fontSize: 14, color: '#7A6B63', lineHeight: 1.65, margin: 0 }}>
                    {FEATURES[fi].desc}
                  </p>
                </div>
              </div>
            ))}
          </div>

          {/* Row 2: 2 stacked left + large right */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gridTemplateRows: 'auto auto',
              gap: 20,
            }}
          >
            {[3, 4].map((fi, di) => (
              <div
                key={fi}
                className={`reveal reveal-d${di + 1} ${r3.visible ? 'visible' : ''}`}
                style={{
                  background: '#FFFFFF',
                  borderRadius: 20,
                  border: '1.5px solid rgba(181,80,46,0.12)',
                  padding: 28,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 14,
                  boxShadow: '0 2px 16px rgba(0,0,0,0.04)',
                }}
              >
                <div
                  style={{
                    width: 44,
                    height: 44,
                    borderRadius: 12,
                    background: 'rgba(181,80,46,0.08)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  {FEATURES[fi].icon}
                </div>
                <div>
                  <span
                    style={{
                      fontSize: 10,
                      fontWeight: 700,
                      letterSpacing: '0.12em',
                      textTransform: 'uppercase',
                      color: '#B5502E',
                    }}
                  >
                    {FEATURES[fi].tag}
                  </span>
                  <h3
                    style={{
                      fontFamily: "'Fraunces', Georgia, serif",
                      fontSize: 20,
                      fontWeight: 700,
                      color: '#1C1917',
                      margin: '6px 0 10px',
                      lineHeight: 1.25,
                    }}
                  >
                    {FEATURES[fi].title}
                  </h3>
                  <p style={{ fontSize: 14, color: '#7A6B63', lineHeight: 1.65, margin: 0 }}>
                    {FEATURES[fi].desc}
                  </p>
                </div>
              </div>
            ))}

            {/* Large card for feature 5 — Readiness Countdown */}
            <div
              className={`reveal reveal-d3 ${r3.visible ? 'visible' : ''}`}
              style={{
                gridRow: '1 / 3',
                background: 'linear-gradient(160deg, #1C1917 0%, #2E1F18 100%)',
                borderRadius: 20,
                border: '1.5px solid rgba(224,164,88,0.20)',
                padding: 36,
                display: 'flex',
                flexDirection: 'column',
                gap: 20,
                boxShadow: '0 2px 24px rgba(0,0,0,0.16)',
              }}
            >
              <div
                style={{
                  width: 52,
                  height: 52,
                  borderRadius: 14,
                  background: 'rgba(224,164,88,0.15)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <svg width="26" height="26" viewBox="0 0 22 22" fill="none">
                  <circle cx="11" cy="12" r="8" stroke="#E0A458" strokeWidth="1.6" />
                  <path d="M11 8v4l3 2" stroke="#E0A458" strokeWidth="1.6" strokeLinecap="round" />
                  <path d="M8 3h6" stroke="#C97350" strokeWidth="1.4" strokeLinecap="round" />
                </svg>
              </div>
              <div>
                <span
                  style={{
                    fontSize: 10,
                    fontWeight: 700,
                    letterSpacing: '0.12em',
                    textTransform: 'uppercase',
                    color: '#E0A458',
                  }}
                >
                  {FEATURES[5].tag}
                </span>
                <h3
                  style={{
                    fontFamily: "'Fraunces', Georgia, serif",
                    fontSize: 26,
                    fontWeight: 700,
                    color: '#FAFAF8',
                    margin: '8px 0 12px',
                    lineHeight: 1.2,
                  }}
                >
                  {FEATURES[5].title}
                </h3>
                <p style={{ fontSize: 15, color: 'rgba(250,250,248,0.68)', lineHeight: 1.7, margin: 0 }}>
                  {FEATURES[5].desc}
                </p>
              </div>
              {/* Mock countdown display */}
              <div style={{ marginTop: 'auto' }}>
                {[
                  { label: 'System Design', days: 4, pct: 62 },
                  { label: 'Behavioral', days: 2, pct: 84 },
                  { label: 'Coding', days: 1, pct: 91 },
                ].map((item) => (
                  <div key={item.label} style={{ marginBottom: 14 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                      <span style={{ fontSize: 12, color: 'rgba(250,250,248,0.72)' }}>{item.label}</span>
                      <span style={{ fontSize: 12, color: '#E0A458', fontWeight: 600 }}>{item.pct}%</span>
                    </div>
                    <div style={{ height: 4, borderRadius: 2, background: 'rgba(255,255,255,0.10)' }}>
                      <div
                        style={{
                          height: '100%',
                          width: `${item.pct}%`,
                          borderRadius: 2,
                          background: 'linear-gradient(90deg, #B5502E 0%, #E0A458 100%)',
                        }}
                      />
                    </div>
                  </div>
                ))}
                <div
                  style={{
                    marginTop: 20,
                    padding: '12px 16px',
                    background: 'rgba(224,164,88,0.12)',
                    borderRadius: 10,
                    fontSize: 13,
                    color: '#E0A458',
                    fontWeight: 600,
                  }}
                >
                  📅 Interview in 7 days — 3 topics to sharpen
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── TESTIMONIALS ─────────────────────────────────────────────────── */}
      <section
        style={{
          padding: 'clamp(72px, 10vw, 120px) clamp(24px, 6vw, 80px)',
          maxWidth: 1100,
          margin: '0 auto',
        }}
      >
        <div
          ref={r4.ref}
          className={`reveal ${r4.visible ? 'visible' : ''}`}
          style={{ textAlign: 'center', marginBottom: 60 }}
        >
          <h2
            style={{
              fontFamily: "'Fraunces', Georgia, serif",
              fontSize: 'clamp(1.8rem, 3.5vw, 2.6rem)',
              fontWeight: 700,
              color: '#1C1917',
              letterSpacing: '-0.02em',
            }}
          >
            Real people. Real offers.
          </h2>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
            gap: 24,
          }}
        >
          {TESTIMONIALS.map((t, i) => (
            <div
              key={t.name}
              className={`reveal reveal-d${i + 1} ${r4.visible ? 'visible' : ''}`}
              style={{
                background: '#FFFFFF',
                borderRadius: 18,
                border: '1.5px solid rgba(181,80,46,0.12)',
                padding: 28,
                display: 'flex',
                flexDirection: 'column',
                gap: 20,
                boxShadow: '0 2px 12px rgba(0,0,0,0.04)',
              }}
            >
              {/* Quote mark */}
              <span
                style={{
                  fontFamily: "'Fraunces', Georgia, serif",
                  fontSize: 56,
                  color: 'rgba(181,80,46,0.18)',
                  lineHeight: 0.8,
                  display: 'block',
                }}
              >
                "
              </span>
              <p
                style={{
                  fontFamily: "'Fraunces', Georgia, serif",
                  fontSize: 16,
                  color: '#1C1917',
                  lineHeight: 1.7,
                  margin: 0,
                  fontStyle: 'italic',
                  fontWeight: 400,
                }}
              >
                {t.quote}
              </p>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 'auto' }}>
                <div
                  style={{
                    width: 36,
                    height: 36,
                    borderRadius: '50%',
                    background: 'linear-gradient(135deg, #B5502E 0%, #E0A458 100%)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                    fontSize: 12,
                    fontWeight: 700,
                    color: '#FAFAF8',
                  }}
                >
                  {t.initials}
                </div>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: '#1C1917' }}>{t.name}</div>
                  <div style={{ fontSize: 12, color: '#7A6B63' }}>{t.role}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── CTA ──────────────────────────────────────────────────────────── */}
      <section
        style={{
          background: 'linear-gradient(135deg, #1C1917 0%, #2E1F18 50%, #3D2419 100%)',
          padding: 'clamp(72px, 10vw, 100px) clamp(24px, 6vw, 80px)',
          textAlign: 'center',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        <div
          aria-hidden
          style={{
            position: 'absolute',
            inset: 0,
            background:
              'radial-gradient(ellipse at 60% 20%, rgba(201,115,80,0.22) 0%, transparent 55%), radial-gradient(ellipse at 30% 80%, rgba(224,164,88,0.15) 0%, transparent 50%)',
          }}
        />
        <div
          ref={r5.ref}
          className={`reveal ${r5.visible ? 'visible' : ''}`}
          style={{ position: 'relative', zIndex: 1 }}
        >
          <h2
            style={{
              fontFamily: "'Fraunces', Georgia, serif",
              fontSize: 'clamp(2rem, 4.5vw, 3.4rem)',
              fontWeight: 700,
              color: '#FAFAF8',
              letterSpacing: '-0.02em',
              lineHeight: 1.1,
              marginBottom: 20,
            }}
          >
            Your next interview is closer
            <br />
            <em style={{ fontStyle: 'italic', color: '#E0A458' }}>than you think.</em>
          </h2>
          <p
            style={{
              fontSize: 'clamp(1rem, 1.8vw, 1.1rem)',
              color: 'rgba(250,250,248,0.65)',
              maxWidth: 480,
              margin: '0 auto 40px',
              lineHeight: 1.7,
            }}
          >
            Start in two minutes. Upload your resume, set your target company, and let Coachline do the rest.
          </p>
          <button
            onClick={goToApp}
            style={{
              background: 'linear-gradient(135deg, #B5502E 0%, #E0A458 100%)',
              border: 'none',
              cursor: 'pointer',
              color: '#FAFAF8',
              fontSize: 15,
              fontWeight: 700,
              padding: '15px 36px',
              borderRadius: 100,
              fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif",
              boxShadow: '0 4px 24px rgba(181,80,46,0.50)',
              letterSpacing: '0.01em',
              transition: 'transform 0.15s ease, box-shadow 0.15s ease',
            }}
            onMouseEnter={(e) => {
              ;(e.currentTarget as HTMLButtonElement).style.transform = 'translateY(-2px)'
              ;(e.currentTarget as HTMLButtonElement).style.boxShadow =
                '0 8px 32px rgba(181,80,46,0.60)'
            }}
            onMouseLeave={(e) => {
              ;(e.currentTarget as HTMLButtonElement).style.transform = 'translateY(0)'
              ;(e.currentTarget as HTMLButtonElement).style.boxShadow =
                '0 4px 24px rgba(181,80,46,0.50)'
            }}
          >
            Start Your Journey →
          </button>
        </div>
      </section>

      {/* ── FOOTER ───────────────────────────────────────────────────────── */}
      <footer
        style={{
          background: '#F5F2EE',
          borderTop: '1px solid rgba(181,80,46,0.10)',
          padding: '40px clamp(24px, 6vw, 80px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 20,
        }}
      >
        <span
          style={{
            fontFamily: "'Fraunces', Georgia, serif",
            fontSize: 16,
            fontWeight: 700,
            color: '#1C1917',
            letterSpacing: '-0.02em',
          }}
        >
          Coachline
        </span>
        <span style={{ fontSize: 13, color: '#7A6B63' }}>
          © {new Date().getFullYear()} Coachline. Built for the focused few.
        </span>
        <div style={{ display: 'flex', gap: 24 }}>
          {['Privacy', 'Terms', 'Contact'].map((l) => (
            <a
              key={l}
              href="#"
              onClick={(e) => e.preventDefault()}
              style={{ fontSize: 13, color: '#7A6B63', textDecoration: 'none', fontWeight: 500 }}
            >
              {l}
            </a>
          ))}
        </div>
      </footer>
    </div>
  )
}
