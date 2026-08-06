import { useState, useRef, useEffect } from 'react'
import { Nav } from '../components/Nav'
import { OrbitLoader } from '../components/OrbitLoader'
import { useAuth } from '../lib/AuthContext'
import { interviewWebSocketUrl } from '../lib/apiClient'

type Page = 'landing' | 'login' | 'register' | 'onboarding' | 'workspace' | 'roadmap' | 'interview' | 'notes' | 'mastery' | 'mentor'
interface Props { navigate: (p: Page) => void }

type Stage = 'ready' | 'connecting' | 'answering' | 'evaluating' | 'feedback' | 'ended' | 'error'

// A single "answer" turn makes two sequential model calls before
// responding (eval, then next question) - weak-topic note regeneration now
// runs *after* the response is sent, so it no longer inflates this wait.
// Each call has its own ~240s backend timeout, so the client-side
// "something's actually wrong" threshold sits comfortably above both
// calls' worst case, not just one. The initial connect has no model call
// at all, so it gets a much shorter budget.
const CONNECT_TIMEOUT_MS = 15_000
const RESPONSE_TIMEOUT_MS = 520_000

interface EvalPayload {
  previous_score: number
  scores_breakdown: { technical: number; communication: number; behavioral: number; confidence: number; star_method: number }
  feedback: string
  weak_topics: string[]
  fallback_used: boolean
  turn_number: number
  next_question: string
  difficulty: string
  mode: 'standard' | 'devils_advocate'
}

