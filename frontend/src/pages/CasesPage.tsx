import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { casesApi } from '../api/client'
import { Plus, Search, Trash2 } from 'lucide-react'

export default function CasesPage() {
  const handleDeleteCase = async (id: number, title: string, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!confirm(`Удалить дело «${title}» и все связанные данные? Это нельзя отменить.`)) return
    try {
      await casesApi.delete(id)
      setCases((prev) => prev.filter((c) => c.id !== id))
    } catch (err: any) {
      alert(err.response?.data?.error || 'Не удалось удалить')
    }
  }

  const [cases, setCases] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({
    title: '',
    organization_name: '',
    bin: '',
    basis: '',
    period_start: '',
    period_end: '',
    subject: '',
  })
  const [error, setError] = useState('')

  const load = () => {
    setLoading(true)
    casesApi.list({ q: q || undefined })
      .then((r) => {
        setCases(r.data.items)
        setTotal(r.data.total)
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      const { data } = await casesApi.create(form)
      setShowForm(false)
      setForm({ title: '', organization_name: '', bin: '', basis: '', period_start: '', period_end: '', subject: '' })
      load()
      window.location.href = `/cases/${data.id}`
    } catch (err: any) {
      setError(err.response?.data?.error || 'Ошибка создания')
    }
  }

  return (
    <>
      <header className="header">
        <h2 style={{ fontSize: 18, fontWeight: 600 }}>Реестр дел</h2>
        <button className="btn btn-primary" onClick={() => setShowForm(true)}>
          <Plus size={16} /> Создать дело
        </button>
      </header>
      <div className="content">
        <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
          <div style={{ position: 'relative', flex: 1, maxWidth: 360 }}>
            <Search size={16} style={{ position: 'absolute', left: 10, top: 10, color: '#94a3b8' }} />
            <input
              style={{ paddingLeft: 34, width: '100%', padding: '8px 12px 8px 34px', border: '1px solid var(--border)', borderRadius: 6 }}
              placeholder="Поиск по номеру, БИН, названию…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && load()}
            />
          </div>
          <button className="btn btn-outline" onClick={load}>Найти</button>
        </div>

        {showForm && (
          <div className="card" style={{ marginBottom: 20 }}>
            <div className="card-title">Новое дело</div>
            {error && <div className="error-msg">{error}</div>}
            <form onSubmit={handleCreate}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                <div className="form-group">
                  <label>Название дела *</label>
                  <input required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
                </div>
                <div className="form-group">
                  <label>Организация</label>
                  <input value={form.organization_name} onChange={(e) => setForm({ ...form, organization_name: e.target.value })} />
                </div>
                <div className="form-group">
                  <label>БИН</label>
                  <input value={form.bin} onChange={(e) => setForm({ ...form, bin: e.target.value })} maxLength={12} />
                </div>
                <div className="form-group">
                  <label>Основание</label>
                  <input value={form.basis} onChange={(e) => setForm({ ...form, basis: e.target.value })} />
                </div>
                <div className="form-group">
                  <label>Период с</label>
                  <input type="date" value={form.period_start} onChange={(e) => setForm({ ...form, period_start: e.target.value })} />
                </div>
                <div className="form-group">
                  <label>Период по</label>
                  <input type="date" value={form.period_end} onChange={(e) => setForm({ ...form, period_end: e.target.value })} />
                </div>
              </div>
              <div className="form-group">
                <label>Предмет анализа</label>
                <textarea rows={2} value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} />
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button type="submit" className="btn btn-primary">Создать</button>
                <button type="button" className="btn btn-outline" onClick={() => setShowForm(false)}>Отмена</button>
              </div>
            </form>
          </div>
        )}

        <div className="card">
          {loading ? (
            <div className="empty">Загрузка…</div>
          ) : cases.length === 0 ? (
            <div className="empty">Дел не найдено</div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Номер</th>
                    <th>Организация</th>
                    <th>БИН</th>
                    <th>Период</th>
                    <th>Статус</th>
                    <th>Обновлено</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {cases.map((c) => (
                    <tr key={c.id}>
                      <td><strong>{c.number}</strong></td>
                      <td>{c.organization_name || '—'}</td>
                      <td>{c.bin || '—'}</td>
                      <td>
                        {c.period_start ? `${c.period_start} — ${c.period_end || '…'}` : '—'}
                      </td>
                      <td><span className={`badge badge-${c.status}`}>{c.status}</span></td>
                      <td>{c.updated_at ? new Date(c.updated_at).toLocaleString('ru') : '—'}</td>
                      <td style={{ display: 'flex', gap: 6 }}>
                        <Link to={`/cases/${c.id}`} className="btn btn-sm btn-outline">Открыть</Link>
                        <button
                          type="button"
                          className="btn btn-sm btn-outline"
                          title="Удалить дело"
                          onClick={(e) => handleDeleteCase(c.id, c.title || c.number, e)}
                          style={{ color: '#dc2626' }}
                        >
                          <Trash2 size={14} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div style={{ marginTop: 12, color: 'var(--text-muted)', fontSize: 13 }}>
            Всего: {total}
          </div>
        </div>
      </div>
    </>
  )
}
