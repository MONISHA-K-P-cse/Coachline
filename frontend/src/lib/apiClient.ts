// Thin fetch wrapper: attaches the JWT, reads the backend base URL from an
// env var, and normalizes errors so callers can just `await` and `catch`.

const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

// Ordinary CRUD calls should fail fast. Calls backed by a live Granite
// generation (resume/roadmap/notes/mentor) can legitimately take up to the
// backend's own ~240s per-call timeout (see GraniteClient.ollama_timeout),
// so their client-side budget is set above that so the backend's own clear
// timeout response arrives first under normal conditions - this is a
// safety net for a request that hangs at the network level instead.
export const DEFAULT_TIMEOUT_MS = 20_000
export const AGENT_TIMEOUT_MS = 260_000

let authToken: string | null = null

export function setAuthToken(token: string | null) {
  authToken = token
}

export class ApiError extends Error {
  status: number
  /** true when this error came from the client giving up (timeout/abort)
   *  rather than a response the server actually sent back. */
  isTimeout: boolean
  constructor(status: number, message: string, isTimeout = false) {
    super(message)
    this.status = status
    this.isTimeout = isTimeout
  }
}

async function request<T>(path: string, options: RequestInit = {}, timeoutMs: number = DEFAULT_TIMEOUT_MS): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> | undefined),
  }
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
  }
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`
  }

  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)

  let res: Response
  try {
    res = await fetch(`${API_BASE_URL}${path}`, { ...options, headers, signal: controller.signal })
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new ApiError(0, 'This is taking longer than expected. Please try again.', true)
    }
    throw new ApiError(0, 'Could not reach the server. Check your connection and try again.')
  } finally {
    clearTimeout(timer)
  }

  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail || detail
    } catch {
      // response wasn't JSON - fall back to statusText
    }
    throw new ApiError(res.status, typeof detail === 'string' ? detail : JSON.stringify(detail))
  }

  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

// ─── Auth ────────────────────────────────────────────────────────────────────

export interface Profile {
  target_role: string | null
  target_company: string | null
  experience_level: string | null
  interview_date: string | null
  bio: string | null
  learning_style: string | null
}

export interface User {
  id: number
  email: string
  full_name: string | null
  created_at: string
  profile: Profile | null
}

export function register(data: {
  email: string
  password: string
  full_name?: string
}): Promise<User> {
  return request('/auth/register', { method: 'POST', body: JSON.stringify(data) })
}

export function login(email: string, password: string): Promise<{ access_token: string; token_type: string }> {
  return request('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) })
}

export function getMe(): Promise<User> {
  return request('/auth/me')
}

export function updateProfile(data: Partial<{
  target_role: string
  target_company: string
  experience_level: string
  interview_date: string
  bio: string
  learning_style: string
}>): Promise<User> {
  return request('/auth/profile', { method: 'PATCH', body: JSON.stringify(data) })
}

// ─── Resume ──────────────────────────────────────────────────────────────────

export interface RewriteSuggestion {
  original: string
  rewritten: string
  reason: string
}

export interface ResumeResponse {
  id: number
  filename: string
  score: number
  ats_score: number
  keyword_count: number
  resume_feedback: string | null
  parsed_text_preview: string | null
  score_details: {
    summary?: string
    strengths?: string[]
    improvements?: string[]
    rewrite_suggestions?: RewriteSuggestion[]
    fallback_used?: boolean
  } | null
  uploaded_at: string
}

export function uploadResume(file: File): Promise<ResumeResponse> {
  const form = new FormData()
  form.append('file', file)
  return request('/resume/upload', { method: 'POST', body: form }, AGENT_TIMEOUT_MS)
}

export function listResumes(): Promise<ResumeResponse[]> {
  return request('/resume/')
}

export interface ResumeImprovementResponse {
  improved_text: string
  changes_made: string[]
}

export function improveResume(resumeId: number): Promise<ResumeImprovementResponse> {
  return request(`/resume/${resumeId}/improve`, { method: 'POST' })
}

export async function downloadImprovedPDF(text: string, filename: string): Promise<void> {
  const url = `${API_BASE_URL}/resume/generate-pdf`
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`
  }

  const res = await fetch(url, {
    method: 'POST',
    headers,
    body: JSON.stringify({ text, filename })
  })

  if (!res.ok) {
    throw new Error('Failed to generate PDF')
  }

  const blob = await res.blob()
  const downloadUrl = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = downloadUrl
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  window.URL.revokeObjectURL(downloadUrl)
}

// ─── Roadmap ─────────────────────────────────────────────────────────────────

export interface RoadmapStep {
  step_number: number
  title: string
  description: string
  estimated_hours: number
  syllabus?: string[]
  questions?: string[]
  notes?: string
  status: string
}

export interface RoadmapResponse {
  id: number
  title: string
  target_role: string
  steps_json: RoadmapStep[]
  progress_percentage: number
  created_at: string
}

export interface PracticeQuestionEvalResponse {
  score: number
  feedback: string
  passed: boolean
  generated_new_question: string | null
  step_questions: string[]
}

export function generateRoadmap(target_role: string, title?: string): Promise<RoadmapResponse> {
  return request('/roadmap/generate', { method: 'POST', body: JSON.stringify({ target_role, title }) }, AGENT_TIMEOUT_MS)
}

export function listRoadmaps(): Promise<RoadmapResponse[]> {
  return request('/roadmap/')
}

