import { useState, useEffect } from 'react'
import { Nav } from '../components/Nav'
import { OrbitLoader } from '../components/OrbitLoader'
import * as api from '../lib/apiClient'
import { ApiError } from '../lib/apiClient'

type Page = 'landing' | 'login' | 'register' | 'onboarding' | 'workspace' | 'roadmap' | 'interview' | 'notes' | 'mastery' | 'mentor'
interface Props { navigate: (p: Page) => void }
type NodeStatus = 'mastered' | 'learning' | 'needs-practice'

interface GNode { id: string; label: string; x: number; y: number; status: NodeStatus; mastery: number; needsRegeneration: boolean; updatedAt: string }

const STATUS: Record<NodeStatus, { fill: string; glow: string; badge: string; badgeBg: string; label: string }> = {
  mastered:         { fill: '#15803d', glow: 'rgba(21,128,61,0.55)',  badge: '#15803d', badgeBg: 'rgba(21,128,61,0.12)',  label: 'Mastered' },
  learning:         { fill: '#C97350', glow: 'rgba(201,115,80,0.55)', badge: '#C97350', badgeBg: 'rgba(201,115,80,0.12)', label: 'Learning' },
  'needs-practice': { fill: '#B5502E', glow: 'rgba(181,80,46,0.55)',  badge: '#B5502E', badgeBg: 'rgba(181,80,46,0.12)',  label: 'Needs Practice' },
}

const VW = 700, VH = 420

function statusFor(score: number): NodeStatus {
  if (score >= 70) return 'mastered'
  if (score >= 40) return 'learning'
  return 'needs-practice'
}

function layout(topics: api.TopicMasteryEntry[]): GNode[] {
  const cx = VW / 2, cy = VH / 2, r = Math.min(VW, VH) / 2 - 70
  return topics.map((t, i) => {
    const angle = (i / Math.max(topics.length, 1)) * Math.PI * 2 - Math.PI / 2
    return {
      id: t.topic,
      label: t.topic,
      x: cx + Math.cos(angle) * r,
      y: cy + Math.sin(angle) * r,
      status: statusFor(t.mastery_score),
      mastery: Math.round(t.mastery_score),
      needsRegeneration: t.needs_regeneration,
      updatedAt: t.updated_at,
    }
  })
}

