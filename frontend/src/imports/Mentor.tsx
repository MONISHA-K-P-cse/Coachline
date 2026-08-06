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
    <div style={{ background: 'linear-gradient(160deg, #1C1917 0%, #261A13 100%)', borderRadius: '18px 18px 0 0', padding: '14px 20px 10px', position: 'relative', overflow: 'hidden' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, position: 'relative', width: '100%' }}>
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
        <div style={{ flex: 1, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
              <div style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 15, fontWeight: 700, color: '#FAFAF8' }}>Your Mentor</div>
              {thinking && <span style={{ fontSize: 10, color: '#E0A458', fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase' }}>Thinking</span>}
              {currentlySpeakingId !== null && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 2.5, height: 12, marginLeft: 8 }}>
                  <style>{`
                    @keyframes speak-bar-bounce {
                      0%, 100% { height: 4px; }
                      50% { height: 14px; }
                    }
                  `}</style>
                  <div style={{ width: 2.5, height: 8, borderRadius: 1, backgroundColor: '#E0A458', animation: 'speak-bar-bounce 0.6s infinite ease-in-out', animationDelay: '0s' }} />
                  <div style={{ width: 2.5, height: 8, borderRadius: 1, backgroundColor: '#E0A458', animation: 'speak-bar-bounce 0.6s infinite ease-in-out', animationDelay: '0.15s' }} />
                  <div style={{ width: 2.5, height: 8, borderRadius: 1, backgroundColor: '#E0A458', animation: 'speak-bar-bounce 0.6s infinite ease-in-out', animationDelay: '0.3s' }} />
                </div>
              )}
            </div>
            <div style={{ fontSize: 11, color: 'rgba(250,250,248,0.55)', lineHeight: 1.5 }}>
              Grounded in interview prep reference material via RAG retrieval.
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <button
              onClick={onToggleVoice}
              style={{
                background: voiceEnabled ? 'rgba(181,80,46,0.25)' : 'rgba(255,255,255,0.08)',
                border: voiceEnabled ? '1.5px solid #B5502E' : '1px solid rgba(255,255,255,0.12)',
                borderRadius: 100,
                cursor: 'pointer',
                padding: '6px 14px',
                fontSize: 11.5,
                fontWeight: 700,
                color: '#FAFAF8',
                fontFamily: "'Plus Jakarta Sans', sans-serif",
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                transition: 'all 0.15s ease'
              }}
            >
              <span>{voiceEnabled ? '🔊' : '🔇'}</span> {voiceEnabled ? 'Voice Active' : 'Mute'}
            </button>
            <button
              onClick={onToggleSettings}
              style={{
                background: showVoiceSettings ? 'rgba(255,255,255,0.15)' : 'rgba(255,255,255,0.08)',
                border: '1px solid rgba(255,255,255,0.12)',
                borderRadius: '50%',
                cursor: 'pointer',
                width: 32,
                height: 32,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#FAFAF8',
                transition: 'all 0.15s ease',
                fontSize: 14
              }}
              title="Voice Settings"
            >
              ⚙️
            </button>
          </div>
        </div>
      </div>

      {showVoiceSettings && (
        <div style={{
          marginTop: 14,
          padding: 16,
          background: 'rgba(255,255,255,0.04)',
          borderRadius: 12,
          border: '1.5px solid rgba(255,255,255,0.08)',
          display: 'grid',
          gridTemplateColumns: '1fr 1fr 1fr',
          gap: 16,
          animation: 'fade-in 0.2s ease'
        }}>
          <div>
            <label style={{ display: 'block', fontSize: 10, color: 'rgba(250,250,248,0.6)', fontWeight: 700, letterSpacing: '0.05em', textTransform: 'uppercase', marginBottom: 6 }}>Voice Speaker</label>
            <select
              value={selectedVoiceName || ''}
              onChange={(e) => onSelectVoice(e.target.value)}
              style={{
                width: '100%',
                background: '#1C1917',
                border: '1px solid rgba(255,255,255,0.15)',
                borderRadius: 6,
                color: '#FAFAF8',
                fontSize: 11.5,
                padding: '6px 8px',
                outline: 'none',
                fontFamily: "'Plus Jakarta Sans', sans-serif"
              }}
            >
              <option value="">Default Female Voice</option>
              {availableVoices.map((v) => (
                <option key={v.name} value={v.name}>{v.name} ({v.lang})</option>
              ))}
            </select>
          </div>

          <div>
            <label style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'rgba(250,250,248,0.6)', fontWeight: 700, letterSpacing: '0.05em', textTransform: 'uppercase', marginBottom: 6 }}>
              <span>Speed (Rate)</span>
              <span>{voiceRate}x</span>
            </label>
            <input
              type="range"
              min="0.6"
              max="1.8"
              step="0.1"
              value={voiceRate}
              onChange={(e) => onRateChange(parseFloat(e.target.value))}
              style={{
                width: '100%',
                accentColor: '#B5502E',
                cursor: 'pointer'
              }}
            />
          </div>

          <div>
            <label style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'rgba(250,250,248,0.6)', fontWeight: 700, letterSpacing: '0.05em', textTransform: 'uppercase', marginBottom: 6 }}>
              <span>Pitch</span>
              <span>{voicePitch}x</span>
            </label>
            <input
              type="range"
              min="0.5"
              max="1.5"
              step="0.1"
              value={voicePitch}
              onChange={(e) => onPitchChange(parseFloat(e.target.value))}
              style={{
                width: '100%',
                accentColor: '#B5502E',
                cursor: 'pointer'
              }}
            />
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Main helper functions ───────────────────────────────────────────────────

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
  
  let selectedVoice = null
  if (voiceName) {
    selectedVoice = voices.find(v => v.name === voiceName)
  }
  
  if (!selectedVoice) {
    const femaleVoiceNames = ["samantha", "karen", "moira", "tessa", "zira", "google us english", "microsoft zira", "female", "en-us"]
    for (const name of femaleVoiceNames) {
      const found = voices.find(v => v.name.toLowerCase().includes(name) && v.lang.startsWith('en'))
      if (found) {
        selectedVoice = found
        break
      }
    }
  }
  
  if (!selectedVoice && voices.length) {
    selectedVoice = voices.find(v => v.lang.startsWith('en')) || voices[0]
  }

  if (selectedVoice) {
    utterance.voice = selectedVoice
  }

  utterance.pitch = pitch
  utterance.rate = rate

  utterance.onend = onEnd
  utterance.onerror = onEnd

  window.speechSynthesis.speak(utterance)
}

