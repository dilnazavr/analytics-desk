import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { LayoutDashboard, FolderOpen, LogOut, FileText } from 'lucide-react'

interface Props {
  user: any
  onLogout: () => void
}

export default function Layout({ user, onLogout }: Props) {
  const navigate = useNavigate()

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-brand">
          ANALYTICS DESK
          <span>Система аналитической работы</span>
        </div>
        <nav>
          <NavLink to="/" end>
            <LayoutDashboard size={18} /> Главная панель
          </NavLink>
          <NavLink to="/cases">
            <FolderOpen size={18} /> Реестр дел
          </NavLink>
          <NavLink to="/users">
            Пользователи
          </NavLink>
        </nav>
        <div style={{ padding: '16px', borderTop: '1px solid #334155', fontSize: 13 }}>
          <div style={{ color: '#94a3b8', marginBottom: 4 }}>{user.full_name}</div>
          <div style={{ color: '#64748b', fontSize: 12 }}>{user.role?.name}</div>
          <button
            className="btn btn-outline"
            style={{ marginTop: 12, width: '100%', color: '#cbd5e1', borderColor: '#475569' }}
            onClick={() => { onLogout(); navigate('/login') }}
          >
            <LogOut size={14} /> Выйти
          </button>
        </div>
      </aside>
      <div className="main">
        <Outlet />
      </div>
    </div>
  )
}
