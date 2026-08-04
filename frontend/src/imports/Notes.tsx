import { useState, useEffect } from 'react'
import { Nav } from '../components/Nav'
import { OrbitLoader } from '../components/OrbitLoader'
import * as api from '../lib/apiClient'

type Page = 'landing' | 'login' | 'register' | 'onboarding' | 'workspace' | 'roadmap' | 'interview' | 'notes' | 'mastery' | 'mentor'
interface Props { navigate: (p: Page) => void }

// The Notes Agent returns `blocks: [{type, content}]` JSON (see
// ai/agents/notes_agent.py); manually-created notes store plain text
// instead, so we fall back gracefully if content isn't parseable JSON.
function parseBlocks(content: string): { type: string; content: string }[] | null {
  try {
    const parsed = JSON.parse(content)
    if (Array.isArray(parsed)) return parsed
    return null
  } catch {
    return null
  }
}

function NoteBody({ note }: { note: api.NoteResponse }) {
  const blocks = parseBlocks(note.content)
  if (!blocks) {
    return <p style={{ fontSize: 15, color: '#1C1917', lineHeight: 1.8, whiteSpace: 'pre-wrap' }}>{note.content}</p>
  }
  return (
    <div style={{ fontSize: 15, color: '#1C1917', lineHeight: 1.8 }}>
      {blocks.map((b, i) => {
        if (b.type === 'diagram') {
          return (
            <pre key={i} style={{ background: '#F5F2EE', borderRadius: 10, padding: '16px 20px', fontSize: 13, overflowX: 'auto', lineHeight: 1.6, border: '1px solid rgba(181,80,46,0.10)', margin: '16px 0', fontFamily: 'monospace' }}>
              {b.content}
            </pre>
          )
        }
        if (b.type === 'exercise') {
          return (
            <div key={i} style={{ background: 'rgba(181,80,46,0.05)', border: '1.5px solid rgba(181,80,46,0.15)', borderRadius: 12, padding: '16px 18px', margin: '16px 0' }}>
              <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#B5502E', marginBottom: 8 }}>Exercise</div>
              <p style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{b.content}</p>
            </div>
          )
        }
        return <p key={i} style={{ margin: '0 0 16px', whiteSpace: 'pre-wrap' }}>{b.content}</p>
      })}
    </div>
  )
}

