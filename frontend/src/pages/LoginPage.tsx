import { useState } from 'react'
import { authApi } from '../api/client'

interface Props {
  onLogin: (user: any, token: string) => void
}

export default function LoginPage({ onLogin }: Props) {
  const [email, setEmail] = useState('analyst@analytics.local')
  const [password, setPassword] = useState('analyst123')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { data } = await authApi.login(email, password)
      onLogin(data.user, data.access_token)
    } catch (err: any) {
      setError(err.response?.data?.error || 'Ошибка входа')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <h1>Analytics Desk</h1>
        <p className="subtitle">Система аналитической работы</p>
        {error && <div className="error-msg">{error}</div>}
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Email</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <div className="form-group">
            <label>Пароль</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </div>
          <button className="btn btn-primary" style={{ width: '100%', marginTop: 8 }} disabled={loading}>
            {loading ? 'Вход…' : 'Войти'}
          </button>
        </form>
        <p style={{ marginTop: 20, fontSize: 12, color: '#94a3b8', textAlign: 'center' }}>
          Демо: analyst@analytics.local / analyst123
        </p>
      </div>
    </div>
  )
}
