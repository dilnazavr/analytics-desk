import { useEffect, useState } from 'react'
import { usersApi } from '../api/client'
import { Plus, Trash2, Save } from 'lucide-react'

export default function UsersPage() {
  const [users, setUsers] = useState<any[]>([])
  const [roles, setRoles] = useState<any[]>([])
  const [error, setError] = useState('')
  const [msg, setMsg] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({
    email: '',
    full_name: '',
    password: '',
    role: 'analyst',
  })
  const [editId, setEditId] = useState<number | null>(null)
  const [edit, setEdit] = useState({ full_name: '', password: '', role: 'analyst', is_active: true })

  const load = () => {
    setError('')
    usersApi
      .list()
      .then((r) => setUsers(r.data))
      .catch((e) => setError(e.response?.data?.error || 'Нет доступа (нужен admin)'))
    usersApi.roles().then((r) => setRoles(r.data)).catch(() => {})
  }

  useEffect(() => {
    load()
  }, [])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      await usersApi.create(form)
      setShowForm(false)
      setForm({ email: '', full_name: '', password: '', role: 'analyst' })
      setMsg('Пользователь создан')
      load()
    } catch (err: any) {
      setError(err.response?.data?.error || 'Ошибка создания')
    }
  }

  const handleSaveEdit = async (id: number) => {
    try {
      const payload: any = {
        full_name: edit.full_name,
        role: edit.role,
        is_active: edit.is_active,
      }
      if (edit.password) payload.password = edit.password
      await usersApi.update(id, payload)
      setEditId(null)
      setMsg('Сохранено')
      load()
    } catch (err: any) {
      setError(err.response?.data?.error || 'Ошибка сохранения')
    }
  }

  const handleDelete = async (id: number, email: string) => {
    if (!confirm(`Удалить пользователя ${email}?`)) return
    try {
      await usersApi.delete(id)
      setMsg('Удалён')
      load()
    } catch (err: any) {
      setError(err.response?.data?.error || 'Ошибка удаления')
    }
  }

  return (
    <>
      <header className="header">
        <h2 style={{ fontSize: 18, fontWeight: 600 }}>Пользователи</h2>
        <button className="btn btn-primary" onClick={() => setShowForm(true)}>
          <Plus size={16} /> Добавить
        </button>
      </header>
      <div className="content">
        {error && <div className="error-msg">{error}</div>}
        {msg && <div className="success-msg">{msg}</div>}

        {showForm && (
          <div className="card" style={{ marginBottom: 16 }}>
            <div className="card-title">Новый пользователь</div>
            <form onSubmit={handleCreate} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div className="form-group">
                <label>Email</label>
                <input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
              </div>
              <div className="form-group">
                <label>ФИО</label>
                <input required value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
              </div>
              <div className="form-group">
                <label>Пароль (мин. 6)</label>
                <input required type="password" minLength={6} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
              </div>
              <div className="form-group">
                <label>Роль</label>
                <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
                  <option value="analyst">analyst</option>
                  <option value="admin">admin</option>
                  {roles.filter((r) => !['admin', 'analyst'].includes(r.name)).map((r) => (
                    <option key={r.id} value={r.name}>{r.name}</option>
                  ))}
                </select>
              </div>
              <div style={{ gridColumn: '1 / -1', display: 'flex', gap: 8 }}>
                <button type="submit" className="btn btn-primary">Создать</button>
                <button type="button" className="btn btn-outline" onClick={() => setShowForm(false)}>Отмена</button>
              </div>
            </form>
          </div>
        )}

        <div className="card">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Email</th>
                  <th>ФИО</th>
                  <th>Роль</th>
                  <th>Активен</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td>{u.id}</td>
                    <td>{u.email}</td>
                    <td>
                      {editId === u.id ? (
                        <input value={edit.full_name} onChange={(e) => setEdit({ ...edit, full_name: e.target.value })} />
                      ) : (
                        u.full_name
                      )}
                    </td>
                    <td>
                      {editId === u.id ? (
                        <select value={edit.role} onChange={(e) => setEdit({ ...edit, role: e.target.value })}>
                          <option value="analyst">analyst</option>
                          <option value="admin">admin</option>
                        </select>
                      ) : (
                        u.role?.name || '—'
                      )}
                    </td>
                    <td>
                      {editId === u.id ? (
                        <input type="checkbox" checked={edit.is_active} onChange={(e) => setEdit({ ...edit, is_active: e.target.checked })} />
                      ) : u.is_active ? (
                        'да'
                      ) : (
                        'нет'
                      )}
                    </td>
                    <td style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      {editId === u.id ? (
                        <>
                          <input
                            type="password"
                            placeholder="Новый пароль"
                            value={edit.password}
                            onChange={(e) => setEdit({ ...edit, password: e.target.value })}
                            style={{ width: 120 }}
                          />
                          <button type="button" className="btn btn-sm btn-primary" onClick={() => handleSaveEdit(u.id)}>
                            <Save size={14} />
                          </button>
                          <button type="button" className="btn btn-sm btn-outline" onClick={() => setEditId(null)}>
                            Отмена
                          </button>
                        </>
                      ) : (
                        <>
                          <button
                            type="button"
                            className="btn btn-sm btn-outline"
                            onClick={() => {
                              setEditId(u.id)
                              setEdit({
                                full_name: u.full_name,
                                password: '',
                                role: u.role?.name || 'analyst',
                                is_active: !!u.is_active,
                              })
                            }}
                          >
                            Изменить
                          </button>
                          <button
                            type="button"
                            className="btn btn-sm btn-outline"
                            style={{ color: '#dc2626' }}
                            onClick={() => handleDelete(u.id, u.email)}
                          >
                            <Trash2 size={14} />
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <p style={{ marginTop: 12, fontSize: 13, color: 'var(--text-muted)' }}>
          Раздел доступен только роли <b>admin</b>. Войдите как admin@analytics.local
        </p>
      </div>
    </>
  )
}
