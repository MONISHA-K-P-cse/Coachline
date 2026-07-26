import { useState } from 'react'
import { Nav } from '../components/Nav'

type Page = 'landing' | 'login' | 'register' | 'onboarding' | 'workspace' | 'roadmap' | 'interview' | 'notes' | 'mastery' | 'mentor'
interface Props { navigate: (p: Page) => void }

const topics = [
  { category: 'System Design', items: [
    { name: 'Caching & CDN', status: 'mastered', days: 0 },
    { name: 'Load Balancing', status: 'mastered', days: 0 },
    { name: 'Rate Limiting', status: 'in-progress', days: 2 },
    { name: 'Consensus (Raft/Paxos)', status: 'weak', days: 4 },
    { name: 'Distributed Transactions', status: 'not-started', days: 5 },
  ]},
  { category: 'Coding', items: [
    { name: 'Dynamic Programming', status: 'in-progress', days: 1 },
    { name: 'Graph Algorithms', status: 'mastered', days: 0 },
    { name: 'Tree Problems', status: 'weak', days: 3 },
    { name: 'Sliding Window', status: 'mastered', days: 0 },
  ]},
  { category: 'Behavioral', items: [
    { name: 'Conflict Resolution', status: 'mastered', days: 0 },
    { name: 'Ownership & Impact', status: 'in-progress', days: 1 },
    { name: 'Cross-team Influence', status: 'weak', days: 3 },
  ]},
]

const statusMeta: Record<string, { label: string; color: string; bg: string }> = {
  mastered:     { label: 'Mastered',    color: '#15803d', bg: 'rgba(21,128,61,0.09)' },
  'in-progress':{ label: 'In Progress', color: '#B5502E', bg: 'rgba(181,80,46,0.09)' },
  weak:         { label: 'Weak',        color: '#c2410c', bg: 'rgba(194,65,12,0.09)' },
  'not-started':{ label: 'Not Started', color: '#7A6B63', bg: 'rgba(122,107,99,0.09)' },
}

export default function Roadmap({ navigate }: Props) {
  const [expanded, setExpanded] = useState<string | null>('System Design')

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#FAFAF8', fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif" }}>
      <Nav page="roadmap" navigate={navigate} />
      <div style={{ maxWidth: 800, margin: '0 auto', padding: '40px clamp(16px, 4vw, 48px)' }}>
        <p style={{ fontSize: 13, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: '#B5502E', marginBottom: 8 }}>Study plan</p>
        <h1 style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 'clamp(1.8rem, 3vw, 2.4rem)', fontWeight: 700, color: '#1C1917', letterSpacing: '-0.02em', margin: '0 0 8px' }}>Your Roadmap</h1>
        <p style={{ fontSize: 15, color: '#7A6B63', margin: '0 0 36px', lineHeight: 1.6 }}>Recalculates daily based on your performance and interview date.</p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {topics.map((group) => (
            <div key={group.category} style={{ background: '#FFFFFF', borderRadius: 18, border: '1.5px solid rgba(181,80,46,0.12)', overflow: 'hidden', boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }}>
              <button
                onClick={() => setExpanded(expanded === group.category ? null : group.category)}
                style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '18px 24px', background: 'none', border: 'none', cursor: 'pointer', fontFamily: "'Plus Jakarta Sans', sans-serif" }}
              >
                <span style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 17, fontWeight: 700, color: '#1C1917' }}>{group.category}</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <span style={{ fontSize: 12, color: '#7A6B63' }}>
                    {group.items.filter(i => i.status === 'mastered').length}/{group.items.length} mastered
                  </span>
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" style={{ transform: expanded === group.category ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s ease' }}>
                    <path d="M4 6l4 4 4-4" stroke="#7A6B63" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </div>
              </button>
              {expanded === group.category && (
                <div style={{ borderTop: '1px solid rgba(181,80,46,0.08)', padding: '8px 16px 16px' }}>
                  {group.items.map((item) => {
                    const meta = statusMeta[item.status]
                    return (
                      <div key={item.name} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 8px', borderBottom: '1px solid rgba(181,80,46,0.06)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                          <div style={{ width: 7, height: 7, borderRadius: '50%', background: meta.color, flexShrink: 0 }} />
                          <span style={{ fontSize: 14, color: '#1C1917' }}>{item.name}</span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                          {item.days > 0 && (
                            <span style={{ fontSize: 11, color: '#7A6B63' }}>{item.days}d to focus</span>
                          )}
                          <span style={{ fontSize: 11, fontWeight: 600, color: meta.color, background: meta.bg, padding: '3px 9px', borderRadius: 100 }}>
                            {meta.label}
                          </span>
                          <button
                            onClick={() => navigate('interview')}
                            style={{ background: 'none', border: '1px solid rgba(181,80,46,0.25)', borderRadius: 8, cursor: 'pointer', padding: '4px 10px', fontSize: 11, fontWeight: 600, color: '#B5502E', fontFamily: "'Plus Jakarta Sans', sans-serif" }}
                          >
                            Practice
                          </button>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