export default function Notes({ navigate }: Props) {
  const [notes, setNotes] = useState<api.NoteResponse[]>([])
  const [selected, setSelected] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [topic, setTopic] = useState('')
  const [generating, setGenerating] = useState(false)
  const [slowGenerate, setSlowGenerate] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
    const data = await api.listNotes()
    setNotes(data)
    if (data.length && selected === null) setSelected(data[0].id)
  }

  useEffect(() => {
    load().finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const runGenerate = async () => {
    if (!topic.trim()) return
    setGenerating(true)
    setSlowGenerate(false)
    setError(null)
    // Real generations typically finish in 15-100s; only nudge the user
    // that it's still working (rather than silently spinning) past that.
    const slowTimer = setTimeout(() => setSlowGenerate(true), 15_000)
    try {
      const note = await api.generateNote(topic.trim())
      setTopic('')
      await load()
      setSelected(note.id)
    } catch (err) {
      setError(err instanceof api.ApiError ? err.message : 'Could not generate this note.')
    } finally {
      clearTimeout(slowTimer)
      setSlowGenerate(false)
      setGenerating(false)
    }
  }

  const handleGenerate = (e: React.FormEvent) => {
    e.preventDefault()
    runGenerate()
  }

  const handleBookmark = async (id: number) => {
    await api.toggleBookmark(id)
    await load()
  }

  const handleDelete = async (id: number) => {
    if (!window.confirm("Are you sure you want to delete this note?")) return
    try {
      await api.deleteNote(id)
      const remaining = notes.filter((n) => n.id !== id)
      setNotes(remaining)
      if (remaining.length) {
        setSelected(remaining[0].id)
      } else {
        setSelected(null)
      }
    } catch (err) {
      setError("Could not delete this note.")
    }
  }

  const note = notes.find((n) => n.id === selected)

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', backgroundColor: '#FAFAF8' }}>
        <Nav page="notes" navigate={navigate} />
        <OrbitLoader label="Loading notes…" size={72} />
      </div>
    )
  }

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#FAFAF8', fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif", display: 'flex', flexDirection: 'column' }}>
      <Nav page="notes" navigate={navigate} />
      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '300px 1fr', maxHeight: 'calc(100vh - 64px)' }}>
        {/* Sidebar */}
        <div style={{ borderRight: '1px solid rgba(181,80,46,0.10)', padding: '24px 16px', overflowY: 'auto', background: '#F5F2EE' }}>
          <p style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.10em', textTransform: 'uppercase', color: '#7A6B63', padding: '0 8px', marginBottom: 12 }}>
            Your notes
          </p>

          <form onSubmit={handleGenerate} style={{ padding: '0 8px', marginBottom: 16 }}>
            <input
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="Generate a note on…"
              style={{ width: '100%', padding: '9px 12px', borderRadius: 10, border: '1.5px solid rgba(181,80,46,0.20)', fontSize: 12.5, boxSizing: 'border-box', marginBottom: 6, fontFamily: "'Plus Jakarta Sans', sans-serif" }}
            />
            <button
              type="submit"
              disabled={generating || !topic.trim()}
              style={{ width: '100%', background: generating ? 'rgba(181,80,46,0.4)' : 'linear-gradient(135deg, #B5502E, #C97350)', border: 'none', cursor: generating ? 'not-allowed' : 'pointer', color: '#FAFAF8', fontSize: 12, fontWeight: 700, padding: '8px 0', borderRadius: 100, fontFamily: "'Plus Jakarta Sans', sans-serif" }}
            >
              {generating ? 'Generating…' : 'Generate'}
            </button>
            {generating && slowGenerate && (
              <p style={{ fontSize: 11, color: '#7A6B63', margin: '6px 0 0' }}>
                Still working - real model generation can take a few minutes.
              </p>
            )}
            {error && (
              <div style={{ marginTop: 6 }}>
                <p style={{ fontSize: 11, color: '#B5502E', margin: '0 0 4px' }}>{error}</p>
                <button
                  type="button"
                  onClick={runGenerate}
                  style={{ background: 'none', border: '1px solid rgba(181,80,46,0.30)', borderRadius: 100, cursor: 'pointer', padding: '4px 10px', fontSize: 10.5, fontWeight: 700, color: '#B5502E', fontFamily: "'Plus Jakarta Sans', sans-serif" }}
                >
                  Retry
                </button>
              </div>
            )}
          </form>

          {notes.length === 0 && (
            <p style={{ fontSize: 12.5, color: '#7A6B63', padding: '0 8px' }}>No notes yet. Generate one above, or complete a mock interview to auto-generate notes for weak topics.</p>
          )}

          {notes.map((n) => (
            <button
              key={n.id}
              onClick={() => setSelected(n.id)}
              style={{ display: 'block', width: '100%', textAlign: 'left', padding: '14px 12px', borderRadius: 12, background: selected === n.id ? '#FFFFFF' : 'none', border: selected === n.id ? '1.5px solid rgba(181,80,46,0.20)' : '1.5px solid transparent', cursor: 'pointer', marginBottom: 4, boxShadow: selected === n.id ? '0 2px 8px rgba(0,0,0,0.05)' : 'none', fontFamily: "'Plus Jakarta Sans', sans-serif" }}
            >
              <div style={{ fontSize: 13, fontWeight: 600, color: '#1C1917', lineHeight: 1.4, marginBottom: 5 }}>{n.title}</div>
              <div style={{ fontSize: 11, color: '#7A6B63', marginBottom: 6 }}>{new Date(n.created_at).toLocaleDateString()}</div>
              <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#B5502E', background: 'rgba(181,80,46,0.09)', padding: '2px 8px', borderRadius: 100 }}>{n.category}</span>
              {n.is_bookmarked && <span style={{ marginLeft: 6 }}>★</span>}
            </button>
          ))}
        </div>

        {/* Main note view */}
        <div style={{ padding: '36px 48px', overflowY: 'auto' }}>
          {!note ? (
            <p style={{ color: '#7A6B63' }}>Select a note, or generate one for a topic you want to study.</p>
          ) : (
            <div style={{ maxWidth: 680 }}>
              <div style={{ display: 'flex', alignItems: 'center', width: '100%', gap: 10 }}>
                <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.10em', textTransform: 'uppercase', color: '#B5502E', background: 'rgba(181,80,46,0.09)', padding: '4px 12px', borderRadius: 100 }}>{note.category}</span>
                <button onClick={() => handleBookmark(note.id)} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 16, color: note.is_bookmarked ? '#E0A458' : '#C4BAB3' }}>★</button>
                <button onClick={() => handleDelete(note.id)} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 13, color: '#7A6B63', marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 4, fontWeight: 600, fontFamily: "'Plus Jakarta Sans', sans-serif" }} title="Delete Note">
                  <span style={{ fontSize: 14 }}>🗑️</span> Delete
                </button>
              </div>
              <h2 style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 24, fontWeight: 700, color: '#1C1917', margin: '16px 0 6px', lineHeight: 1.3 }}>{note.title}</h2>
              <p style={{ fontSize: 13, color: '#7A6B63', margin: '0 0 28px' }}>{note.note_type.replace('_', ' ')} · {new Date(note.created_at).toLocaleString()}</p>

              <NoteBody note={note} />

              <div style={{ marginTop: 32, display: 'flex', gap: 12 }}>
                <button onClick={() => navigate('interview')} style={{ background: 'linear-gradient(135deg, #B5502E, #C97350)', border: 'none', cursor: 'pointer', color: '#FAFAF8', fontSize: 13, fontWeight: 700, padding: '10px 20px', borderRadius: 100, fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
                  Practice this topic →
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
