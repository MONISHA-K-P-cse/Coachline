import { useState, useEffect } from 'react'
import { Nav } from '../components/Nav'
import { OrbitLoader } from '../components/OrbitLoader'
import * as api from '../lib/apiClient'
import { motion, AnimatePresence } from 'framer-motion'
import { BookOpen, Star, Trash2, Search, Sparkles, Folder, Play, Plus, RefreshCw } from 'lucide-react'

type Page = 'landing' | 'login' | 'register' | 'onboarding' | 'workspace' | 'roadmap' | 'interview' | 'notes' | 'mastery' | 'mentor'
interface Props { navigate: (p: Page) => void }

function parseBlocks(content: string): { type: string; content: string }[] | null {
  try {
    const parsed = JSON.parse(content)
    if (Array.isArray(parsed)) return parsed
    return null
  } catch {
    return null
  }
}

function renderMarkdown(text: string) {
  const lines = text.split('\n')
  const elements: JSX.Element[] = []
  let listItems: JSX.Element[] = []
  let inCode = false
  let codeLines: string[] = []
  
  const flushList = (keyPrefix: string) => {
    if (listItems.length > 0) {
      elements.push(
        <ul key={`ul-${keyPrefix}`} className="list-disc pl-5 my-2 flex flex-col gap-1.5 text-text-muted">
          {listItems}
        </ul>
      )
      listItems = []
    }
  }

  const formatBold = (str: string) => {
    const parts = str.split('**')
    return parts.map((part, index) => {
      if (index % 2 === 1) {
        return <strong key={index} className="font-bold text-text">{part}</strong>
      }
      return part
    })
  }

  lines.forEach((line, idx) => {
    if (line.trim().startsWith('```')) {
      if (inCode) {
        elements.push(
          <pre key={`code-${idx}`} className="bg-terminal-bg rounded-xl p-4 text-[11px] overflow-x-auto text-accent font-mono border border-border/10 leading-relaxed my-2">
            {codeLines.join('\n')}
          </pre>
        )
        codeLines = []
        inCode = false
      } else {
        inCode = true
      }
      return
    }
    
    if (inCode) {
      codeLines.push(line)
      return
    }

    const trimmed = line.trim()
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ') || trimmed.startsWith('• ')) {
      const content = trimmed.substring(2)
      listItems.push(
        <li key={`li-${idx}`} className="text-xs sm:text-sm text-text-muted">
          {formatBold(content)}
        </li>
      )
    } else {
      flushList(idx.toString())
      
      if (trimmed.startsWith('### ')) {
        elements.push(
          <h4 key={idx} className="text-xs sm:text-sm font-bold text-rust uppercase tracking-wider mt-4 mb-2">
            {formatBold(trimmed.substring(4))}
          </h4>
        )
      } else if (trimmed.startsWith('## ')) {
        elements.push(
          <h3 key={idx} className="text-sm sm:text-base font-bold text-text mt-5 mb-2 border-b border-border/20 pb-1">
            {formatBold(trimmed.substring(3))}
          </h3>
        )
      } else if (trimmed.startsWith('# ')) {
        elements.push(
          <h2 key={idx} className="text-base sm:text-lg font-bold text-text mt-6 mb-3">
            {formatBold(trimmed.substring(2))}
          </h2>
        )
      } else if (trimmed === '') {
        // Empty spacer
      } else {
        elements.push(
          <p key={idx} className="text-xs sm:text-sm text-text-muted leading-relaxed mb-3">
            {formatBold(trimmed)}
          </p>
        )
      }
    }
  })
  
  flushList('end')
  return <div className="flex flex-col">{elements}</div>
}

