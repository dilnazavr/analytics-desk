import { Routes, Route, Navigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import Layout from './components/Layout'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import CasesPage from './pages/CasesPage'
import UsersPage from './pages/UsersPage'
import CaseDetailPage from './pages/CaseDetailPage'
import { authApi } from './api/client'

function useAuth() {
  const [user, setUser] = useState<any>(() => {
    const s = localStorage.getItem('user')
    return s ? JSON.parse(s) : null
  })
  const [loading, setLoading] = useState(!!localStorage.getItem('access_token'))

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) {
      setLoading(false)
      return
    }
    authApi.me()
      .then((r) => {
        setUser(r.data)
        localStorage.setItem('user', JSON.stringify(r.data))
      })
      .catch(() => {
        localStorage.removeItem('access_token')
        localStorage.removeItem('user')
        setUser(null)
      })
      .finally(() => setLoading(false))
  }, [])

  const login = (userData: any, token: string) => {
    localStorage.setItem('access_token', token)
    localStorage.setItem('user', JSON.stringify(userData))
    setUser(userData)
  }

  const logout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('user')
    setUser(null)
  }

  return { user, loading, login, logout }
}

export default function App() {
  const auth = useAuth()

  if (auth.loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>
        Загрузка…
      </div>
    )
  }

  if (!auth.user) {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage onLogin={auth.login} />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    )
  }

  return (
    <Routes>
      <Route element={<Layout user={auth.user} onLogout={auth.logout} />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/cases" element={<CasesPage />} />
        <Route path="/users" element={<UsersPage />} />
        <Route path="/cases/:id/*" element={<CaseDetailPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