export default function Mastery({ navigate }: Props) {
  const [topics, setTopics] = useState<api.TopicMasteryEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [hovered, setHovered] = useState<string | null>(null)
  const [selected, setSelected] = useState<GNode | null>(null)
  const [diff, setDiff] = useState<Awaited<ReturnType<typeof api.getReplayDiff>> | null | 'none' | 'loading'>(null)

  useEffect(() => {
    api.getTopicMastery().then(setTopics).finally(() => setLoading(false))
  }, [])

  const nodes = layout(topics)

  const selectNode = async (n: GNode) => {
    setSelected(n)
    setDiff('loading')
    try {
      const d = await api.getReplayDiff(n.id)
      setDiff(d as Awaited<ReturnType<typeof api.getReplayDiff>>)
    } catch (err) {
      setDiff(err instanceof ApiError && err.status === 404 ? 'none' : 'none')
    }
  }

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', backgroundColor: '#FAFAF8' }}>
        <Nav page="mastery" navigate={navigate} />
        <OrbitLoader label="Loading your mastery map…" size={72} />
      </div>
    )
  }

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#FAFAF8', fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif" }}>
      <Nav page="mastery" navigate={navigate} />
      <div style={{ maxWidth: 1140, margin: '0 auto', padding: '32px clamp(16px, 4vw, 48px) 60px' }}>

        <div style={{ marginBottom: 24 }}>
          <p style={{ fontSize: 13, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: '#B5502E', marginBottom: 6 }}>
            Knowledge Galaxy
          </p>
          <h1 style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 'clamp(1.8rem, 3vw, 2.4rem)', fontWeight: 700, color: '#1C1917', letterSpacing: '-0.02em', margin: '0 0 8px' }}>
            Your mastery constellation.
          </h1>
          <p style={{ fontSize: 14, color: '#7A6B63', margin: 0, lineHeight: 1.6 }}>
            Every topic your mock interviews have touched, scored from your real answers.
          </p>
        </div>

        {topics.length === 0 ? (
          <div style={{ background: '#F5F2EE', borderRadius: 20, border: '1.5px dashed rgba(181,80,46,0.22)', padding: '60px 24px', textAlign: 'center' }}>
            <p style={{ fontSize: 14, color: '#7A6B63', margin: '0 0 16px' }}>No topics tracked yet - complete a mock interview to start building your mastery map.</p>
            <button onClick={() => navigate('interview')} style={{ background: 'linear-gradient(135deg, #B5502E, #C97350)', border: 'none', cursor: 'pointer', color: '#FAFAF8', fontSize: 13, fontWeight: 700, padding: '10px 22px', borderRadius: 100, fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
              Start a Mock Interview →
            </button>
          </div>
        ) : (
          <>
            <div style={{ display: 'flex', gap: 22, marginBottom: 20, flexWrap: 'wrap' }}>
              {(Object.entries(STATUS) as [NodeStatus, typeof STATUS[NodeStatus]][]).map(([k, v]) => (
                <div key={k} style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                  <div style={{ width: 10, height: 10, borderRadius: '50%', background: v.fill, boxShadow: `0 0 7px ${v.glow}` }} />
                  <span style={{ fontSize: 12, color: '#7A6B63', fontWeight: 500 }}>{v.label}</span>
                </div>
              ))}
              <div style={{ marginLeft: 'auto', fontSize: 12, color: '#7A6B63', fontStyle: 'italic' }}>
                {nodes.filter((n) => n.status === 'mastered').length} of {nodes.length} topics mastered
              </div>
            </div>

            <div style={{ display: 'flex', gap: 20, alignItems: 'flex-start' }}>
              <div style={{ flex: 1, minWidth: 0, background: 'linear-gradient(160deg, #1C1917 0%, #261A13 55%, #1E1310 100%)', borderRadius: 24, border: '1.5px solid rgba(224,164,88,0.15)', overflow: 'hidden', boxShadow: '0 6px 40px rgba(0,0,0,0.22)' }}>
                <svg viewBox={`0 0 ${VW} ${VH}`} style={{ width: '100%', display: 'block' }} aria-label="Knowledge Galaxy">
                  <defs>
                    {(['green', 'orange', 'red'] as const).map((name) => (
                      <filter key={name} id={`glow-${name}`} x="-60%" y="-60%" width="220%" height="220%">
                        <feGaussianBlur stdDeviation={name === 'green' ? 7 : 6} result="blur" />
                        <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
                      </filter>
                    ))}
                  </defs>
                  {nodes.map((node) => {
                    const s = STATUS[node.status]
                    const isHov = hovered === node.id
                    const isSel = selected?.id === node.id
                    const filterId = node.status === 'mastered' ? 'glow-green' : node.status === 'learning' ? 'glow-orange' : 'glow-red'
                    const scale = isSel ? 1.45 : isHov ? 1.3 : 1
                    return (
                      <g key={node.id} transform={`translate(${node.x},${node.y})`} style={{ cursor: 'pointer' }} onMouseEnter={() => setHovered(node.id)} onMouseLeave={() => setHovered(null)} onClick={() => selectNode(node)}>
                        {isSel && (
                          <circle r="28" fill="none" stroke={s.fill} strokeWidth="1.2" opacity="0.5">
                            <animate attributeName="r" values="22;34;22" dur="2.8s" repeatCount="indefinite" />
                            <animate attributeName="opacity" values="0.5;0;0.5" dur="2.8s" repeatCount="indefinite" />
                          </circle>
                        )}
                        <circle r="18" fill={s.glow} opacity={isHov || isSel ? 0.55 : 0.28} filter={`url(#${filterId})`} />
                        <g style={{ transform: `scale(${scale})`, transformOrigin: '0 0' }}>
                          <circle r="13" fill={s.fill} filter={`url(#${filterId})`} />
                          {(isHov || isSel) && (
                            <text textAnchor="middle" dy="4.5" fill="#FAFAF8" fontSize="9.5" fontWeight="800" fontFamily="'Fraunces', Georgia, serif">{node.mastery}%</text>
                          )}
                        </g>
                        <text dy={isHov || isSel ? 30 : 26} textAnchor="middle" fill={isHov || isSel ? 'rgba(250,250,248,0.96)' : 'rgba(250,250,248,0.72)'} fontSize={isHov || isSel ? 11.5 : 10} fontWeight={isHov || isSel ? 700 : 500} fontFamily="'Plus Jakarta Sans', system-ui, sans-serif">
                          {node.label}
                        </text>
                      </g>
                    )
                  })}
                </svg>
              </div>

              {selected ? (
                <div style={{ width: 308, flexShrink: 0, background: '#FFFFFF', borderRadius: 20, border: '1.5px solid rgba(181,80,46,0.14)', boxShadow: '0 6px 32px rgba(0,0,0,0.10)', overflow: 'hidden' }}>
                  <div style={{ background: 'linear-gradient(160deg, #1C1917 0%, #2E1F18 100%)', padding: '20px 20px 18px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                      <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.10em', textTransform: 'uppercase', color: STATUS[selected.status].badge, background: STATUS[selected.status].badgeBg, padding: '3px 10px', borderRadius: 100 }}>
                        {STATUS[selected.status].label}
                      </span>
                      <button onClick={() => setSelected(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'rgba(250,250,248,0.45)', fontSize: 20, lineHeight: 1, padding: 0 }}>×</button>
                    </div>
                    <div style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 22, fontWeight: 700, color: '#FAFAF8', marginBottom: 10 }}>{selected.label}</div>
                    <div style={{ height: 5, borderRadius: 3, background: 'rgba(255,255,255,0.12)', marginBottom: 10 }}>
                      <div style={{ height: '100%', width: `${selected.mastery}%`, borderRadius: 3, background: `linear-gradient(90deg, ${STATUS[selected.status].fill}, #E0A458)` }} />
                    </div>
                    <div style={{ fontSize: 12, color: 'rgba(250,250,248,0.55)' }}>
                      Mastery <span style={{ color: '#E0A458', fontWeight: 700 }}>{selected.mastery}%</span> · Updated {new Date(selected.updatedAt).toLocaleDateString()}
                    </div>
                  </div>

                  <div style={{ padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: 16 }}>
                    {selected.needsRegeneration && (
                      <div style={{ padding: '10px 14px', background: 'rgba(181,80,46,0.07)', borderRadius: 10, fontSize: 12, color: '#B5502E' }}>
                        Flagged for regeneration - a fresh note for this topic should already be in Notes.
                      </div>
                    )}

                    <div>
                      <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.10em', textTransform: 'uppercase', color: '#7A6B63', marginBottom: 8 }}>Replay Diff</div>
                      {diff === 'loading' && <p style={{ fontSize: 12.5, color: '#7A6B63' }}>Loading…</p>}
                      {diff === 'none' && <p style={{ fontSize: 12.5, color: '#7A6B63' }}>Only tracked from live interview answers - no attempts recorded for this topic yet.</p>}
                      {diff && diff !== 'loading' && diff !== 'none' && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                          <div style={{ background: '#FFF5F0', borderRadius: 12, padding: '11px 13px', border: '1px solid rgba(181,80,46,0.14)' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                              <span style={{ fontSize: 10, fontWeight: 700, color: '#B5502E', opacity: 0.65, textTransform: 'uppercase' }}>First attempt</span>
                              <span style={{ fontSize: 15, fontWeight: 800, color: '#B5502E', fontFamily: "'Fraunces', Georgia, serif" }}>{Math.round(diff.earliest.score)}</span>
                            </div>
                            <p style={{ fontSize: 11.5, color: '#7A6B63', margin: 0 }}>{diff.earliest.feedback || 'No feedback recorded.'}</p>
                          </div>
                          {diff.attempt_count > 1 && (
                            <div style={{ background: 'rgba(181,80,46,0.07)', borderRadius: 12, padding: '11px 13px', border: '1.5px solid rgba(181,80,46,0.26)' }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                                <span style={{ fontSize: 10, fontWeight: 700, color: '#B5502E', opacity: 0.65, textTransform: 'uppercase' }}>Latest attempt</span>
                                <span style={{ fontSize: 15, fontWeight: 800, color: '#B5502E', fontFamily: "'Fraunces', Georgia, serif" }}>{Math.round(diff.latest.score)}</span>
                              </div>
                              <p style={{ fontSize: 11.5, color: '#4B3D37', margin: 0 }}>{diff.latest.feedback || 'No feedback recorded.'}</p>
                              {diff.score_delta != null && (
                                <p style={{ fontSize: 11.5, fontWeight: 700, color: diff.score_delta >= 0 ? '#15803d' : '#B5502E', margin: '8px 0 0' }}>
                                  {diff.score_delta >= 0 ? '+' : ''}{diff.score_delta} pts since first attempt
                                </p>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>

                    <button onClick={() => navigate('interview')} style={{ background: 'linear-gradient(135deg, #B5502E, #C97350)', border: 'none', cursor: 'pointer', color: '#FAFAF8', fontSize: 13, fontWeight: 700, padding: '11px 0', borderRadius: 10, fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
                      Practice this topic →
                    </button>
                  </div>
                </div>
              ) : (
                <div style={{ width: 308, flexShrink: 0, background: '#F5F2EE', borderRadius: 20, border: '1.5px dashed rgba(181,80,46,0.22)', padding: '40px 24px', textAlign: 'center' }}>
                  <p style={{ fontSize: 13, color: '#7A6B63', lineHeight: 1.6, margin: 0 }}>
                    Click any node in the galaxy to see mastery details and your Replay Diff.
                  </p>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
