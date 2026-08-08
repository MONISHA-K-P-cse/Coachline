import { useState, useRef, useEffect } from 'react'
import { Nav } from '../components/Nav'
import { OrbitLoader } from '../components/OrbitLoader'
import { useAuth } from '../lib/AuthContext'
import { interviewWebSocketUrl } from '../lib/apiClient'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Video, Mic, MicOff, Volume2, StopCircle, RefreshCw, 
  ArrowRight, Award, Clock, Star, Flame, CheckCircle, BarChart3, AlertCircle 
} from 'lucide-react'

type Page = 'landing' | 'login' | 'register' | 'onboarding' | 'workspace' | 'roadmap' | 'interview' | 'notes' | 'mastery' | 'mentor'
interface Props { navigate: (p: Page) => void }

type Stage = 'ready' | 'connecting' | 'answering' | 'evaluating' | 'feedback' | 'ended' | 'error'

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
  const [unlockedNextWeek, setUnlockedNextWeek] = useState(false)
  const [practiceWeek, setPracticeWeek] = useState<number | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const waitTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const slowTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
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

  const armWaitTimer = (ms: number, message: string) => {
    clearWaitTimer()
    if (ms > 20000) {
      slowTimerRef.current = setTimeout(() => setSlowWait(true), 20000)
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
        if (selectedVoice) {
          utterance.voice = selectedVoice
        }
        utterance.rate = 1.05
        utterance.pitch = 1.0
        
        utterance.onend = () => {
          setIsSpeaking(false)
        }
        utterance.onerror = () => {
          setIsSpeaking(false)
        }
        
        setIsSpeaking(true)
        window.speechSynthesis.speak(utterance)
      }
    } else {
      alert('Text-to-speech is not supported in this browser.')
    }
  }

  const toggleRecording = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SpeechRecognition) {
      alert('Speech recognition is not supported in this browser. Please type your answer.')
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
      rec.onresult = (e: any) => {
        let finalTrans = ''
        for (let i = e.resultIndex; i < e.results.length; ++i) {
          if (e.results[i].isFinal) {
            finalTrans += e.results[i][0].transcript + ' '
          }
        }
        if (finalTrans) {
          setAnswer(prev => prev + finalTrans)
        }
      }
      rec.onerror = (e: any) => {
        console.error('Speech recognition error', e)
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
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel()
    }
    setIsSpeaking(false)
    setIsRecording(false)
    setAnswer('')
    setErrorMsg(null)
    setFeedback(null)
    setEnded(null)
    setTurnNumber(1)
    setUnlockedNextWeek(false)

    const savedWeek = localStorage.getItem('active_roadmap_week')
    const savedTopic = localStorage.getItem('active_roadmap_topic')
    const weekVal = savedWeek ? parseInt(savedWeek) : 1
    setPracticeWeek(weekVal)

    setStage('connecting')
    armWaitTimer(15000, "Timed out establishing secure connection to IBM interview agent.")
    expectedCloseRef.current = false

    const ws = new WebSocket(interviewWebSocketUrl(user.id))
    wsRef.current = ws

    ws.onopen = () => {
      localStorage.setItem('active_roadmap_week_for_unlock', weekVal.toString())
      ws.send(JSON.stringify({
        event: 'start',
        role,
        week: weekVal,
        topic: savedTopic || undefined
      }))
      localStorage.removeItem('active_roadmap_week')
      localStorage.removeItem('active_roadmap_topic')
      armWaitTimer(15000, 'The interview server accepted the connection but never sent a question. Please try again.')
    }

    ws.onmessage = (e) => {
      clearWaitTimer()
      try {
        const data = JSON.parse(e.data)
        if (data.event === 'question') {
          if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel()
            setIsSpeaking(false)
          }
          setQuestion(data.question)
          setTurnNumber(data.turn_number)
          setMode(data.mode ?? 'standard')
          setAnswer('')
          setStage('answering')
          
          setTimeout(() => {
            if ('speechSynthesis' in window) {
              window.speechSynthesis.cancel()
              const cleanText = data.question.replace(/[*#_`]/g, '')
              const utterance = new SpeechSynthesisUtterance(cleanText)
              utterance.onend = () => setIsSpeaking(false)
              utterance.onerror = () => setIsSpeaking(false)
              setIsSpeaking(true)
              window.speechSynthesis.speak(utterance)
            }
          }, 300)
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
          
          const weekForUnlock = localStorage.getItem('active_roadmap_week_for_unlock')
          if (weekForUnlock) {
            const completedWeek = parseInt(weekForUnlock)
            const currentUnlocked = parseInt(localStorage.getItem('roadmap_max_unlocked') || '1')
            if (completedWeek === currentUnlocked && data.average_score >= 50) {
              localStorage.setItem('roadmap_max_unlocked', (completedWeek + 1).toString())
              setUnlockedNextWeek(true)
            }
            localStorage.removeItem('active_roadmap_week_for_unlock')
          }

          setEnded({
            average_score: data.average_score,
            scores_breakdown: data.scores_breakdown
          })
          setStage('ended')
          ws.close()
        } else if (data.event === 'error') {
          setErrorMsg(data.message)
          setStage('error')
        }
      } catch (err) {
        console.error('Socket JSON error', err)
      }
    }

    ws.onclose = () => {
      clearWaitTimer()
      if (!expectedCloseRef.current) {
        setErrorMsg("WebSocket connection closed unexpectedly.")
        setStage('error')
      }
    }

    ws.onerror = () => {
      clearWaitTimer()
      setErrorMsg("Failed to connect to mock interview agent.")
      setStage('error')
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
    armWaitTimer(520000, "Evaluation calculation timed out. Retrying...")
  }

  const handleEnd = () => {
    if (isRecording) {
      recognitionRef.current?.stop()
      setIsRecording(false)
    }
    expectedCloseRef.current = true
    wsRef.current?.send(JSON.stringify({ event: 'end' }))
    armWaitTimer(15000, 'The interview server did not confirm the session ended. Please try again.')
  }

  const nextQuestion = () => {
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

  const resetToReady = () => {
    clearWaitTimer()
    expectedCloseRef.current = true
    wsRef.current?.close()
    wsRef.current = null
    setErrorMsg(null)
    setStage('ready')
  }

  return (
    <div className="min-h-screen bg-bg text-text transition-colors duration-300 font-sans pb-16">
      <Nav page="interview" navigate={navigate} />

      <div className="max-w-4xl mx-auto px-6 pt-10">
        
        {/* Header Banner */}
        <div className="flex items-center justify-between gap-6 mb-8 border-b border-border/50 pb-6">
          <div>
            <span className="text-[10px] uppercase font-bold tracking-wider text-rust">Mock Simulation</span>
            <h1 className="font-display text-3xl font-bold tracking-tight text-text mt-0.5">Mock Interview Agent</h1>
          </div>
          {stage !== 'ready' && stage !== 'ended' && (
            <div className="bg-panel-bg px-4 py-2 rounded-xl border border-border text-center">
              <span className="text-[9px] uppercase font-bold text-text-muted tracking-wider">Question Turn</span>
              <span className="block font-display text-lg font-bold text-rust">{turnNumber}</span>
            </div>
          )}
        </div>

        {/* ── STAGE: READY ────────────────────────────────────────────────── */}
        {stage === 'ready' && (
          <div className="p-8 rounded-2xl border border-border bg-card-bg/60 glass-panel flex flex-col md:flex-row items-center gap-8">
            <div className="flex-1">
              <h2 className="font-display text-xl font-bold text-text">Initialize mock environment</h2>
              <p className="text-xs text-text-muted mt-2 leading-relaxed">
                Configure your target role. CoachLine will run agent loops designed with customizable parameters for company standards.
              </p>
              
              <div className="mt-6 w-full max-w-sm">
                <label className="text-[10px] font-bold uppercase tracking-wider text-text-muted mb-1.5 block">Role Target</label>
                <input
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  className="w-full px-3 py-2.5 rounded-xl border border-border bg-bg/50 text-xs font-semibold text-text focus:outline-none focus:border-rust/80 transition-colors"
                />
              </div>

              <button
                onClick={connectAndStart}
                className="mt-6 px-6 py-3 bg-rust hover:bg-rust/90 text-white rounded-xl text-xs font-bold transition-all shadow-md shadow-rust/15 flex items-center gap-1.5 cursor-pointer"
              >
                <span>Launch Agent Session</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>

            {/* Video Call Mock Avatar Frame */}
            <div className="w-full md:w-72 aspect-video bg-terminal-bg rounded-2xl border border-border/80 flex items-center justify-center relative overflow-hidden shadow-2xl">
              <div className="absolute inset-0 bg-gradient-to-tr from-rust/10 via-transparent to-transparent pointer-events-none" />
              <div className="w-12 h-12 rounded-full bg-rust/20 border border-rust/40 flex items-center justify-center animate-pulse">
                <Video className="w-5 h-5 text-rust" />
              </div>
              <span className="absolute bottom-3 left-3 text-[9px] font-bold text-text-muted/80 uppercase font-mono tracking-wider">
                Coach Avatar Feed
              </span>
            </div>
          </div>
        )}

        {/* ── STAGE: CONNECTING ────────────────────────────────────────────── */}
        {stage === 'connecting' && (
          <div className="p-8 rounded-2xl border border-border bg-card-bg/60 glass-panel">
            <OrbitLoader label="Connecting socket feed..." size={70} />
          </div>
        )}

        {/* ── STAGE: ERROR ────────────────────────────────────────────────── */}
        {stage === 'error' && (
          <div className="p-8 rounded-2xl border border-red-500/20 bg-red-500/5 text-center flex flex-col items-center gap-4">
            <AlertCircle className="w-8 h-8 text-red-500" />
            <h3 className="font-display text-base font-bold text-text">Connection Error</h3>
            <p className="text-xs text-text-muted max-w-sm leading-relaxed">{errorMsg}</p>
            <button
              onClick={resetToReady}
              className="px-4 py-2 border border-border hover:bg-border/20 text-xs font-semibold text-text rounded-lg transition-colors cursor-pointer"
            >
              Try Again
            </button>
          </div>
        )}

        {/* ── STAGE: ANSWERING / EVALUATING ───────────────────────────────── */}
        {(stage === 'answering' || stage === 'evaluating') && (
          <div className="flex flex-col gap-6">
            
            {/* Split layout: Avatar & Question Details */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              
              {/* Avatar Feeds with dynamic voice indicators */}
              <div className="md:col-span-1 bg-terminal-bg rounded-2xl border border-border/80 p-5 flex flex-col justify-between min-h-[160px] relative overflow-hidden shadow-xl">
                <div className="absolute inset-0 bg-gradient-to-tr from-rust/5 to-transparent pointer-events-none" />
                <div className="flex items-center justify-between">
                  <span className="text-[9px] uppercase font-bold tracking-wider text-text-muted/65 font-mono">Interviewer feed</span>
                  <button
                    onClick={speakQuestion}
                    className="p-1.5 rounded-lg bg-bg/10 hover:bg-bg/25 text-rust transition-colors cursor-pointer"
                    title={isSpeaking ? "Mute" : "Speak text"}
                  >
                    <Volume2 className={`w-3.5 h-3.5 ${isSpeaking ? 'animate-bounce' : ''}`} />
                  </button>
                </div>

                {/* Speaker indicator balls */}
                <div className="flex justify-center my-6">
                  {isSpeaking ? (
                    <div className="flex items-center gap-1.5 h-8">
                      {[0.1, 0.3, 0.5, 0.2].map((delay, i) => (
                        <div 
                          key={i} 
                          className="w-1.5 bg-rust rounded-full" 
                          style={{ 
                            height: '100%', 
                            animation: 'speak-bar-bounce 0.6s infinite ease-in-out',
                            animationDelay: `${delay}s` 
                          }} 
                        />
                      ))}
                    </div>
                  ) : (
                    <div className="w-10 h-10 rounded-full bg-rust/15 border border-rust/35 flex items-center justify-center">
                      <div className="w-4 h-4 rounded-full bg-rust animate-pulse" />
                    </div>
                  )}
                </div>

                <div className="flex items-center justify-between text-[9px] text-text-muted font-bold tracking-wider">
                  <span className="uppercase">Agentic Granite</span>
                  {stage === 'answering' && (
                    <span className="bg-rust/20 text-rust px-1.5 py-0.5 rounded-md font-mono">
                      ⏳ {formatTime(secondsSpent)}
                    </span>
                  )}
                </div>
              </div>

              {/* Question panel */}
              <div className="md:col-span-2 p-6 rounded-2xl border border-border bg-card-bg/60 glass-panel flex flex-col justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-[9px] uppercase font-bold tracking-wider text-rust">Active Question</span>
                    {mode === 'devils_advocate' && (
                      <span className="text-[8px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-terminal-bg text-accent">
                        Devil\'s Advocate Mode
                      </span>
                    )}
                  </div>
                  <p className="font-display text-sm md:text-base text-text leading-relaxed mt-3 italic">
                    "{question}"
                  </p>
                </div>
              </div>
            </div>

            {/* Answer workspace */}
            {stage === 'answering' ? (
              <div className="flex flex-col gap-4">
                <textarea
                  ref={textareaRef}
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  placeholder="Structure your answer, highlight context examples..."
                  className="w-full min-h-[160px] p-5 rounded-2xl border border-border bg-card-bg/60 text-xs sm:text-sm text-text leading-relaxed outline-none focus:border-rust/60 transition-colors resize-y glass-panel"
                />

                <div className="flex justify-between items-center gap-4">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleEnd}
                      className="px-4 py-2 border border-border hover:bg-red-500/5 hover:text-red-500 hover:border-red-500/20 text-xs font-semibold text-text-muted rounded-xl transition-all cursor-pointer flex items-center gap-1"
                    >
                      <StopCircle className="w-3.5 h-3.5" />
                      <span>End Interview</span>
                    </button>
                    <button
                      onClick={toggleRecording}
                      className={`px-4 py-2 border text-xs font-semibold rounded-xl transition-all flex items-center gap-1.5 cursor-pointer ${
                        isRecording 
                          ? 'bg-red-500 border-red-500 text-white animate-pulse' 
                          : 'border-rust/45 hover:bg-rust/5 text-rust'
                      }`}
                    >
                      {isRecording ? <MicOff className="w-3.5 h-3.5" /> : <Mic className="w-3.5 h-3.5" />}
                      <span>{isRecording ? 'Mute' : 'Speak answer'}</span>
                    </button>
                  </div>

                  <button
                    onClick={handleSubmit}
                    disabled={!answer.trim()}
                    className={`px-5 py-2.5 rounded-xl text-white text-xs font-bold transition-all cursor-pointer ${
                      answer.trim() ? 'bg-rust hover:bg-rust/90 shadow' : 'bg-rust/40 cursor-not-allowed'
                    }`}
                  >
                    Submit response
                  </button>
                </div>
              </div>
            ) : (
              <div className="p-8 rounded-2xl border border-border bg-card-bg/60 glass-panel">
                <OrbitLoader label="Agent scoring response..." size={64} />
              </div>
            )}
          </div>
        )}

        {/* ── STAGE: FEEDBACK ─────────────────────────────────────────────── */}
        {stage === 'feedback' && feedback && (
          <div className="flex flex-col gap-6">
            
            {/* Feedback Core Score card */}
            <div className="p-6 rounded-2xl border border-border bg-card-bg/60 glass-panel flex flex-col md:flex-row items-center justify-between gap-6">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-[10px] uppercase font-bold tracking-wider text-rust">Turn Feedback</span>
                  {feedback.fallback_used && (
                    <span className="text-[8px] uppercase tracking-wider text-red-500 bg-red-500/10 px-2 py-0.5 rounded-full font-bold">
                      Calculated rating
                    </span>
                  )}
                </div>
                <p className="text-xs sm:text-sm text-text leading-relaxed">
                  {feedback.feedback}
                </p>
              </div>

              <div className="flex items-center gap-4 flex-shrink-0">
                {lastAnswerDuration !== null && (
                  <div className="bg-panel-bg border border-border px-3 py-1.5 rounded-xl text-center">
                    <span className="text-[9px] uppercase font-semibold text-text-muted">Duration</span>
                    <span className="block font-mono text-xs font-bold text-text mt-0.5">{formatTime(lastAnswerDuration)}</span>
                  </div>
                )}
                <div className="bg-rust/15 border border-rust/35 w-20 h-20 rounded-full flex flex-col items-center justify-center">
                  <span className="font-display text-2xl font-bold text-rust">{Math.round(feedback.previous_score)}</span>
                  <span className="text-[8px] uppercase tracking-wider font-bold text-rust/80">Score</span>
                </div>
              </div>
            </div>

            {/* Score Breakdowns Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
              {Object.entries(feedback.scores_breakdown).map(([key, score]) => (
                <div key={key} className="p-4 rounded-xl border border-border bg-card-bg/60 glass-panel text-center">
                  <span className="text-[9px] uppercase font-bold text-text-muted tracking-wider block mb-1">
                    {key.replace('_', ' ')}
                  </span>
                  <span className="font-display text-base font-bold text-rust">{Math.round(score)}%</span>
                </div>
              ))}
            </div>

            {/* Actions for next step */}
            <div className="flex items-center justify-between border-t border-border pt-6 mt-4">
              <button
                onClick={handleEnd}
                className="px-4 py-2 border border-border hover:bg-red-500/5 hover:text-red-500 hover:border-red-500/20 text-xs font-semibold text-text-muted rounded-xl transition-all cursor-pointer"
              >
                End loop session
              </button>
              <button
                onClick={nextQuestion}
                className="px-5 py-2.5 bg-rust hover:bg-rust/90 text-white rounded-xl text-xs font-bold transition-all shadow flex items-center gap-1.5 cursor-pointer"
              >
                <span>Request next question</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}

        {/* ── STAGE: ENDED ────────────────────────────────────────────────── */}
        {stage === 'ended' && ended && (
          <div className="flex flex-col gap-6">
            
            {/* Session Summary Card */}
            <div className="p-8 rounded-2xl border border-border bg-card-bg/60 glass-panel text-center flex flex-col items-center gap-3">
              <CheckCircle className="w-10 h-10 text-green-500" />
              <h2 className="font-display text-xl font-bold text-text">Session completed successfully</h2>
              <p className="text-xs text-text-muted max-w-sm leading-relaxed mt-1">
                Your performance scores have been mapped to target topics. Weak domain cards have been initialized inside the Galaxy constellation.
              </p>
              {unlockedNextWeek && (
                <div className="p-3 bg-green-500/10 border border-green-500/20 rounded-xl text-green-500 text-xs font-semibold mt-3">
                  🎉 Achievement: Next study milestone unlocked!
                </div>
              )}
            </div>

            {/* Performance breakdowns */}
            <div className="p-6 rounded-2xl border border-border bg-card-bg/60 glass-panel">
              <h3 className="font-display text-base font-bold text-text mb-6 text-center">Cumulative Competency</h3>
              
              <div className="flex flex-col sm:flex-row items-center justify-around gap-8">
                {/* Total Avg Score ring */}
                <div className="relative flex items-center justify-center w-32 h-32 flex-shrink-0">
                  <svg className="w-full h-full transform -rotate-90">
                    <circle cx="64" cy="64" r="54" stroke="var(--border)" strokeWidth="6" fill="transparent" />
                    <circle 
                      cx="64" 
                      cy="64" 
                      r="54" 
                      stroke="var(--rust)" 
                      strokeWidth="6" 
                      fill="transparent" 
                      strokeDasharray="339"
                      strokeDashoffset={339 - (339 * ended.average_score) / 100}
                      strokeLinecap="round"
                    />
                  </svg>
                  <div className="absolute text-center">
                    <span className="font-display text-3xl font-bold text-rust">{Math.round(ended.average_score)}%</span>
                    <span className="block text-[8px] uppercase tracking-wider font-semibold text-text-muted mt-0.5">Average</span>
                  </div>
                </div>

                {/* Breakdown metrics list */}
                <div className="flex-1 flex flex-col gap-4 w-full">
                  {Object.entries(ended.scores_breakdown).map(([key, score]) => (
                    <div key={key}>
                      <div className="flex justify-between text-xs font-semibold text-text-muted mb-1.5 capitalize">
                        <span>{key.replace('_', ' ')}</span>
                        <span>{Math.round(score)}%</span>
                      </div>
                      <div className="w-full h-1.5 bg-border/40 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-rust" 
                          style={{ width: `${score}%` }} 
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Return action bar */}
            <div className="flex justify-center mt-6">
              <button
                onClick={resetToReady}
                className="px-6 py-3 bg-rust hover:bg-rust/90 text-white rounded-xl text-xs font-bold transition-all shadow-md shadow-rust/10 cursor-pointer"
              >
                Return to Interview Home
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