// ─── Main component ──────────────────────────────────────────────────────────

export default function Mentor({ navigate }: Props) {
  const [messages, setMessages] = useState<api.MentorMessage[]>([])
  const [loading, setLoading] = useState(true)
  const [input, setInput] = useState('')
  const [thinking, setThinking] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [currentlySpeakingId, setCurrentlySpeakingId] = useState<number | null>(null)
  const [selectedGroupId, setSelectedGroupId] = useState<number | null>(null)
  const [voiceEnabled, setVoiceEnabled] = useState(false)
  const [selectedVoiceName, setSelectedVoiceName] = useState<string | null>(null)
  const [voicePitch, setVoicePitch] = useState<number>(1.0)
  const [voiceRate, setVoiceRate] = useState<number>(1.0)
  const [availableVoices, setAvailableVoices] = useState<SpeechSynthesisVoice[]>([])
  const [showVoiceSettings, setShowVoiceSettings] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  const load = async () => {
    try {
      const data = await api.getMentorHistory()
      setMessages(data)
      const groups = groupMessages(data)
      if (groups.length && selectedGroupId === null) {
        setSelectedGroupId(groups[groups.length - 1].id)
      }
    } catch (err) {
      setError('Could not load chat history.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    if (window.speechSynthesis) {
      const updateVoices = () => {
        const list = window.speechSynthesis.getVoices().filter(v => v.lang.startsWith('en'))
        setAvailableVoices(list)
      }
      updateVoices()
      window.speechSynthesis.onvoiceschanged = updateVoices
    }
    return () => {
      if (window.speechSynthesis) window.speechSynthesis.cancel()
    }
  }, [])

  const sessionGroups = groupMessages(messages)
  const activeGroup = sessionGroups.find(g => g.id === selectedGroupId)
  const activeMessages = activeGroup ? activeGroup.messages : []

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [activeMessages, thinking])

  const send = async () => {
    const text = input.trim()
    if (!text) return
    setInput('')
    setError(null)
    setThinking(true)
    try {
      if (sessionGroups.length === 0) {
        const firstSession = await api.startNewMentorSession()
        setMessages((p) => [...p, firstSession])
        setSelectedGroupId(firstSession.id)
      }
      
      const [userMsg, mentorMsg] = await api.sendMentorMessage(text)
      setMessages((p) => [...p, userMsg, mentorMsg])

      if (voiceEnabled) {
        handleSpeak(mentorMsg.id, mentorMsg.message)
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
      setError(err instanceof api.ApiError ? err.message : 'The mentor is temporarily unavailable.')
    } finally {
      setThinking(false)
    }
  }

  const startNewChat = async () => {
    setError(null)
    setThinking(true)
    try {
      if (window.speechSynthesis) window.speechSynthesis.cancel()
      setCurrentlySpeakingId(null)
      const newSessionMsg = await api.startNewMentorSession()
      setMessages((p) => [...p, newSessionMsg])
      setSelectedGroupId(newSessionMsg.id)
    } catch (err) {
      setError("Could not start a new conversation.")
    } finally {
      setThinking(false)
    }
  }

  const clearAllHistory = async () => {
    if (!window.confirm("Are you sure you want to clear ALL your conversation history? This cannot be undone.")) return
    setError(null)
    try {
      if (window.speechSynthesis) window.speechSynthesis.cancel()
      setCurrentlySpeakingId(null)
      await api.clearMentorHistory()
      setMessages([])
      setSelectedGroupId(null)
    } catch (err) {
      setError("Could not clear history.")
    }
  }

  const handleSpeak = (id: number, text: string) => {
    if (!window.speechSynthesis) return
    if (currentlySpeakingId === id) {
      window.speechSynthesis.cancel()
      setCurrentlySpeakingId(null)
    } else {
      setCurrentlySpeakingId(id)
      speakText(text, selectedVoiceName, voicePitch, voiceRate, () => {
        setCurrentlySpeakingId(null)
      })
    }
  }

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#FAFAF8', fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif", display: 'flex', flexDirection: 'column' }}>
      <Nav page="mentor" navigate={navigate} />

      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '260px 1fr', maxHeight: 'calc(100vh - 64px)', overflow: 'hidden' }}>
        {/* Sidebar */}
        <div style={{ borderRight: '1px solid rgba(181,80,46,0.10)', padding: '20px 16px', overflowY: 'auto', background: '#F5F2EE', display: 'flex', flexDirection: 'column', gap: 12 }}>
          <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.10em', textTransform: 'uppercase', color: '#7A6B63', padding: '0 8px', margin: 0 }}>
            Conversations
          </p>
          <button
            onClick={startNewChat}
            style={{
              width: '100%',
              background: 'linear-gradient(135deg, #B5502E, #C97350)',
              border: 'none',
              cursor: 'pointer',
              color: '#FAFAF8',
              fontSize: 12.5,
              fontWeight: 700,
              padding: '10px 0',
              borderRadius: 10,
              fontFamily: "'Plus Jakarta Sans', sans-serif"
            }}
          >
            + New Chat
          </button>
          
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 6, marginTop: 8 }}>
            {sessionGroups.map((group) => (
              <button
                key={group.id}
                onClick={() => {
                  if (window.speechSynthesis) window.speechSynthesis.cancel()
                  setCurrentlySpeakingId(null)
                  setSelectedGroupId(group.id)
                }}
                style={{
                  display: 'block',
                  width: '100%',
                  textAlign: 'left',
                  padding: '12px 10px',
                  borderRadius: 10,
                  background: selectedGroupId === group.id ? '#FFFFFF' : 'transparent',
                  border: selectedGroupId === group.id ? '1.5px solid rgba(181,80,46,0.20)' : '1.5px solid transparent',
                  cursor: 'pointer',
                  fontFamily: "'Plus Jakarta Sans', sans-serif",
                  transition: 'all 0.15s ease'
                }}
              >
                <div style={{ fontSize: 12.5, fontWeight: 600, color: '#1C1917', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {group.title}
                </div>
              </button>
            ))}
          </div>

          <button
            onClick={clearAllHistory}
            style={{
              background: 'none',
              border: '1px solid rgba(181,80,46,0.30)',
              borderRadius: 10,
              cursor: 'pointer',
              padding: '8px 0',
              fontSize: 11.5,
              fontWeight: 700,
              color: '#B5502E',
              fontFamily: "'Plus Jakarta Sans', sans-serif",
              marginTop: 'auto'
            }}
          >
            Clear All History
          </button>
        </div>

        {/* Chat Area */}
        <div style={{ display: 'flex', flexDirection: 'column', padding: '0 24px', height: '100%', overflow: 'hidden' }}>
          <div style={{ flexShrink: 0, marginTop: 20, borderRadius: 18, overflow: 'hidden', border: '1.5px solid rgba(181,80,46,0.12)', boxShadow: '0 2px 12px rgba(0,0,0,0.06)' }}>
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
            <div style={{ borderTop: '1px solid rgba(181,80,46,0.10)' }} />
          </div>

          <div style={{ flex: 1, overflowY: 'auto', padding: '20px 0', display: 'flex', flexDirection: 'column', gap: 20 }}>
            {loading ? (
              <OrbitLoader label="Loading conversation…" size={56} />
            ) : activeMessages.length === 0 ? (
              <p style={{ textAlign: 'center', color: '#7A6B63', fontSize: 13, marginTop: 40 }}>
                Ask your mentor anything about interview prep — it has access to the same reference material as your notes and questions.
              </p>
            ) : (
              activeMessages.map((msg) => (
                <div key={msg.id} style={{ display: 'flex', flexDirection: msg.sender === 'user' ? 'row-reverse' : 'row', alignItems: 'flex-start', gap: 12 }}>
                  {msg.sender === 'mentor' && (
                    <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'linear-gradient(135deg, #B5502E, #C97350)', flexShrink: 0, marginTop: 2 }} />
                  )}
                  <div
                    style={{
                      maxWidth: '75%',
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
                  {msg.sender === 'mentor' && (
                    <button
                      onClick={() => handleSpeak(msg.id, msg.message)}
                      style={{
                        background: 'rgba(181,80,46,0.06)',
                        border: 'none',
                        borderRadius: '50%',
                        cursor: 'pointer',
                        fontSize: 12,
                        width: 28,
                        height: 28,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: currentlySpeakingId === msg.id ? '#B5502E' : '#7A6B63',
                        alignSelf: 'center',
                        marginTop: 4
                      }}
                      title={currentlySpeakingId === msg.id ? "Stop voice" : "Listen to response"}
                    >
                      {currentlySpeakingId === msg.id ? '⏹️' : '🔊'}
                    </button>
                  )}
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
    </div>
  )
}
