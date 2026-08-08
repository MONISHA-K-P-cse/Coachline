import { useState, useEffect } from 'react'
import { Nav } from '../components/Nav'
import { OrbitLoader } from '../components/OrbitLoader'
import * as api from '../lib/apiClient'
import { ApiError } from '../lib/apiClient'
import { motion, AnimatePresence } from 'framer-motion'
import { Compass, Sparkles, TrendingUp, AlertTriangle, Play, X, RotateCw } from 'lucide-react'

type Page = 'landing' | 'login' | 'register' | 'onboarding' | 'workspace' | 'roadmap' | 'interview' | 'notes' | 'mastery' | 'mentor'
interface Props { navigate: (p: Page) => void }
type NodeStatus = 'mastered' | 'learning' | 'needs-practice'

interface GNode { id: string; label: string; x: number; y: number; status: NodeStatus; mastery: number; needsRegeneration: boolean; updatedAt: string }

const STATUS: Record<NodeStatus, { fill: string; glow: string; badge: string; label: string }> = {
  mastered:         { fill: '#22c55e', glow: 'rgba(34,197,94,0.4)',  badge: 'bg-green-500/10 text-green-500',  label: 'Mastered' },
  learning:         { fill: '#eab308', glow: 'rgba(234,179,8,0.4)',  badge: 'bg-yellow-500/10 text-yellow-500', label: 'Learning' },
  'needs-practice': { fill: '#ef4444', glow: 'rgba(239,68,68,0.4)',  badge: 'bg-red-500/10 text-red-500',  label: 'Needs Practice' },
}

const VW = 720, VH = 460

function statusFor(score: number): NodeStatus {
  if (score >= 70) return 'mastered'
  if (score >= 40) return 'learning'
  return 'needs-practice'
}

