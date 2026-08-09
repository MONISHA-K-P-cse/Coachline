import { useState, useRef, useEffect, useCallback } from 'react'
import { Nav } from '../components/Nav'
import { OrbitLoader } from '../components/OrbitLoader'
import * as api from '../lib/apiClient'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Send, Mic, MicOff, Settings, Volume2, Plus, 
  MessageSquare, Compass, ArrowRight, CornerDownLeft, Sparkles, BrainCircuit, RefreshCw
} from 'lucide-react'

type Page = 'landing' | 'login' | 'register' | 'onboarding' | 'workspace' | 'roadmap' | 'interview' | 'notes' | 'mastery' | 'mentor'
interface Props { navigate: (p: Page) => void }

// ─── AI Mentor Brain Visualization (RAG context nodes) ──────────────────────
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

function AIMentorBrain({
  thinking,
  voiceEnabled,
  onToggleVoice,
  showVoiceSettings,
  onToggleSettings,
  availableVoices,
  selectedVoiceName,
  onSelectVoice,
  voicePitch,
  onPitchChange,
  voiceRate,
  onRateChange,
  currentlySpeakingId
}: {
  thinking: boolean
  voiceEnabled: boolean
  onToggleVoice: () => void
  showVoiceSettings: boolean
  onToggleSettings: () => void
  availableVoices: SpeechSynthesisVoice[]
  selectedVoiceName: string | null
  onSelectVoice: (name: string) => void
  voicePitch: number
  onPitchChange: (val: number) => void
  voiceRate: number
  onRateChange: (val: number) => void
  currentlySpeakingId: number | null
}) {
  const nodeMap = Object.fromEntries(BRAIN_NODES.map((n) => [n.id, n]))
  return (
    <div className="bg-terminal-bg rounded-t-2xl p-5 border-b border-border/10 relative overflow-hidden flex flex-col sm:flex-row items-center gap-6">
      <div className="absolute inset-0 bg-gradient-to-tr from-rust/5 to-transparent pointer-events-none" />
      
      {/* SVG Network Map */}
      <svg viewBox="0 0 320 176" className="w-48 flex-shrink-0 select-none">
        <defs>
          <filter id="brain-glow" x="-40%" y="-40%" width="180%" height="180%">
            <feGaussianBlur stdDeviation="6" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>

        {BRAIN_EDGES.map((e) => {
          const na = nodeMap[e.from], nb = nodeMap[e.to]
          return (
            <g key={`${e.from}-${e.to}`}>
              <path 
                d={brainArc(na.x, na.y, nb.x, nb.y)} 
                fill="none" 
                className="transition-all duration-300"
                stroke={thinking ? 'rgba(217, 119, 6, 0.45)' : 'rgba(255, 255, 255, 0.08)'} 
                strokeWidth={thinking ? 1.5 : 0.8} 
              />
              {thinking && (
                <path 
                  d={brainArc(na.x, na.y, nb.x, nb.y)} 
                  fill="none" 
                  stroke="rgba(217, 119, 6, 0.9)" 
                  strokeWidth="1.5" 
                  strokeDasharray="4 8"
                >
                  <animate attributeName="stroke-dashoffset" from="0" to="-24" dur="0.8s" repeatCount="indefinite" />
                </path>
              )}
            </g>
          )
        })}

        {/* Outer nodes */}
        {BRAIN_NODES.filter((n) => !n.isCore).map((node) => (
          <g key={node.id} transform={`translate(${node.x},${node.y})`}>
            <circle r={thinking ? 9 : 7} className="fill-rust/80" filter="url(#brain-glow)">
              {thinking && <animate attributeName="opacity" values="0.6;1;0.6" dur="1.5s" repeatCount="indefinite" />}
            </circle>
            <text textAnchor="middle" dy="3.5" className="fill-white text-[7px] font-bold font-mono">
              {node.label.charAt(0)}
            </text>
          </g>
        ))}

        {/* Center core */}
        {(() => {
          const core = nodeMap['ai']
          return (
            <g transform={`translate(${core.x},${core.y})`}>
              <circle r="18" className="fill-rust/35" filter="url(#brain-glow)" />
              <circle r="13" className="fill-rust" />
              <text textAnchor="middle" dy="3.5" className="fill-white text-[9px] font-bold">AI</text>
            </g>
          )
        })()}
      </svg>

      {/* Voice controls & status header */}
      <div className="flex-1 flex flex-col justify-between h-full w-full">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-display font-bold text-base text-white">Career AI Mentor</span>
            {thinking && <span className="text-[8px] font-bold bg-accent/25 text-accent px-2 py-0.5 rounded-full animate-pulse uppercase">Thinking</span>}
          </div>
          <p className="text-xs text-text-muted mt-1 leading-relaxed">
            RAG client grounding search prompts inside targeted competency logs.
          </p>
        </div>

        {/* Wave indicator & action buttons */}
        <div className="flex items-center justify-between gap-4 mt-6">
          <div className="flex items-center gap-3">
            <button
              onClick={onToggleVoice}
              className={`px-3.5 py-1.5 rounded-xl border text-[11px] font-bold tracking-wide transition-all cursor-pointer flex items-center gap-1.5 ${
                voiceEnabled
                  ? 'bg-rust/20 border-rust text-white'
                  : 'border-border/10 bg-white/5 text-text-muted/80 hover:text-white'
              }`}
            >
              <span>{voiceEnabled ? '🔊 Active' : '🔇 Mute'}</span>
            </button>
            <button
              onClick={onToggleSettings}
              className={`p-2 rounded-xl border border-border/10 transition-all cursor-pointer ${
                showVoiceSettings ? 'bg-white/10 text-white' : 'bg-white/5 text-text-muted hover:text-white'
              }`}
              title="Voice Configurations"
            >
              <Settings className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Glowing Voice Waveform */}
          {currentlySpeakingId !== null && (
            <div className="flex items-center gap-1 h-5 select-none pr-4">
              {[0.1, 0.4, 0.2, 0.5, 0.3].map((delay, i) => (
                <div 
                  key={i} 
                  className="w-1 bg-accent rounded-full" 
                  style={{ 
                    height: '100%', 
                    animation: 'speak-bar-bounce 0.7s infinite ease-in-out', 
                    animationDelay: `${delay}s` 
                  }} 
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

interface SessionGroup {
  id: number
  title: string
  messages: api.MentorMessage[]
}

function groupMessages(rawMessages: api.MentorMessage[]): SessionGroup[] {
  const groups: SessionGroup[] = []
  let currentGroup: SessionGroup | null = null

  for (const msg of rawMessages) {
    if (msg.sender === 'system') {
      currentGroup = {
        id: msg.id,
        title: msg.message,
        messages: []
      }
      groups.push(currentGroup)
    } else {
      if (!currentGroup) {
        currentGroup = {
          id: 0,
          title: "Initial Conversation",
          messages: []
        }
        groups.push(currentGroup)
      }
      currentGroup.messages.push(msg)
    }
  }
  return groups
}

function speakText(text: string, voiceName: string | null, pitch: number, rate: number, onEnd: () => void) {
  if (!window.speechSynthesis) {
    onEnd()
    return
  }
  window.speechSynthesis.cancel()

  const utterance = new SpeechSynthesisUtterance(text)
  const voices = window.speechSynthesis.getVoices()
  if (voiceName) {
    const found = voices.find(v => v.name === voiceName)
    if (found) utterance.voice = found
  }
  utterance.pitch = pitch
  utterance.rate = rate

  utterance.onend = onEnd
  utterance.onerror = onEnd
  window.speechSynthesis.speak(utterance)
}

export default function Mentor({ navigate }: Props) {
  const [messages, setMessages] = useState<api.MentorMessage[]>([])
  const [loading, setLoading] = useState(true)
  const [inputValue, setInputValue] = useState('')
  const [thinking, setThinking] = useState(false)

  const [voiceEnabled, setVoiceEnabled] = useState(false)
  const [showVoiceSettings, setShowVoiceSettings] = useState(false)
  const [availableVoices, setAvailableVoices] = useState<SpeechSynthesisVoice[]>([])
  const [selectedVoiceName, setSelectedVoiceName] = useState<string | null>(null)
  const [voicePitch, setVoicePitch] = useState(1.0)
  const [voiceRate, setVoiceRate] = useState(1.0)
  const [currentlySpeakingId, setCurrentlySpeakingId] = useState<number | null>(null)

  const [selectedGroupId, setSelectedGroupId] = useState<number | null>(null)
  const chatBottomRef = useRef<HTMLDivElement>(null)

  const loadMessages = useCallback(async () => {
    try {
      const data = await api.getMentorHistory()
      setMessages(data)

      const groups = groupMessages(data)
      if (groups.length > 0 && selectedGroupId === null) {
        setSelectedGroupId(groups[groups.length - 1].id)
      }
    } catch (err) {
      console.error(err)
    }
  }, [selectedGroupId])

  useEffect(() => {
    loadMessages().finally(() => setLoading(false))
  }, [loadMessages])

  useEffect(() => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      const loadVoices = () => {
        const list = window.speechSynthesis.getVoices()
        setAvailableVoices(list.filter(v => v.lang.startsWith('en')))
      }
      loadVoices()
      window.speechSynthesis.onvoiceschanged = loadVoices
    }
  }, [])

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, thinking])

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputValue.trim() || thinking) return
    const userText = inputValue.trim()
    setInputValue('')
    setThinking(true)

    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel()
      setCurrentlySpeakingId(null)
    }

    try {
      if (groupMessages(messages).length === 0) {
        const firstSession = await api.startNewMentorSession()
        setMessages((p) => [...p, firstSession])
        setSelectedGroupId(firstSession.id)
      }

      const [userMsg, mentorMsg] = await api.sendMentorMessage(userText)
      setMessages((p) => [...p, userMsg, mentorMsg])

      if (voiceEnabled) {
        setCurrentlySpeakingId(mentorMsg.id)
        speakText(
          mentorMsg.message.replace(/[*#_`]/g, ''),
          selectedVoiceName,
          voicePitch,
          voiceRate,
          () => setCurrentlySpeakingId(null)
        )
      }

      if (selectedGroupId === null || selectedGroupId === 0) {
        const fresh = await api.getMentorHistory()
        setMessages(fresh)
        const freshGroups = groupMessages(fresh)
        if (freshGroups.length) {
          setSelectedGroupId(freshGroups[freshGroups.length - 1].id)
        }
      }
    } catch (err) {
      alert("Mentor message processing failed.")
    } finally {
      setThinking(false)
    }
  }

  const handleStartConversation = async () => {
    if (thinking) return
    setThinking(true)
    try {
      if (window.speechSynthesis) window.speechSynthesis.cancel()
      setCurrentlySpeakingId(null)
      const newSessionMsg = await api.startNewMentorSession()
      setMessages((p) => [...p, newSessionMsg])
      setSelectedGroupId(newSessionMsg.id)
    } catch (err) {
      alert("Could not start new conversation.")
    } finally {
      setThinking(false)
    }
  }

  const sessionGroups = groupMessages(messages)
  const currentGroup = sessionGroups.find(g => g.id === selectedGroupId) || sessionGroups[sessionGroups.length - 1]
  const displayMessages = currentGroup ? currentGroup.messages : []

  if (loading) {
    return (
      <div className="min-h-screen bg-bg">
        <Nav page="mentor" navigate={navigate} />
        <OrbitLoader label="Syncing mentor logs..." size={80} />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-bg text-text transition-colors duration-300 font-sans flex flex-col h-screen overflow-hidden">
      <Nav page="mentor" navigate={navigate} />

      <div className="flex-1 flex overflow-hidden">
        
        {/* Sidebar thread selector */}
        <aside className="w-80 border-r border-border bg-panel-bg/30 flex flex-col h-full overflow-hidden">
          
          {/* New convo button */}
          <div className="p-4 border-b border-border/80 flex flex-col gap-3">
            <span className="text-[9px] uppercase font-bold tracking-wider text-text-muted">Chat History</span>
            <button
              onClick={handleStartConversation}
              disabled={thinking}
              className="w-full py-2.5 bg-rust hover:bg-rust/95 text-white rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors cursor-pointer shadow-sm shadow-rust/10"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>New Conversation</span>
            </button>
          </div>

          {/* Folder listing */}
          <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-2">
            {sessionGroups.length === 0 ? (
              <p className="text-xs text-text-muted italic text-center py-10">No sessions recorded.</p>
            ) : (
              sessionGroups.map((g) => {
                const isActive = g.id === selectedGroupId
                return (
                  <button
                    key={g.id}
                    onClick={() => setSelectedGroupId(g.id)}
                    className={`w-full flex items-start gap-3 p-3 rounded-xl border text-left transition-all cursor-pointer ${
                      isActive
                        ? 'border-rust bg-card-bg text-text shadow-sm'
                        : 'border-transparent hover:bg-border/20 text-text-muted hover:text-text'
                    }`}
                  >
                    <MessageSquare className={`w-4 h-4 mt-0.5 flex-shrink-0 ${isActive ? 'text-rust' : 'text-text-muted/60'}`} />
                    <div className="flex-1 min-w-0">
                      <div className="font-bold text-xs leading-normal truncate">{g.title}</div>
                      <span className="text-[9px] text-text-muted/60 mt-1 block">
                        {g.messages.length} exchanges
                      </span>
                    </div>
                  </button>
                )
              })
            )}
          </div>
        </aside>

        {/* Main Chat Area */}
        <main className="flex-1 flex flex-col h-full bg-bg/50 overflow-hidden">
          
          {/* RAG network brain header */}
          <AIMentorBrain
            thinking={thinking}
            voiceEnabled={voiceEnabled}
            onToggleVoice={() => setVoiceEnabled(!voiceEnabled)}
            showVoiceSettings={showVoiceSettings}
            onToggleSettings={() => setShowVoiceSettings(!showVoiceSettings)}
            availableVoices={availableVoices}
            selectedVoiceName={selectedVoiceName}
            onSelectVoice={setSelectedVoiceName}
            voicePitch={voicePitch}
            onPitchChange={setVoicePitch}
            voiceRate={voiceRate}
            onRateChange={setVoiceRate}
            currentlySpeakingId={currentlySpeakingId}
          />

          {/* Settings panel */}
          <AnimatePresence>
            {showVoiceSettings && (
              <motion.div 
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="bg-terminal-bg/95 border-b border-border/10 p-5 grid grid-cols-1 sm:grid-cols-3 gap-5 text-left select-none overflow-hidden"
              >
                <div className="flex flex-col gap-1.5">
                  <label className="text-[9px] uppercase font-bold text-text-muted">Voice Character</label>
                  <select
                    value={selectedVoiceName || ''}
                    onChange={(e) => setSelectedVoiceName(e.target.value)}
                    className="w-full bg-bg/40 border border-border/10 rounded-lg text-xs font-semibold px-2 py-1.5 focus:outline-none focus:border-rust"
                  >
                    <option value="">System Default</option>
                    {availableVoices.map(v => <option key={v.name} value={v.name}>{v.name}</option>)}
                  </select>
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className="text-[9px] uppercase font-bold text-text-muted">Speech Rate ({voiceRate}x)</label>
                  <input
                    type="range"
                    min="0.6"
                    max="1.8"
                    step="0.1"
                    value={voiceRate}
                    onChange={(e) => setVoiceRate(parseFloat(e.target.value))}
                    className="w-full accent-rust"
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className="text-[9px] uppercase font-bold text-text-muted">Speech Pitch ({voicePitch}x)</label>
                  <input
                    type="range"
                    min="0.5"
                    max="1.5"
                    step="0.1"
                    value={voicePitch}
                    onChange={(e) => setVoicePitch(parseFloat(e.target.value))}
                    className="w-full accent-rust"
                  />
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Chat scrolling feed */}
          <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-4">
            {displayMessages.length === 0 ? (
              <div className="text-center py-24 text-text-muted max-w-sm mx-auto">
                <BrainCircuit className="w-8 h-8 mx-auto text-text-muted/40 mb-3 animate-pulse" />
                <p className="text-xs">Introduce yourself. Ask questions about system architecture design, STAR formats, or security principles.</p>
              </div>
            ) : (
              displayMessages.map((msg) => {
                const isUser = msg.sender === 'user'
                return (
                  <div 
                    key={msg.id}
                    className={`flex flex-col max-w-[80%] ${isUser ? 'self-end items-end' : 'self-start items-start'}`}
                  >
                    <div className={`p-4 rounded-2xl text-xs sm:text-sm leading-relaxed ${
                      isUser 
                        ? 'bg-rust text-white shadow-sm shadow-rust/10'
                        : 'border border-border bg-card-bg/60 glass-panel text-text'
                    }`}>
                      <p className="whitespace-pre-wrap">{msg.message}</p>
                    </div>
                    <span className="text-[9px] text-text-muted/65 mt-1 px-1">
                      {isUser ? 'You' : 'Mentor'} · {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                )
              })
            )}

            {thinking && (
              <div className="self-start flex items-center gap-2.5 p-4 rounded-2xl border border-border bg-card-bg/40 max-w-[80%]">
                <RefreshCw className="w-4 h-4 text-rust animate-spin" />
                <span className="text-xs text-text-muted font-semibold tracking-wide">Mentor is preparing advice...</span>
              </div>
            )}

            <div ref={chatBottomRef} />
          </div>

          {/* Chat Form prompt inputs */}
          <form 
            onSubmit={handleSend}
            className="p-4 border-t border-border/80 bg-panel-bg/40 flex items-center gap-3.5"
          >
            <input
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Ask for guidance on STAR method or CS fundamentals..."
              className="flex-1 px-4 py-3 rounded-xl border border-border/70 bg-bg/50 text-xs sm:text-sm focus:outline-none focus:border-rust/80 focus:ring-3 focus:ring-rust/15 transition-all placeholder:text-text-muted/40"
            />
            <button
              type="submit"
              disabled={!inputValue.trim() || thinking}
              className={`p-3 rounded-xl text-white transition-all duration-200 cursor-pointer ${
                !inputValue.trim() || thinking ? 'bg-rust/50 cursor-not-allowed' : 'bg-rust hover:bg-rust/90 shadow-md shadow-rust/20 hover:shadow-lg active:scale-[0.98]'
              }`}
            >
              <Send className="w-4 h-4" />
            </button>
          </form>

        </main>

      </div>
    </div>
  )
}