export default function Interview({ navigate }: Props) {
  const { user } = useAuth()
  const [role, setRole] = useState(user?.profile?.target_role || 'Backend Engineer')
  const [stage, setStage] = useState<Stage>('ready')
  const [question, setQuestion] = useState('')
  const [mode, setMode] = useState<'standard' | 'devils_advocate'>('standard')
  const [answer, setAnswer] = useState('')
  const [turnNumber, setTurnNumber] = useState(1)
  const [feedback, setFeedback] = useState<EvalPayload | null>(null)
  const [ended, setEnded] = useState<{ average_score: number; scores_breakdown: EvalPayload['scores_breakdown'] } | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [slowWait, setSlowWait] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const waitTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const slowTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  // Distinguishes a close we triggered ourselves (timeout bail-out, end of
  // session) from one the server/network initiated, so onclose only shows
  // an error for the latter.
  const expectedCloseRef = useRef(false)

  const clearWaitTimer = () => {
    if (waitTimerRef.current) {
      clearTimeout(waitTimerRef.current)
      waitTimerRef.current = null
    }
    if (slowTimerRef.current) {
      clearTimeout(slowTimerRef.current)
      slowTimerRef.current = null
    }
    setSlowWait(false)
  }

  // Arms a "give up and let the user retry" timer for whatever we're
  // currently waiting on the socket for. Any real response clears it via
  // clearWaitTimer(); if it fires first, the connection is presumed stuck
  // and we surface a visible error instead of spinning forever. A shorter
  // "still working" nudge fires first so a merely-slow (not stuck) call
  // doesn't look identical to a hang while it's still in flight.
  const armWaitTimer = (ms: number, message: string) => {
    clearWaitTimer()
    if (ms > 20_000) {
      slowTimerRef.current = setTimeout(() => setSlowWait(true), 20_000)
    }
    waitTimerRef.current = setTimeout(() => {
      expectedCloseRef.current = true
      wsRef.current?.close()
      setErrorMsg(message)
      setStage('error')
    }, ms)
  }

  const [isSpeaking, setIsSpeaking] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [secondsSpent, setSecondsSpent] = useState(0)
  const [lastAnswerDuration, setLastAnswerDuration] = useState<number | null>(null)
  const timerIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const recognitionRef = useRef<any>(null)

  useEffect(() => {
    if (stage === 'answering') {
      setSecondsSpent(0)
      timerIntervalRef.current = setInterval(() => {
        setSecondsSpent(prev => prev + 1)
      }, 1000)
    } else {
      if (timerIntervalRef.current) {
        clearInterval(timerIntervalRef.current)
        timerIntervalRef.current = null
      }
    }
    return () => {
      if (timerIntervalRef.current) {
        clearInterval(timerIntervalRef.current)
        timerIntervalRef.current = null
      }
    }
  }, [stage, question])

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60)
    const s = secs % 60
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  }

  useEffect(() => () => {
    clearWaitTimer()
    expectedCloseRef.current = true
    wsRef.current?.close()
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel()
    }
    recognitionRef.current?.stop()
  }, [])

  const speakQuestion = () => {
    if ('speechSynthesis' in window) {
      if (isSpeaking) {
        window.speechSynthesis.cancel()
        setIsSpeaking(false)
      } else {
        window.speechSynthesis.cancel()
        const cleanText = question.replace(/[*#_`]/g, '')
        const utterance = new SpeechSynthesisUtterance(cleanText)
        
        const voices = window.speechSynthesis.getVoices()
        const femaleVoiceNames = ["samantha", "karen", "moira", "tessa", "zira", "google us english", "microsoft zira", "female", "en-us"]
        
        let selectedVoice = null
        for (const name of femaleVoiceNames) {
          const found = voices.find(v => v.name.toLowerCase().includes(name) && v.lang.startsWith('en'))
          if (found) {
            selectedVoice = found
            break
          }
        }
        
        if (!selectedVoice && voices.length) {
          selectedVoice = voices.find(v => v.lang.startsWith('en')) || voices[0]
        }
        
        if (selectedVoice) {
          utterance.voice = selectedVoice
        }

        utterance.onend = () => setIsSpeaking(false)
        utterance.onerror = () => setIsSpeaking(false)
        setIsSpeaking(true)
        window.speechSynthesis.speak(utterance)
      }
    } else {
      alert("Text-to-Speech is not supported in this browser.")
    }
  }

  const toggleRecording = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SpeechRecognition) {
      alert("Speech Recognition is not supported in this browser. Please use a browser like Chrome, Safari or Edge.")
      return
    }

    if (isRecording) {
      recognitionRef.current?.stop()
      setIsRecording(false)
    } else {
      const rec = new SpeechRecognition()
      rec.continuous = true
      rec.interimResults = true
      rec.lang = 'en-US'

      rec.onstart = () => {
        setIsRecording(true)
      }

      rec.onresult = (event: any) => {
        let finalTrans = ''
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            finalTrans += event.results[i][0].transcript
          }
        }
        if (finalTrans) {
          setAnswer((prev) => prev + (prev.endsWith(' ') || prev === '' ? '' : ' ') + finalTrans)
        }
      }

      rec.onerror = (e: any) => {
        console.error("Speech recognition error", e)
        setIsRecording(false)
      }

      rec.onend = () => {
        setIsRecording(false)
      }

      recognitionRef.current = rec
      rec.start()
    }
  }

  const connectAndStart = () => {
    if (!user) return
    setStage('connecting')
    setErrorMsg(null)
    expectedCloseRef.current = false
    const ws = new WebSocket(interviewWebSocketUrl(user.id))
    wsRef.current = ws

    armWaitTimer(CONNECT_TIMEOUT_MS, 'Could not connect to the interview server. Please try again.')

    ws.onopen = () => {
      const weekStr = localStorage.getItem('active_roadmap_week')
      const topicStr = localStorage.getItem('active_roadmap_topic')
      const weekVal = weekStr ? parseInt(weekStr) : 1
      ws.send(JSON.stringify({
        event: 'start',
        role,
        week: weekVal,
        topic: topicStr || undefined
      }))
      localStorage.removeItem('active_roadmap_week')
      localStorage.removeItem('active_roadmap_topic')
      
      // First question has no model call behind it, so the same short
      // connect budget applies to it too.
      armWaitTimer(CONNECT_TIMEOUT_MS, 'The interview server accepted the connection but never sent a question. Please try again.')
    }

    ws.onmessage = (evt) => {
      clearWaitTimer()
      const data = JSON.parse(evt.data)
      if (data.event === 'question') {
        if ('speechSynthesis' in window) {
          window.speechSynthesis.cancel()
          setIsSpeaking(false)
        }
        setQuestion(data.question)
        setMode(data.mode ?? 'standard')
        setTurnNumber(data.turn_number)
        setStage('answering')
        setTimeout(() => textareaRef.current?.focus(), 100)
      } else if (data.event === 'eval_and_next') {
        if ('speechSynthesis' in window) {
          window.speechSynthesis.cancel()
          setIsSpeaking(false)
        }
        setFeedback(data as EvalPayload)
        setStage('feedback')
      } else if (data.event === 'ended') {
        expectedCloseRef.current = true
        if ('speechSynthesis' in window) {
          window.speechSynthesis.cancel()
          setIsSpeaking(false)
        }
        setEnded({ average_score: data.average_score, scores_breakdown: data.scores_breakdown })
        setStage('ended')
      } else if (data.event === 'error') {
        setErrorMsg(data.message)
        setStage('error')
      }
    }

    ws.onerror = () => {
      clearWaitTimer()
      setErrorMsg('Lost connection to the interview server.')
      setStage('error')
    }

    ws.onclose = () => {
      clearWaitTimer()
      if (!expectedCloseRef.current) {
        setErrorMsg('The connection to the interview server closed unexpectedly. Please try again.')
        setStage('error')
      }
    }
  }

  const handleSubmit = () => {
    if (!answer.trim() || !wsRef.current) return
    if (isRecording) {
      recognitionRef.current?.stop()
      setIsRecording(false)
    }
    setLastAnswerDuration(secondsSpent)
    wsRef.current.send(JSON.stringify({ event: 'answer', user_answer: answer }))
    setStage('evaluating')
    armWaitTimer(
      RESPONSE_TIMEOUT_MS,
      "This is taking much longer than expected - the AI evaluator may be stuck. Please try again."
    )
  }

  const handleNext = () => {
    if (!feedback) return
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel()
      setIsSpeaking(false)
    }
    setQuestion(feedback.next_question)
    setMode(feedback.mode)
    setAnswer('')
    setFeedback(null)
    setStage('answering')
    setTimeout(() => textareaRef.current?.focus(), 100)
  }

  const handleEnd = () => {
    if (isRecording) {
      recognitionRef.current?.stop()
      setIsRecording(false)
    }
    wsRef.current?.send(JSON.stringify({ event: 'end' }))
    armWaitTimer(CONNECT_TIMEOUT_MS, 'The interview server did not confirm the session ended. Please try again.')
  }

  const resetToReady = () => {
    clearWaitTimer()
    expectedCloseRef.current = true
    wsRef.current?.close()
    wsRef.current = null
    setErrorMsg(null)
    setStage('ready')
  }

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#FAFAF8', fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif" }}>
      <Nav page="interview" navigate={navigate} />
      <div style={{ maxWidth: 780, margin: '0 auto', padding: '40px clamp(16px, 4vw, 48px)' }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 32 }}>
          <div>
            <p style={{ fontSize: 13, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: '#B5502E', marginBottom: 6 }}>Mock Interview</p>
            <h1 style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 24, fontWeight: 700, color: '#1C1917', margin: 0 }}>Adaptive Session</h1>
          </div>
          {stage !== 'ready' && stage !== 'ended' && (
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: 12, color: '#7A6B63' }}>Turn</div>
              <div style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 24, fontWeight: 700, color: '#B5502E' }}>{turnNumber}</div>
            </div>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 16px', background: 'rgba(181,80,46,0.07)', borderRadius: 10, marginBottom: 28, fontSize: 13, color: '#4B3D37' }}>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <circle cx="7" cy="7" r="6" stroke="#B5502E" strokeWidth="1.4" />
            <path d="M7 4v3l2 1.5" stroke="#B5502E" strokeWidth="1.3" strokeLinecap="round" />
          </svg>
          Questions come live from the interview agent and difficulty adapts to your previous score.
        </div>

        {/* Stage: ready */}
        {stage === 'ready' && (
          <div style={{ background: '#FFFFFF', borderRadius: 20, border: '1.5px solid rgba(181,80,46,0.12)', padding: 32, textAlign: 'center' }}>
            <div style={{ maxWidth: 280, margin: '0 auto 20px' }}>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#4B3D37', marginBottom: 6, textAlign: 'left' }}>Role to practice for</label>
              <input
                value={role}
                onChange={(e) => setRole(e.target.value)}
                style={{ width: '100%', padding: '10px 14px', borderRadius: 12, border: '1.5px solid rgba(181,80,46,0.20)', fontSize: 14, boxSizing: 'border-box', fontFamily: "'Plus Jakarta Sans', sans-serif" }}
              />
            </div>
            <button
              onClick={connectAndStart}
              style={{ background: 'linear-gradient(135deg, #B5502E, #C97350)', border: 'none', cursor: 'pointer', color: '#FAFAF8', fontSize: 15, fontWeight: 700, padding: '14px 36px', borderRadius: 100, fontFamily: "'Plus Jakarta Sans', sans-serif", boxShadow: '0 4px 20px rgba(181,80,46,0.36)' }}
            >
              Begin Interview →
            </button>
          </div>
        )}

        {stage === 'connecting' && <OrbitLoader label="Connecting to interviewer…" size={72} />}

        {stage === 'error' && (
          <div style={{ background: 'rgba(181,80,46,0.06)', border: '1.5px solid rgba(181,80,46,0.20)', borderRadius: 16, padding: 24, textAlign: 'center' }}>
            <p style={{ color: '#B5502E', fontSize: 14, marginBottom: 16 }}>{errorMsg}</p>
            <button onClick={resetToReady} style={{ background: 'none', border: '1.5px solid rgba(181,80,46,0.30)', borderRadius: 100, cursor: 'pointer', padding: '10px 20px', fontSize: 13, fontWeight: 600, color: '#B5502E' }}>
              Try again
            </button>
          </div>
        )}

        {(stage === 'answering' || stage === 'evaluating') && (
          <>
            <div style={{ background: '#FFFFFF', borderRadius: 20, border: '1.5px solid rgba(181,80,46,0.12)', padding: 32, marginBottom: 20, boxShadow: '0 2px 12px rgba(0,0,0,0.05)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
                <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                  {mode === 'devils_advocate' && (
                    <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.10em', textTransform: 'uppercase', color: '#FAFAF8', background: 'linear-gradient(135deg, #1C1917, #3D2419)', padding: '3px 10px', borderRadius: 100 }}>
                      Devil's Advocate
                    </span>
                  )}
                  {stage === 'answering' && (
                    <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.06em', color: '#FAFAF8', background: '#B5502E', padding: '3px 10px', borderRadius: 100, display: 'flex', alignItems: 'center', gap: 4 }}>
                      ⏳ {formatTime(secondsSpent)}
                    </span>
                  )}
                </div>
                <button
                  onClick={speakQuestion}
                  style={{ background: 'rgba(181,80,46,0.08)', border: 'none', borderRadius: 8, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, padding: '6px 12px', fontSize: 12, fontWeight: 600, color: '#B5502E', fontFamily: "'Plus Jakarta Sans', sans-serif" }}
                >
                  {isSpeaking ? (
                    <>
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><rect x="4" y="4" width="16" height="16" rx="2"/></svg>
                      Stop
                    </>
                  ) : (
                    <>
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M11 5L6 9H2v6h4l5 4V5z"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07M19.07 4.93a10 10 0 0 1 0 14.14"/></svg>
                      Read Aloud
                    </>
                  )}
                </button>
              </div>
              <p style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 18, fontWeight: 400, color: '#1C1917', lineHeight: 1.65, margin: 0, fontStyle: 'italic', whiteSpace: 'pre-wrap' }}>
                {question}
              </p>
            </div>

            {stage === 'answering' ? (
              <div>
                <style>{`
                  @keyframes voice-pulse {
                    0% { transform: scale(1); opacity: 1; }
                    50% { transform: scale(1.05); opacity: 0.8; }
                    100% { transform: scale(1); opacity: 1; }
                  }
                `}</style>
                <textarea
                  ref={textareaRef}
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  placeholder="Structure your response as you would in a real interview..."
                  style={{ width: '100%', minHeight: 200, padding: '18px 20px', borderRadius: 14, border: '1.5px solid rgba(181,80,46,0.25)', background: '#FFFFFF', fontSize: 15, color: '#1C1917', lineHeight: 1.65, fontFamily: "'Plus Jakarta Sans', sans-serif", resize: 'vertical', outline: 'none', boxSizing: 'border-box' }}
                />
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 12 }}>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button onClick={handleEnd} style={{ background: 'none', border: '1.5px solid rgba(181,80,46,0.25)', borderRadius: 100, cursor: 'pointer', padding: '11px 20px', fontSize: 13, fontWeight: 600, color: '#7A6B63', fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
                      End Session
                    </button>
                    <button
                      onClick={toggleRecording}
                      style={{
                        background: isRecording ? '#dc2626' : 'none',
                        border: isRecording ? '1.5px solid #dc2626' : '1.5px solid rgba(181,80,46,0.25)',
                        borderRadius: 100,
                        cursor: 'pointer',
                        padding: '11px 20px',
                        fontSize: 13,
                        fontWeight: 600,
                        color: isRecording ? '#FAFAF8' : '#B5502E',
                        fontFamily: "'Plus Jakarta Sans', sans-serif",
                        display: 'flex',
                        alignItems: 'center',
                        gap: 6,
                        transition: 'all 0.2s ease',
                        animation: isRecording ? 'voice-pulse 1.5s infinite ease-in-out' : 'none'
                      }}
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                        <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
                        <path d="M19 10v1a7 7 0 0 1-14 0v-1M12 19v4M8 23h8"/>
                      </svg>
                      {isRecording ? 'Recording...' : 'Answer with Voice'}
                    </button>
                  </div>
                  <button
                    onClick={handleSubmit}
                    disabled={!answer.trim()}
                    style={{ background: answer.trim() ? 'linear-gradient(135deg, #B5502E, #C97350)' : 'rgba(181,80,46,0.25)', border: 'none', cursor: answer.trim() ? 'pointer' : 'not-allowed', color: '#FAFAF8', fontSize: 14, fontWeight: 700, padding: '12px 28px', borderRadius: 100, fontFamily: "'Plus Jakarta Sans', sans-serif" }}
                  >
                    Submit Answer
                  </button>
                </div>
              </div>
            ) : (
              <div>
                <OrbitLoader label="Evaluating your answer…" size={72} />
                {slowWait && (
                  <p style={{ textAlign: 'center', fontSize: 12.5, color: '#7A6B63', marginTop: -8 }}>
                    Still working - real model evaluation can take a couple of minutes.
                  </p>
                )}
              </div>
            )}
          </>
        )}

        {/* Stage: feedback */}
        {stage === 'feedback' && feedback && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {feedback.fallback_used && (
              <div style={{ padding: '10px 16px', background: 'rgba(181,80,46,0.08)', borderRadius: 10, fontSize: 12.5, color: '#B5502E' }}>
                The AI evaluator couldn't fully score this turn - showing a placeholder score.
              </div>
            )}
            <div style={{ display: 'flex', alignItems: 'center', gap: 20, background: '#FFFFFF', borderRadius: 16, border: '1.5px solid rgba(181,80,46,0.12)', padding: '20px 24px' }}>
              <div style={{ textAlign: 'center', flexShrink: 0 }}>
                <div style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 40, fontWeight: 700, color: '#B5502E' }}>{Math.round(feedback.previous_score)}</div>
                <div style={{ fontSize: 11, color: '#7A6B63', fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase' }}>Score</div>
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ height: 8, borderRadius: 4, background: 'rgba(181,80,46,0.12)', overflow: 'hidden', flex: 1, marginRight: 16 }}>
                    <div style={{ height: '100%', width: `${feedback.previous_score}%`, borderRadius: 4, background: 'linear-gradient(90deg, #B5502E, #E0A458)', transition: 'width 1s ease' }} />
                  </div>
                  {lastAnswerDuration !== null && (
                    <span style={{ fontSize: 11, fontWeight: 700, color: '#B5502E', background: 'rgba(181,80,46,0.08)', padding: '2px 8px', borderRadius: 100, flexShrink: 0 }}>
                      ⏱️ {formatTime(lastAnswerDuration)}
                    </span>
                  )}
                </div>
                <p style={{ fontSize: 13, color: '#7A6B63', margin: '8px 0 0', lineHeight: 1.5 }}>{feedback.feedback}</p>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 10 }}>
              {Object.entries(feedback.scores_breakdown).map(([k, v]) => (
                <div key={k} style={{ background: '#FFFFFF', borderRadius: 12, border: '1.5px solid rgba(181,80,46,0.10)', padding: '10px 8px', textAlign: 'center' }}>
                  <div style={{ fontSize: 15, fontWeight: 700, color: '#B5502E', fontFamily: "'Fraunces', Georgia, serif" }}>{Math.round(v)}</div>
                  <div style={{ fontSize: 9, color: '#7A6B63', textTransform: 'capitalize' }}>{k.replace('_method', '')}</div>
                </div>
              ))}
            </div>

            {feedback.weak_topics.length > 0 && (
              <div style={{ background: 'rgba(181,80,46,0.05)', borderRadius: 14, border: '1.5px solid rgba(181,80,46,0.15)', padding: 20 }}>
                <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.10em', textTransform: 'uppercase', color: '#B5502E', marginBottom: 12 }}>Gaps → Notes Generating</div>
                {feedback.weak_topics.map((g) => (
                  <div key={g} style={{ display: 'flex', gap: 8, marginBottom: 8, fontSize: 13, color: '#1C1917' }}>
                    <span style={{ color: '#B5502E', flexShrink: 0 }}>→</span>
                    {g}
                  </div>
                ))}
              </div>
            )}

            <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
              <button onClick={handleEnd} style={{ background: 'none', border: '1.5px solid rgba(181,80,46,0.20)', borderRadius: 100, cursor: 'pointer', padding: '11px 22px', fontSize: 13, fontWeight: 600, color: '#7A6B63', fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
                End Session
              </button>
              <button onClick={() => navigate('notes')} style={{ background: 'none', border: '1.5px solid rgba(181,80,46,0.30)', borderRadius: 100, cursor: 'pointer', padding: '11px 22px', fontSize: 13, fontWeight: 600, color: '#B5502E', fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
                View Generated Notes
              </button>
              <button onClick={handleNext} style={{ background: 'linear-gradient(135deg, #B5502E, #C97350)', border: 'none', cursor: 'pointer', color: '#FAFAF8', fontSize: 13, fontWeight: 700, padding: '11px 22px', borderRadius: 100, fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
                Next Question →
              </button>
            </div>
          </div>
        )}

        {/* Stage: ended */}
        {stage === 'ended' && ended && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div style={{ background: 'linear-gradient(160deg, #1C1917, #2E1F18)', borderRadius: 20, padding: 32, textAlign: 'center' }}>
              <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.10em', textTransform: 'uppercase', color: '#E0A458', marginBottom: 12 }}>Session Complete</div>
              <div style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 48, fontWeight: 700, color: '#FAFAF8' }}>{Math.round(ended.average_score)}</div>
              <div style={{ fontSize: 12, color: 'rgba(250,250,248,0.6)' }}>Average score across the session</div>
            </div>
            <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
              <button onClick={() => navigate('mastery')} style={{ background: 'none', border: '1.5px solid rgba(181,80,46,0.30)', borderRadius: 100, cursor: 'pointer', padding: '11px 22px', fontSize: 13, fontWeight: 600, color: '#B5502E', fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
                View Mastery Map
              </button>
              <button onClick={() => { setStage('ready'); setEnded(null) }} style={{ background: 'linear-gradient(135deg, #B5502E, #C97350)', border: 'none', cursor: 'pointer', color: '#FAFAF8', fontSize: 13, fontWeight: 700, padding: '11px 22px', borderRadius: 100, fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
                Start Another Session
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