function layout(topics: api.TopicMasteryEntry[]): GNode[] {
  const cx = VW / 2, cy = VH / 2, r = Math.min(VW, VH) / 2 - 80
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

function curvePath(x1: number, y1: number, x2: number, y2: number) {
  const mx = (x1 + x2) / 2, my = (y1 + y2) / 2
  const dx = x2 - x1, dy = y2 - y1
  const px = mx - dy * 0.18
  const py = my + dx * 0.18
  return `M ${x1} ${y1} Q ${px} ${py} ${x2} ${y2}`
}

const MOCK_TOPICS: api.TopicMasteryEntry[] = [
  { topic: 'System Design', mastery_score: 85, needs_regeneration: false, updated_at: new Date().toISOString() },
  { topic: 'Data Structures', mastery_score: 62, needs_regeneration: true, updated_at: new Date().toISOString() },
  { topic: 'Databases & SQL', mastery_score: 48, needs_regeneration: false, updated_at: new Date().toISOString() },
  { topic: 'Network Security', mastery_score: 28, needs_regeneration: true, updated_at: new Date().toISOString() },
  { topic: 'Concurrency & Threads', mastery_score: 72, needs_regeneration: false, updated_at: new Date().toISOString() },
]

export default function Mastery({ navigate }: Props) {
  const [topics, setTopics] = useState<api.TopicMasteryEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [hovered, setHovered] = useState<string | null>(null)
  const [selected, setSelected] = useState<GNode | null>(null)
  const [diff, setDiff] = useState<Awaited<ReturnType<typeof api.getReplayDiff>> | null | 'none' | 'loading'>(null)

  useEffect(() => {
    api.getTopicMastery().then((data) => {
      if (data && data.length > 0) {
        setTopics(data)
      } else {
        setTopics(MOCK_TOPICS)
      }
    }).catch(() => {
      setTopics(MOCK_TOPICS)
    }).finally(() => setLoading(false))
  }, [])

  const nodes = layout(topics)

  const selectNode = async (n: GNode) => {
    setSelected(n)
    setDiff('loading')
    try {
      const d = await api.getReplayDiff(n.id)
      setDiff(d as Awaited<ReturnType<typeof api.getReplayDiff>>)
    } catch (err) {
      const mockDiffs: Record<string, any> = {
        'System Design': {
          earliest: { score: 65, feedback: "Gathered functional requirements but struggled to explain DB partitions under scale." },
          latest: { score: 85, feedback: "Excellent breakdown of Kafka queuing systems, consistent hashing rings, and composite indexes." },
          attempt_count: 2,
          score_delta: 20
        },
        'Data Structures': {
          earliest: { score: 40, feedback: "Relied on brute force loops. Struggled with heap operations and tree balancing constraints." },
          latest: { score: 62, feedback: "Implemented optimal recursive traversals. Solid improvement on Big-O calculation." },
          attempt_count: 2,
          score_delta: 22
        },
        'Databases & SQL': {
          earliest: { score: 35, feedback: "Failed to explain difference between clustered and non-clustered database index profiles." },
          latest: { score: 48, feedback: "Correctly resolved composite keys, but struggled to debug ORM N+1 load latency issues." },
          attempt_count: 2,
          score_delta: 13
        },
        'Network Security': {
          earliest: { score: 28, feedback: "Left database query calls open to injection vulnerabilities. Missing sanitization layers." },
          latest: { score: 28, feedback: "Lacks core security defense patterns. Requires targeted practice cycles." },
          attempt_count: 1,
          score_delta: 0
        },
        'Concurrency & Threads': {
          earliest: { score: 55, feedback: "Struggled to resolve thread safety and mutual exclusion deadlocks." },
          latest: { score: 72, feedback: "Designed thread-safe shared queues. Good use of mutex bounds and semaphores." },
          attempt_count: 2,
          score_delta: 17
        }
      }

      if (mockDiffs[n.id]) {
        setDiff(mockDiffs[n.id])
      } else {
        setDiff('none')
      }
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-bg">
        <Nav page="mastery" navigate={navigate} />
        <OrbitLoader label="Loading mastery map…" size={72} />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-bg text-text transition-colors duration-300 font-sans pb-16">
      <Nav page="mastery" navigate={navigate} />

      <div className="max-w-5xl mx-auto px-6 pt-10">
        
        {/* Header Title */}
        <div className="mb-8">
          <span className="text-[10px] uppercase font-bold tracking-wider text-rust">Knowledge Galaxy</span>
          <h1 className="font-display text-3xl font-bold tracking-tight text-text mt-0.5">Mastery Constellation</h1>
          <p className="text-xs text-text-muted mt-2">
            Interactive map tracing your computer science competencies parsed from mock interview transcripts.
          </p>
        </div>

        {/* Status Legend indicator bar */}
        <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-xl border border-border bg-card-bg/60 glass-panel mb-6 select-none">
          <div className="flex items-center gap-4">
            {(Object.entries(STATUS) as [NodeStatus, typeof STATUS[NodeStatus]][]).map(([key, item]) => (
              <div key={key} className="flex items-center gap-2">
                <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: item.fill }} />
                <span className="text-[10px] text-text-muted font-bold uppercase tracking-wider">{item.label}</span>
              </div>
            ))}
          </div>
          <span className="text-xs text-text-muted font-semibold italic">
            {nodes.filter(n => n.status === 'mastered').length} of {nodes.length} nodes mastered
          </span>
        </div>

        {/* Constellation Workspace Frame */}
        <div className="w-full bg-terminal-bg rounded-2xl border border-border/80 overflow-hidden shadow-2xl relative min-h-[460px]">
          
          {/* Ambient space background */}
          <div className="absolute inset-0 bg-[radial-gradient(#ffffff03_1px,transparent_1px)] [background-size:16px_16px] pointer-events-none" />
          
          <svg viewBox={`0 0 ${VW} ${VH}`} className="w-full h-full block">
            <defs>
              {/* Glowing Filters */}
              {Object.entries(STATUS).map(([key, item]) => (
                <filter key={key} id={`constell-glow-${key}`} x="-30%" y="-30%" width="160%" height="160%">
                  <feGaussianBlur stdDeviation="5" result="blur" />
                  <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
                </filter>
              ))}
            </defs>

            {/* Glowing Concentric Orbits (Dashed background circles) */}
            <circle cx={VW / 2} cy={VH / 2} r="65" fill="none" stroke="rgba(255,255,255,0.03)" strokeWidth="1" strokeDasharray="3 6" />
            <circle cx={VW / 2} cy={VH / 2} r="135" fill="none" stroke="rgba(255,255,255,0.03)" strokeWidth="1" strokeDasharray="4 8" />
            <circle cx={VW / 2} cy={VH / 2} r="200" fill="none" stroke="rgba(255,255,255,0.02)" strokeWidth="1.2" strokeDasharray="5 10" />            {/* Adjacent Constellation Curves (Nodes connected in sequence ring) */}
            {nodes.map((node, idx) => {
              const nextNode = nodes[(idx + 1) % nodes.length]
              return (
                <path
                  key={`edge-ring-${idx}`}
                  d={curvePath(node.x, node.y, nextNode.x, nextNode.y)}
                  fill="none"
                  style={{ stroke: 'var(--rust)' }}
                  strokeOpacity="0.08"
                  strokeWidth="0.8"
                  strokeDasharray="2 4"
                />
              )
            })}

            {/* Radial Core Connectors (Arched lines from center to nodes) */}
            {nodes.map((node) => {
              const isSel = selected?.id === node.id
              const isHov = hovered === node.id
              return (
                <path
                  key={`edge-center-${node.id}`}
                  d={curvePath(VW / 2, VH / 2, node.x, node.y)}
                  fill="none"
                  className="transition-all duration-300"
                  style={{ stroke: 'var(--rust)' }}
                  strokeOpacity={isSel ? 0.45 : isHov ? 0.28 : 0.08}
                  strokeWidth={isSel ? 1.8 : 0.8}
                />
              )
            })}

            {/* Nodes */}
            {nodes.map((node) => {
              const s = STATUS[node.status]
              const isHov = hovered === node.id
              const isSel = selected?.id === node.id
              const scale = isSel ? 1.35 : isHov ? 1.25 : 1

              return (
                <g
                  key={node.id}
                  transform={`translate(${node.x},${node.y})`}
                  className="cursor-pointer"
                  onMouseEnter={() => setHovered(node.id)}
                  onMouseLeave={() => setHovered(null)}
                  onClick={() => selectNode(node)}
                >
                  {/* Outer Pulsing Aura Selector Ring */}
                  {isSel && (
                    <circle r="22" fill="none" stroke={s.fill} strokeWidth="1" opacity="0.4">
                      <animate attributeName="r" values="18;26;18" dur="2s" repeatCount="indefinite" />
                      <animate attributeName="opacity" values="0.4;0;0.4" dur="2s" repeatCount="indefinite" />
                    </circle>
                  )}

                  {/* Core Planet Circle */}
                  <circle 
                    r={12 * scale} 
                    fill={s.fill} 
                    filter={`url(#constell-glow-${node.status})`} 
                    opacity={isHov || isSel ? 0.95 : 0.75} 
                    className="transition-all duration-200" 
                  />
                  
                  {/* Score text directly inside node */}
                  {(isHov || isSel) && (
                    <text textAnchor="middle" dy="3.5" fill="#ffffff" style={{ fontSize: '8px', fontFamily: 'monospace', fontWeight: 'bold' }}>
                      {node.mastery}%
                    </text>
                  )}

                  {/* Label Text below node */}
                  <text 
                    dy={isHov || isSel ? 28 : 24} 
                    textAnchor="middle" 
                    style={{ 
                      fill: isHov || isSel ? '#ffffff' : 'var(--text-muted)',
                      fontSize: '9.5px', 
                      fontWeight: isHov || isSel ? 700 : 500 
                    }}
                    fillOpacity={isHov || isSel ? 1 : 0.75}
                  >
                    {node.label}
                  </text>
                </g>
              )
            })}

            {/* Glowing Galaxy Core */}
            <g transform={`translate(${VW / 2}, ${VH / 2})`}>
              <circle r="18" style={{ fill: 'var(--rust)', fillOpacity: 0.25 }} filter="url(#constell-glow-learning)" />
              <circle r="10" style={{ fill: 'var(--rust)' }} />
              <text textAnchor="middle" dy="3" fill="#ffffff" style={{ fontSize: '8.5px', fontWeight: 'bold' }}>RAG</text>
            </g>
          </svg>

          {/* ── REPLAY DIFF SLIDING PANEL OVERLAY ─────────────────────────── */}
          <AnimatePresence>
            {selected && (
              <motion.div
                initial={{ x: '100%', opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                exit={{ x: '100%', opacity: 0 }}
                transition={{ type: 'spring', damping: 22, stiffness: 150 }}
                className="absolute top-0 right-0 h-full w-80 bg-card-bg/95 border-l border-border/80 backdrop-blur-md shadow-2xl p-6 flex flex-col gap-5 z-20 text-left overflow-y-auto"
              >
                {/* Drawer Close / Header */}
                <div className="flex items-center justify-between border-b border-border/40 pb-3">
                  <span className={`text-[9px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full ${STATUS[selected.status].badge}`}>
                    {STATUS[selected.status].label}
                  </span>
                  <button 
                    onClick={() => setSelected(null)}
                    className="text-text-muted hover:text-text cursor-pointer p-1"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                {/* Node Title & Score */}
                <div>
                  <h3 className="font-display text-base font-bold text-text">{selected.label}</h3>
                  <span className="text-[10px] text-text-muted mt-1 block">
                    Overall mastery: <span className="text-rust font-bold">{selected.mastery}%</span>
                  </span>
                </div>

                {/* Notes regeneration alert block */}
                {selected.needsRegeneration && (
                  <div className="p-3.5 bg-rust/5 border border-rust/15 text-[10px] text-rust font-semibold rounded-xl leading-relaxed flex gap-2">
                    <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                    <span>Seeded card review trigger active in Study Notes.</span>
                  </div>
                )}

                {/* Attempt History / Replay Diffs */}
                <div>
                  <span className="text-[9px] uppercase font-bold text-text-muted tracking-wider mb-2.5 block">Replay Diff stats</span>
                  
                  {diff === 'loading' && <span className="text-xs text-text-muted">Loading history...</span>}
                  
                  {diff === 'none' && (
                    <span className="text-[11px] text-text-muted leading-relaxed block italic">
                      No separate attempt entries saved for this competency node.
                    </span>
                  )}

                  {diff && diff !== 'loading' && diff !== 'none' && (
                    <div className="flex flex-col gap-3">
                      {/* First attempt */}
                      <div className="p-3 rounded-xl border border-border/80 bg-panel-bg/30 text-[11px]">
                        <div className="flex justify-between font-bold text-rust">
                          <span>First attempt</span>
                          <span>{Math.round(diff.earliest.score)}%</span>
                        </div>
                        <p className="text-text-muted mt-1.5 leading-normal">{diff.earliest.feedback}</p>
                      </div>

                      {/* Latest attempt */}
                      {diff.attempt_count > 1 && (
                        <div className="p-3 rounded-xl border border-rust/20 bg-rust/5 text-[11px]">
                          <div className="flex justify-between font-bold text-rust">
                            <span>Latest attempt</span>
                            <span>{Math.round(diff.latest.score)}%</span>
                          </div>
                          <p className="text-text mt-1.5 leading-normal">{diff.latest.feedback}</p>
                          {diff.score_delta != null && (
                            <div className={`mt-2 font-bold flex items-center gap-1 ${diff.score_delta >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                              <TrendingUp className="w-3.5 h-3.5" />
                              <span>
                                {diff.score_delta >= 0 ? '+' : ''}{diff.score_delta} pts delta improvement
                              </span>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Practice Trigger */}
                <button
                  onClick={() => {
                    localStorage.setItem('active_roadmap_topic', selected.label)
                    navigate('interview')
                  }}
                  className="w-full py-2.5 rounded-xl bg-rust hover:bg-rust/90 text-white font-semibold text-xs transition-colors flex items-center justify-center gap-1 cursor-pointer mt-auto"
                >
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>Practice Node</span>
                </button>
              </motion.div>
            )}
          </AnimatePresence>

        </div>

      </div>
    </div>
  )
}
