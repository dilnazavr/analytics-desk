import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { dashboardApi } from '../api/client'
import { Plus, FolderOpen } from 'lucide-react'

export default function DashboardPage() {
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    dashboardApi.stats()
      .then((r) => setStats(r.data))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="content">Загрузка…</div>

  return (
    <>
      <header className="header">
        <h2 style={{ fontSize: 18, fontWeight: 600 }}>Главная панель</h2>
        <Link to="/cases" className="btn btn-primary">
          <Plus size={16} /> Создать дело
        </Link>
      </header>
      <div className="content">
        <div className="stats-grid">
          <div className="stat-card">
            <div className="label">Открытые дела</div>
            <div className="value">{stats?.open_cases ?? 0}</div>
          </div>
          <div className="stat-card">
            <div className="label">На проверке</div>
            <div className="value">{stats?.review_cases ?? 0}</div>
          </div>
          <div className="stat-card">
            <div className="label">Подготовка справки</div>
            <div className="value">{stats?.report_ready ?? 0}</div>
          </div>
          <div className="stat-card">
            <div className="label">Обработано файлов</div>
            <div className="value">{stats?.files_processed ?? 0}</div>
          </div>
        </div>

        <div className="card">
          <div className="card-title">Последние дела</div>
          {stats?.recent_cases?.length ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Номер</th>
                    <th>Название</th>
                    <th>Организация</th>
                    <th>Статус</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {stats.recent_cases.map((c: any) => (
                    <tr key={c.id}>
                      <td>{c.number}</td>
                      <td>{c.title}</td>
                      <td>{c.organization_name}</td>
                      <td><span className={`badge badge-${c.status}`}>{c.status}</span></td>
                      <td>
                        <Link to={`/cases/${c.id}`} className="btn btn-sm btn-outline">
                          Открыть
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty">
              <FolderOpen size={40} style={{ opacity: 0.3, marginBottom: 12 }} />
              <p>Дел пока нет</p>
              <Link to="/cases" className="btn btn-primary" style={{ marginTop: 12 }}>
                Создать первое дело
              </Link>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