function NoteBody({ note }: { note: api.NoteResponse }) {
  const blocks = parseBlocks(note.content)
  if (!blocks) {
    return <div className="text-xs sm:text-sm text-text-muted leading-relaxed whitespace-pre-wrap">{renderMarkdown(note.content)}</div>
  }
  return (
    <div className="flex flex-col gap-4 font-sans text-xs sm:text-sm text-text">
      {blocks.map((b, i) => {
        if (b.type === 'diagram') {
          return (
            <pre key={i} className="bg-terminal-bg rounded-xl p-4 text-[11px] overflow-x-auto text-accent font-mono border border-border/10 leading-relaxed my-2">
              {b.content}
            </pre>
          )
        }
        if (b.type === 'exercise') {
          return (
            <div key={i} className="bg-rust/5 border border-rust/20 rounded-xl p-4 my-2">
              <div className="text-[10px] font-bold tracking-wider uppercase text-rust mb-2">Target Exercise</div>
              <div className="margin-0 text-xs text-text leading-relaxed">{renderMarkdown(b.content)}</div>
            </div>
          )
        }
        return <div key={i}>{renderMarkdown(b.content)}</div>
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
  const [searchQuery, setSearchQuery] = useState('')
  const [activeFilter, setActiveFilter] = useState<'all' | 'bookmarks'>('all')

  const load = async () => {
    const data = await api.listNotes()
    setNotes(data)
    if (data.length && selected === null) setSelected(data[0].id)
  }

  useEffect(() => {
    load().finally(() => setLoading(false))
  }, [])

  const runGenerate = async () => {
    if (!topic.trim()) return
    setGenerating(true)
    setSlowGenerate(false)
    setError(null)
    const slowTimer = setTimeout(() => setSlowGenerate(true), 15000)
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
    if (!window.confirm("Are you sure you want to delete this study note?")) return
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

  const filteredNotes = notes.filter((n) => {
    const matchesSearch = n.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          n.category.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesBookmark = activeFilter === 'bookmarks' ? n.is_bookmarked : true
    return matchesSearch && matchesBookmark
  })

  const note = notes.find((n) => n.id === selected)

  if (loading) {
    return (
      <div className="min-h-screen bg-bg">
        <Nav page="notes" navigate={navigate} />
        <OrbitLoader label="Syncing study sheets..." size={80} />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-bg text-text transition-colors duration-300 font-sans flex flex-col h-screen overflow-hidden">
      <Nav page="notes" navigate={navigate} />

      <div className="flex-1 flex overflow-hidden">
        
        {/* Left Sidebar */}
        <aside className="w-80 border-r border-border bg-panel-bg/30 flex flex-col h-full overflow-hidden">
          
          {/* Note Generator Section */}
          <div className="p-4 border-b border-border/80 flex flex-col gap-3">
            <span className="text-[9px] uppercase font-bold tracking-wider text-text-muted">Generate Study Sheet</span>
            <form onSubmit={handleGenerate} className="flex flex-col gap-2">
              <input
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="Topic e.g. Cache Invalidations"
                className="w-full px-3.5 py-2 rounded-xl border border-border/70 bg-bg/50 text-xs focus:outline-none focus:border-rust/80 focus:ring-3 focus:ring-rust/15 transition-all placeholder:text-text-muted/40"
              />
              <button
                type="submit"
                disabled={generating || !topic.trim()}
                className={`w-full py-2 rounded-xl text-white text-xs font-semibold transition-all duration-200 flex items-center justify-center gap-1.5 cursor-pointer ${
                  generating || !topic.trim() ? 'bg-rust/50 cursor-not-allowed' : 'bg-rust hover:bg-rust/90 shadow-sm shadow-rust/15 hover:shadow-md hover:shadow-rust/25 active:scale-[0.98]'
                }`}
              >
                <Plus className="w-3.5 h-3.5" />
                <span>{generating ? 'Generating...' : 'Generate Notes'}</span>
              </button>
            </form>

            {generating && slowGenerate && (
              <p className="text-[10px] text-text-muted/80 leading-normal animate-pulse">
                Generating comprehensive analysis...
              </p>
            )}

            {error && (
              <div className="text-[10px] text-red-500 font-semibold mt-1">
                {error}
                <button 
                  onClick={runGenerate} 
                  className="block text-rust underline cursor-pointer mt-1"
                >
                  Retry
                </button>
              </div>
            )}
          </div>

          {/* Search bar & filter chips */}
          <div className="px-4 py-3 border-b border-border/60 flex flex-col gap-3.5">
            <div className="relative flex items-center">
              <Search className="w-3.5 h-3.5 text-text-muted/70 absolute left-3 pointer-events-none" />
              <input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search study cards..."
                className="w-full pl-9 pr-4 py-1.5 rounded-lg border border-border/70 bg-bg/40 text-xs focus:outline-none focus:border-rust/80 focus:ring-2 focus:ring-rust/10 transition-all placeholder:text-text-muted/40"
              />
            </div>

            <div className="flex gap-2">
              {[
                { id: 'all', label: 'All Cards' },
                { id: 'bookmarks', label: 'Starred' }
              ].map((filter) => (
                <button
                  key={filter.id}
                  onClick={() => setActiveFilter(filter.id as any)}
                  className={`px-3 py-1 rounded-full text-[10px] font-semibold transition-all cursor-pointer border ${
                    activeFilter === filter.id
                      ? 'bg-rust/10 border-rust text-rust'
                      : 'border-border/80 text-text-muted hover:text-text'
                  }`}
                >
                  {filter.label}
                </button>
              ))}
            </div>
          </div>

          {/* Sidebar folders list */}
          <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-2">
            {filteredNotes.length === 0 ? (
              <div className="py-12 text-center text-xs text-text-muted italic">
                No matching study cards.
              </div>
            ) : (
              filteredNotes.map((n) => {
                const isSelected = selected === n.id
                return (
                  <button
                    key={n.id}
                    onClick={() => setSelected(n.id)}
                    className={`w-full flex items-start gap-3 p-3 rounded-xl border text-left transition-all cursor-pointer ${
                      isSelected
                        ? 'border-rust bg-card-bg text-text shadow-sm shadow-rust/5'
                        : 'border-transparent hover:bg-border/20 text-text-muted hover:text-text'
                    }`}
                  >
                    <Folder className={`w-4 h-4 mt-0.5 flex-shrink-0 ${isSelected ? 'text-rust' : 'text-text-muted/60'}`} />
                    <div className="flex-1 min-w-0">
                      <div className="font-bold text-xs leading-normal truncate">{n.title}</div>
                      <div className="text-[10px] text-text-muted/60 mt-1 flex items-center justify-between">
                        <span>{new Date(n.created_at).toLocaleDateString()}</span>
                        {n.is_bookmarked && <Star className="w-3 h-3 text-accent fill-current" />}
                      </div>
                    </div>
                  </button>
                )
              })
            )}
          </div>
        </aside>

        {/* Main Note Sheet View */}
        <main className="flex-1 overflow-y-auto p-8 md:p-12 flex justify-center bg-bg/50">
          <AnimatePresence mode="wait">
            {!note ? (
              <div className="text-center py-32 text-text-muted max-w-sm">
                <BookOpen className="w-8 h-8 mx-auto text-text-muted/40 mb-3" />
                <p className="text-xs">Select a study folder on the sidebar, or search weak topics.</p>
              </div>
            ) : (
              <motion.div
                key={note.id}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -15 }}
                transition={{ duration: 0.3 }}
                className="w-full max-w-2xl bg-card-bg border border-border rounded-2xl p-8 shadow-xl flex flex-col gap-6 relative glass-panel"
              >
                {/* Note metadata headers */}
                <div className="flex items-center justify-between border-b border-border pb-5">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-[9px] uppercase font-bold tracking-wider px-2.5 py-0.5 rounded-full bg-rust/10 text-rust">
                      {note.category}
                    </span>
                    <span className="text-[9px] uppercase font-bold tracking-wider px-2.5 py-0.5 rounded-full bg-border text-text-muted">
                      {note.note_type.replace('_', ' ')}
                    </span>
                  </div>

                  {/* Top actions */}
                  <div className="flex items-center gap-3">
                    <button 
                      onClick={() => handleBookmark(note.id)} 
                      className={`p-2 rounded-lg border border-border cursor-pointer transition-colors ${
                        note.is_bookmarked ? 'bg-accent/15 border-accent text-accent' : 'bg-bg/40 text-text-muted hover:text-text'
                      }`}
                      aria-label="Star card"
                    >
                      <Star className={`w-3.5 h-3.5 ${note.is_bookmarked ? 'fill-current' : ''}`} />
                    </button>
                    <button 
                      onClick={() => handleDelete(note.id)} 
                      className="p-2 rounded-lg border border-border bg-bg/40 hover:bg-red-500/5 hover:border-red-500/30 text-text-muted hover:text-red-500 transition-colors cursor-pointer"
                      title="Delete card"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                {/* Title */}
                <div>
                  <h1 className="font-display text-2xl md:text-3xl font-bold text-text tracking-tight">
                    {note.title}
                  </h1>
                  <span className="text-[10px] text-text-muted/65 mt-1 block">
                    Updated {new Date(note.created_at).toLocaleString()}
                  </span>
                </div>

                {/* Study Body Content */}
                <div className="flex-1">
                  <NoteBody note={note} />
                </div>

                {/* Practice trigger action */}
                <div className="border-t border-border pt-6 mt-6 flex justify-end">
                  <button
                    onClick={() => {
                      localStorage.setItem('active_roadmap_topic', note.title)
                      navigate('interview')
                    }}
                    className="px-5 py-2.5 bg-rust hover:bg-rust/90 text-white rounded-xl text-xs font-bold transition-all shadow-sm shadow-rust/10 flex items-center gap-1.5 cursor-pointer"
                  >
                    <Play className="w-3.5 h-3.5 fill-current" />
                    <span>Practice mock loops</span>
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </main>

      </div>
    </div>
  )
}
