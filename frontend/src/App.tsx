import { useState } from 'react'
import { AuthProvider, useAuth } from './lib/AuthContext'
import Landing from './imports/Landing'
import Login from './imports/Login'
import Register from './imports/Register'
import Onboarding from './imports/Onboarding'
import Workspace from './imports/Workspace'
import Roadmap from './imports/Roadmap'
import Interview from './imports/Interview'
import Notes from './imports/Notes'
import Mastery from './imports/Mastery'
import Mentor from './imports/Mentor'

type Page = 'landing' | 'login' | 'register' | 'onboarding' | 'workspace' | 'roadmap' | 'interview' | 'notes' | 'mastery' | 'mentor'

const AUTH_REQUIRED_PAGES: Page[] = ['onboarding', 'workspace', 'roadmap', 'interview', 'notes', 'mastery', 'mentor']

function AppShell() {
  const [page, setPage] = useState<Page>('landing')
  const { user, loading } = useAuth()

  const navigate = (p: Page) => {
    setPage(p)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  // Auth guard: bounce unauthenticated visitors trying to reach an
  // in-app page to Login instead of rendering it with no user context.
  if (!loading && !user && AUTH_REQUIRED_PAGES.includes(page)) {
    return <Login navigate={navigate} />
  }

  return (
    <>
      {page === 'landing'    && <Landing    navigate={navigate} />}
      {page === 'login'      && <Login      navigate={navigate} />}
      {page === 'register'   && <Register   navigate={navigate} />}
      {page === 'onboarding' && <Onboarding navigate={navigate} />}
      {page === 'workspace'  && <Workspace  navigate={navigate} />}
      {page === 'roadmap'    && <Roadmap    navigate={navigate} />}
      {page === 'interview'  && <Interview  navigate={navigate} />}
      {page === 'notes'      && <Notes      navigate={navigate} />}
      {page === 'mastery'    && <Mastery    navigate={navigate} />}
      {page === 'mentor'     && <Mentor     navigate={navigate} />}
    </>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppShell />
    </AuthProvider>
  )
}
