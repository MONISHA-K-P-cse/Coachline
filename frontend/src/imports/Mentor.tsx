import { useState, useRef, useEffect } from 'react'
import { Nav } from '../components/Nav'
import { OrbitLoader } from '../components/OrbitLoader'
import * as api from '../lib/apiClient'

type Page = 'landing' | 'login' | 'register' | 'onboarding' | 'workspace' | 'roadmap' | 'interview' | 'notes' | 'mastery' | 'mentor'
interface Props { navigate: (p: Page) => void }

// ─── AI Mentor Brain Visualization (purely decorative "thinking" indicator) ──

const BRAIN_NODES = [
  { id: 'ai',        label: 'AI Mentor', x: 160, y: 72, isCore: true },
  { id: 'resume',    label: 'Resume',     x:  52, y:  28, isCore: false },
  { id: 'roadmap',   label: 'Roadmap',    x: 268, y:  28, isCore: false },
  { id: 'interview', label: 'Interview',  x: 310, y:  92, isCore: false },
  { id: 'galaxy',    label: 'Galaxy',     x: 268, y: 148, isCore: false },
  { id: 'notes',     label: 'Notes',      x:  52, y: 148, isCore: false },
  { id: 'replay',    label: 'Replay',     x:  10, y:  92, isCore: false },
]

const BRAIN_EDGES = [
  { from: 'ai', to: 'resume' }, { from: 'ai', to: 'roadmap' }, { from: 'ai', to: 'interview' },
  { from: 'ai', to: 'galaxy' }, { from: 'ai', to: 'notes' }, { from: 'ai', to: 'replay' },
]

function brainArc(x1: number, y1: number, x2: number, y2: number) {
  const mx = (x1 + x2) / 2, my = (y1 + y2) / 2
  const dx = x2 - x1, dy = y2 - y1
  return `M ${x1} ${y1} Q ${mx - dy * 0.15} ${my + dx * 0.15} ${x2} ${y2}`
}