export function evaluatePracticeQuestion(
  roadmapId: number,
  stepNumber: number,
  question: string,
  userAnswer: string
): Promise<PracticeQuestionEvalResponse> {
  return request(`/roadmap/${roadmapId}/steps/${stepNumber}/evaluate-question`, {
    method: 'POST',
    body: JSON.stringify({ question, user_answer: userAnswer })
  }, AGENT_TIMEOUT_MS)
}


// ─── Notes ───────────────────────────────────────────────────────────────────

export interface NoteBlock {
  type: 'text' | 'diagram' | 'exercise'
  content: string
}

export interface NoteResponse {
  id: number
  roadmap_id: number | null
  topic: string
  title: string
  content: string
  note_type: string
  category: string
  is_bookmarked: boolean
  created_at: string
}

export function listNotes(bookmarkedOnly = false): Promise<NoteResponse[]> {
  return request(`/notes/?bookmarked_only=${bookmarkedOnly}`)
}

export function generateNote(topic: string, roadmapId?: number): Promise<NoteResponse> {
  const params = new URLSearchParams({ topic })
  if (roadmapId) params.set('roadmap_id', String(roadmapId))
  return request(`/notes/generate?${params.toString()}`, { method: 'POST' }, AGENT_TIMEOUT_MS)
}

export function toggleBookmark(noteId: number): Promise<NoteResponse> {
  return request(`/notes/${noteId}/bookmark`, { method: 'PATCH' })
}

export function deleteNote(noteId: number): Promise<void> {
  return request(`/notes/${noteId}`, { method: 'DELETE' })
}

// ─── Interview ───────────────────────────────────────────────────────────────

export interface InterviewSession {
  id: number
  role: string
  status: string
  average_score: number
  technical_score: number
  communication_score: number
  behavioral_score: number
  confidence_score: number
  star_score: number
  started_at: string
  ended_at: string | null
}

export function listInterviewSessions(): Promise<InterviewSession[]> {
  return request('/interview/sessions')
}

export interface ReplayDiffAttempt {
  session_id: number
  turn_number: number
  question: string
  user_answer: string | null
  score: number
  feedback: string | null
  created_at: string
}

export interface ReplayDiffResult {
  topic: string
  attempt_count: number
  earliest: ReplayDiffAttempt
  latest: ReplayDiffAttempt
  score_delta: number | null
}

export function getReplayDiff(topic: string): Promise<ReplayDiffResult> {
  return request(`/interview/replay-diff/${encodeURIComponent(topic)}`)
}

export function interviewWebSocketUrl(userId: number): string {
  const wsBase = API_BASE_URL.replace(/^http/, 'ws').replace(/\/api$/, '')
  return `${wsBase}/api/interview/ws/${userId}`
}

// ─── Dashboard ───────────────────────────────────────────────────────────────

export interface InterviewScoreBreakdown {
  overall_score: number
  technical_score: number
  communication_score: number
  behavioral_score: number
  confidence_score: number
  star_score: number
}

export interface DashboardSummary {
  user_id: number
  full_name: string | null
  target_role: string | null
  target_company: string | null
  interview_date: string | null
  days_until_interview: number | null
  panic_mode: boolean
  overall_readiness_score: number
  latest_resume_score: number
  latest_ats_score: number
  keyword_count: number
  roadmap_progress_percentage: number
  total_notes_count: number
  bookmarked_notes_count: number
  total_interviews_conducted: number
  interview_scores: InterviewScoreBreakdown
  weak_topics: string[]
  recommendations: string[]
}

export function getDashboard(): Promise<DashboardSummary> {
  return request('/dashboard/')
}

export interface ActivityHeatmapEntry {
  date: string
  interviews: number
  notes: number
  resumes: number
  total: number
}

export function getActivityHeatmap(days = 90): Promise<{ days: ActivityHeatmapEntry[] }> {
  return request(`/dashboard/activity-heatmap?days=${days}`)
}

export interface TopicMasteryEntry {
  topic: string
  mastery_score: number
  needs_regeneration: boolean
  updated_at: string
}

export function getTopicMastery(): Promise<TopicMasteryEntry[]> {
  return request('/dashboard/topic-mastery')
}

// ─── Mentor ──────────────────────────────────────────────────────────────────

export interface MentorMessage {
  id: number
  sender: 'user' | 'mentor'
  message: string
  created_at: string
}

export function sendMentorMessage(message: string): Promise<MentorMessage[]> {
  return request('/mentor/chat', { method: 'POST', body: JSON.stringify({ message }) }, AGENT_TIMEOUT_MS)
}

export function getMentorHistory(): Promise<MentorMessage[]> {
  return request('/mentor/history')
}

export function clearMentorHistory(): Promise<void> {
  return request('/mentor/history', { method: 'DELETE' })
}

export function startNewMentorSession(): Promise<MentorMessage> {
  return request('/mentor/new-session', { method: 'POST' })
}

// ─── IBM Bob ──────────────────────────────────────────────────────────────────

export interface BobVulnerabilityItem {
  severity: string
  line: number
  issue: string
  fix: string
}

export interface BobAuditResponse {
  plan: string[]
  vulnerabilities: BobVulnerabilityItem[]
  refactored_code: string
  score: number
}

export function auditCode(code: string, challengeId: string, language: string = 'python'): Promise<BobAuditResponse> {
  return request('/bob/audit', {
    method: 'POST',
    body: JSON.stringify({ code, challenge_id: challengeId, language })
  }, AGENT_TIMEOUT_MS)
}