function AIMentorBrain({ thinking }: { thinking: boolean }) {
  const nodeMap = Object.fromEntries(BRAIN_NODES.map((n) => [n.id, n]))
  return (
    <div style={{ background: 'linear-gradient(160deg, #1C1917 0%, #261A13 100%)', borderRadius: '18px 18px 0 0', padding: '14px 20px 10px', position: 'relative', overflow: 'hidden' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, position: 'relative' }}>
        <svg viewBox="0 0 320 176" style={{ width: 200, flexShrink: 0 }}>
          <defs>
            <filter id="brain-glow-core" x="-80%" y="-80%" width="260%" height="260%"><feGaussianBlur stdDeviation="8" result="blur" /><feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
            <filter id="brain-glow-sat" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="4" result="blur" /><feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
          </defs>
          {BRAIN_EDGES.map((e) => {
            const na = nodeMap[e.from], nb = nodeMap[e.to]
            return (
              <g key={`${e.from}-${e.to}`}>
                <path d={brainArc(na.x, na.y, nb.x, nb.y)} fill="none" stroke={thinking ? 'rgba(224,164,88,0.55)' : 'rgba(255,255,255,0.14)'} strokeWidth={thinking ? 1.5 : 0.8} />
                {thinking && (
                  <path d={brainArc(na.x, na.y, nb.x, nb.y)} fill="none" stroke="rgba(224,164,88,0.9)" strokeWidth="1.5" strokeDasharray="4 8">
                    <animate attributeName="stroke-dashoffset" from="0" to="-24" dur="0.8s" repeatCount="indefinite" />
                  </path>
                )}
              </g>
            )
          })}
          {BRAIN_NODES.filter((n) => !n.isCore).map((node) => (
            <g key={node.id} transform={`translate(${node.x},${node.y})`}>
              <circle r={thinking ? 10 : 8} fill="rgba(201,115,80,0.75)" filter="url(#brain-glow-sat)">
                {thinking && <animate attributeName="opacity" values="0.7;1;0.7" dur="1.6s" repeatCount="indefinite" />}
              </circle>
              <text textAnchor="middle" dy="4" fill="#FAFAF8" fontSize="6.5" fontWeight="700" fontFamily="'Plus Jakarta Sans', sans-serif">{node.label.charAt(0)}</text>
            </g>
          ))}
          {(() => {
            const core = nodeMap['ai']
            return (
              <g transform={`translate(${core.x},${core.y})`}>
                {thinking && (
                  <circle r="28" fill="none" stroke="rgba(224,164,88,0.4)" strokeWidth="1">
                    <animate attributeName="r" values="20;30;20" dur="2s" repeatCount="indefinite" />
                    <animate attributeName="opacity" values="0.4;0;0.4" dur="2s" repeatCount="indefinite" />
                  </circle>
                )}
                <circle r="22" fill="rgba(181,80,46,0.25)" filter="url(#brain-glow-core)" />
                <circle r="16" fill="#B5502E" filter="url(#brain-glow-core)" />
                <text textAnchor="middle" dy="4" fill="#FAFAF8" fontSize="9" fontWeight="700" fontFamily="'Plus Jakarta Sans', sans-serif">AI</text>
              </g>
            )
          })()}
        </svg>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <div style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 15, fontWeight: 700, color: '#FAFAF8' }}>Your Mentor</div>
            {thinking && <span style={{ fontSize: 10, color: '#E0A458', fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase' }}>Thinking</span>}
          </div>
          <div style={{ fontSize: 11, color: 'rgba(250,250,248,0.55)', lineHeight: 1.5 }}>
            Grounded in interview prep reference material via RAG retrieval.
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Main component ──────────────────────────────────────────────────────────

export default function Mentor({ navigate }: Props) {
  const [messages, setMessages] = useState<api.MentorMessage[]>([])
  const [loading, setLoading] = useState(true)
  const [input, setInput] = useState('')
  const [thinking, setThinking] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    api.getMentorHistory().then(setMessages).finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, thinking])

  const send = async () => {
    const text = input.trim()
    if (!text) return
    setInput('')
    setError(null)
    setThinking(true)
    try {
      const [userMsg, mentorMsg] = await api.sendMentorMessage(text)
      setMessages((p) => [...p, userMsg, mentorMsg])
    } catch (err) {
      setError(err instanceof api.ApiError ? err.message : 'The mentor is temporarily unavailable.')
    } finally {
      setThinking(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#FAFAF8', fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif", display: 'flex', flexDirection: 'column' }}>
      <Nav page="mentor" navigate={navigate} />

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', maxWidth: 720, margin: '0 auto', width: '100%', padding: '0 clamp(16px, 4vw, 32px)', height: 'calc(100vh - 64px)' }}>
        <div style={{ flexShrink: 0, marginTop: 20, borderRadius: 18, overflow: 'hidden', border: '1.5px solid rgba(181,80,46,0.12)', boxShadow: '0 2px 12px rgba(0,0,0,0.06)' }}>
          <AIMentorBrain thinking={thinking} />
          <div style={{ borderTop: '1px solid rgba(181,80,46,0.10)' }} />
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: '20px 0', display: 'flex', flexDirection: 'column', gap: 20 }}>
          {loading ? (
            <OrbitLoader label="Loading conversation…" size={56} />
          ) : messages.length === 0 ? (
            <p style={{ textAlign: 'center', color: '#7A6B63', fontSize: 13, marginTop: 40 }}>
              Ask your mentor anything about interview prep — it has access to the same reference material as your notes and questions.
            </p>
          ) : (
            messages.map((msg) => (
              <div key={msg.id} style={{ display: 'flex', flexDirection: msg.sender === 'user' ? 'row-reverse' : 'row', alignItems: 'flex-start', gap: 12 }}>
                {msg.sender === 'mentor' && (
                  <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'linear-gradient(135deg, #B5502E, #C97350)', flexShrink: 0, marginTop: 2 }} />
                )}
                <div
                  style={{
                    maxWidth: '80%',
                    padding: '14px 18px',
                    borderRadius: msg.sender === 'user' ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
                    background: msg.sender === 'user' ? 'linear-gradient(135deg, #B5502E, #C97350)' : '#FFFFFF',
                    color: msg.sender === 'user' ? '#FAFAF8' : '#1C1917',
                    fontSize: 14,
                    lineHeight: 1.7,
                    border: msg.sender === 'mentor' ? '1.5px solid rgba(181,80,46,0.12)' : 'none',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
                    fontFamily: msg.sender === 'mentor' ? "'Fraunces', Georgia, serif" : "'Plus Jakarta Sans', sans-serif",
                    fontStyle: msg.sender === 'mentor' ? 'italic' : 'normal',
                    whiteSpace: 'pre-wrap',
                  }}
                >
                  {msg.message}
                </div>
              </div>
            ))
          )}
          {thinking && (
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
              <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'linear-gradient(135deg, #B5502E, #C97350)', flexShrink: 0 }} />
              <div style={{ background: '#FFFFFF', border: '1.5px solid rgba(181,80,46,0.12)', borderRadius: '18px 18px 18px 4px', padding: '0 4px', boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}>
                <OrbitLoader label="Thinking…" size={48} />
              </div>
            </div>
          )}
          {error && (
            <div style={{ padding: '10px 16px', background: 'rgba(181,80,46,0.08)', borderRadius: 10, fontSize: 12.5, color: '#B5502E', alignSelf: 'center' }}>{error}</div>
          )}
          <div ref={bottomRef} />
        </div>

        <div style={{ padding: '16px 0 24px', flexShrink: 0, borderTop: '1px solid rgba(181,80,46,0.08)' }}>
          <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
              placeholder="Reply to your mentor…"
              rows={2}
              style={{ flex: 1, padding: '12px 16px', borderRadius: 14, border: '1.5px solid rgba(181,80,46,0.22)', background: '#FFFFFF', fontSize: 14, color: '#1C1917', lineHeight: 1.6, fontFamily: "'Plus Jakarta Sans', sans-serif", resize: 'none', outline: 'none', boxSizing: 'border-box' }}
            />
            <button
              onClick={send}
              disabled={!input.trim() || thinking}
              style={{ background: input.trim() && !thinking ? 'linear-gradient(135deg, #B5502E, #C97350)' : 'rgba(181,80,46,0.20)', border: 'none', cursor: input.trim() && !thinking ? 'pointer' : 'not-allowed', width: 46, height: 46, borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}
            >
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                <path d="M3 9h12M9 4l6 5-6 5" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
          </div>
          <p style={{ fontSize: 11, color: '#7A6B63', margin: '8px 0 0', textAlign: 'center' }}>Enter to send · Shift+Enter for new line</p>
        </div>
      </div>
    </div>
  )
}
