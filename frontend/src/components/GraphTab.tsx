import { useCallback, useEffect, useRef, useState } from 'react'
import { graphApi } from '../api/client'
import {
  Download, RefreshCw, Plus, Link2, ZoomIn, ZoomOut, Maximize2, Trash2, Save,
} from 'lucide-react'

interface Props {
  caseId: number
}

const EDGE_META: Record<string, { color: string; label: string }> = {
  esf_purchase: { color: '#2563eb', label: 'Покупка (ЭСФ)' },
  esf_sale: { color: '#1d4ed8', label: 'Продажа (ЭСФ)' },
  gov_contract: { color: '#16a34a', label: 'Госзакупки' },
  manual: { color: '#7c3aed', label: 'Ручная связь' },
  management: { color: '#a855f7', label: 'Руководство' },
  founder: { color: '#c026d3', label: 'Учредитель' },
  same_address: { color: '#64748b', label: 'Один адрес' },
  anomaly: { color: '#dc2626', label: 'Аномалия' },
}

const TYPE_LABELS: Record<string, string> = {
  organization: 'Организация',
  gov: 'Госорган',
  contract: 'Договор',
  person: 'Физлицо',
}

function shortLabel(text: string, max = 48): string {
  const t = (text || '').trim()
  if (t.length <= max) return t
  return t.slice(0, max - 1) + '…'
}

export default function GraphTab({ caseId }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<any>(null)
  const [loading, setLoading] = useState(false)
  const [msg, setMsg] = useState('')
  const [minAmount, setMinAmount] = useState(0)
  const [depth, setDepth] = useState(2)
  const [stats, setStats] = useState<any>(null)
  const [risks, setRisks] = useState<any[]>([])
  const [selected, setSelected] = useState<any>(null)
  const [edgeFilters, setEdgeFilters] = useState({
    esf_purchase: true,
    esf_sale: true,
    gov_contract: true,
    manual: true,
    management: true,
  })
  const [linkMode, setLinkMode] = useState(false)
  const [linkFrom, setLinkFrom] = useState<any>(null)
  const [relForm, setRelForm] = useState({
    relation_type: 'manual',
    from_entity_label: '',
    from_entity_id: '' as string,
    to_entity_label: '',
    to_entity_id: '' as string,
    comment: '',
    status: 'unverified',
  })
  const [editComment, setEditComment] = useState('')
  const [editStatus, setEditStatus] = useState('unverified')
  const [editType, setEditType] = useState('manual')
  const [goszakupOk, setGoszakupOk] = useState<boolean | null>(null)
  const [procurement, setProcurement] = useState<any[]>([])
  const [showNamesFull, setShowNamesFull] = useState(true)

  const edgeTypesParam = Object.entries(edgeFilters)
    .filter(([, v]) => v)
    .map(([k]) => k)
    .concat(['founder', 'same_address', 'anomaly'])
    .join(',')

  const loadGraph = useCallback(async () => {
    setLoading(true)
    setMsg('')
    try {
      const { data } = await graphApi.getGraph(caseId, {
        min_amount: minAmount,
        depth,
        edge_types: edgeTypesParam,
      })
      setStats(data.stats)
      setRisks(data.risks || [])
      await renderCy(data.nodes || [], data.edges || [])
    } catch (e: any) {
      setMsg(e.response?.data?.error || e.message || 'Ошибка загрузки графа')
    } finally {
      setLoading(false)
    }
  }, [caseId, minAmount, depth, edgeTypesParam, showNamesFull])

  const renderCy = async (nodes: any[], edges: any[]) => {
    if (!containerRef.current) return
    const cytoscape = (await import('cytoscape')).default
    let fcose: any
    try {
      fcose = (await import('cytoscape-fcose')).default
      cytoscape.use(fcose)
    } catch {
      /* optional */
    }
    if (cyRef.current) {
      cyRef.current.destroy()
      cyRef.current = null
    }

    const elements = [
      ...nodes.map((n) => ({
        data: {
          id: n.id,
          label: showNamesFull ? (n.label || n.id) : shortLabel(n.label || n.id, 28),
          fullLabel: n.label || n.id,
          type: n.type,
          bin: n.bin || '',
          meta: n.meta || {},
        },
      })),
      ...edges.map((e) => {
        const meta = EDGE_META[e.type] || { color: '#94a3b8', label: e.type }
        const weightLabel = e.weight
          ? `${Math.round(Number(e.weight)).toLocaleString('ru')} ₸`
          : meta.label
        return {
          data: {
            id: e.id,
            source: e.source,
            target: e.target,
            type: e.type,
            weight: e.weight || 0,
            risk: e.risk || '',
            label: weightLabel,
            color: e.risk ? EDGE_META.anomaly.color : meta.color,
            meta: e.meta || {},
            relation_id: e.meta?.relation_id || null,
          },
        }
      }),
    ]

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      minZoom: 0.15,
      maxZoom: 3,
      wheelSensitivity: 0.35,
      style: [
        {
          selector: 'node',
          style: {
            label: 'data(label)',
            'text-valign': 'bottom',
            'text-halign': 'center',
            'text-margin-y': 8,
            'font-size': showNamesFull ? 11 : 10,
            'font-weight': 600,
            'text-max-width': showNamesFull ? 160 : 90,
            'text-wrap': 'wrap',
            'text-background-color': '#ffffff',
            'text-background-opacity': 0.85,
            'text-background-padding': '3px',
            'text-border-width': 0,
            width: 42,
            height: 42,
            'background-color': '#64748b',
            color: '#0f172a',
            'border-width': 3,
            'border-color': '#ffffff',
            'overlay-padding': 6,
          },
        },
        {
          selector: 'node[type="organization"]',
          style: { 'background-color': '#3b82f6' },
        },
        {
          selector: 'node[type="gov"]',
          style: { 'background-color': '#16a34a', shape: 'round-rectangle' },
        },
        {
          selector: 'node[type="contract"]',
          style: {
            'background-color': '#f59e0b',
            shape: 'diamond',
            width: 32,
            height: 32,
            'font-size': 9,
          },
        },
        {
          selector: 'node[type="person"]',
          style: { 'background-color': '#a855f7', shape: 'ellipse' },
        },
        {
          selector: 'edge',
          style: {
            width: 2.5,
            'curve-style': 'bezier',
            'target-arrow-shape': 'triangle',
            'target-arrow-color': 'data(color)',
            'line-color': 'data(color)',
            label: 'data(label)',
            'font-size': 9,
            color: '#334155',
            'text-rotation': 'autorotate',
            'text-margin-y': -6,
            'text-background-color': '#f8fafc',
            'text-background-opacity': 0.9,
            'text-background-padding': '2px',
            'arrow-scale': 1.2,
          },
        },
        {
          selector: 'edge[type="gov_contract"]',
          style: { 'line-style': 'dashed', width: 3 },
        },
        {
          selector: 'edge[risk]',
          style: {
            width: 4,
            'line-color': EDGE_META.anomaly.color,
            'target-arrow-color': EDGE_META.anomaly.color,
          },
        },
        {
          selector: 'node:selected',
          style: { 'border-width': 5, 'border-color': '#f59e0b', 'background-blacken': -0.1 },
        },
        {
          selector: 'edge:selected',
          style: { width: 5, 'line-color': '#f59e0b', 'target-arrow-color': '#f59e0b' },
        },
      ],
      layout: fcose
        ? {
            name: 'fcose',
            animate: false,
            nodeRepulsion: () => 12000,
            idealEdgeLength: () => 140,
            nestingFactor: 0.1,
            gravity: 0.25,
            numIter: 2500,
            tilingPaddingVertical: 20,
            tilingPaddingHorizontal: 20,
          }
        : { name: 'cose', animate: false, nodeRepulsion: 12000 },
    })

    cy.on('tap', 'node', (evt: any) => {
      const d = evt.target.data()
      if (linkMode) {
        if (!linkFrom) {
          setLinkFrom(d)
          setMsg(`Выбрано «${d.fullLabel}». Кликните второй узел.`)
        } else if (linkFrom.id !== d.id) {
          setRelForm({
            relation_type: 'manual',
            from_entity_label: linkFrom.fullLabel,
            from_entity_id: linkFrom.id,
            to_entity_label: d.fullLabel,
            to_entity_id: d.id,
            comment: '',
            status: 'unverified',
          })
          setLinkFrom(null)
          setLinkMode(false)
          setMsg('Заполните тип связи и сохраните справа.')
          setSelected({ kind: 'new-link', from: linkFrom, to: d })
        }
        return
      }
      setSelected({ kind: 'node', ...d })
      setEditComment('')
    })

    cy.on('tap', 'edge', (evt: any) => {
      if (linkMode) return
      const d = evt.target.data()
      setSelected({ kind: 'edge', ...d })
      setEditComment(d.meta?.comment || '')
      setEditStatus(d.meta?.status || 'unverified')
      setEditType(d.type || 'manual')
    })

    cy.on('tap', (evt: any) => {
      if (evt.target === cy) {
        if (!linkMode) setSelected(null)
      }
    })

    cyRef.current = cy
  }

  useEffect(() => {
    loadGraph()
    graphApi.goszakupStatus().then((r) => setGoszakupOk(!!r.data.configured)).catch(() => setGoszakupOk(false))
    graphApi.listProcurement(caseId).then((r) => setProcurement(r.data)).catch(() => {})
  }, [caseId])

  const zoomBy = (factor: number) => {
    if (!cyRef.current) return
    cyRef.current.zoom(cyRef.current.zoom() * factor)
    cyRef.current.center()
  }

  const fitView = () => {
    cyRef.current?.fit(undefined, 40)
  }

  const exportPng = () => {
    if (!cyRef.current) return
    const png = cyRef.current.png({ full: true, scale: 2, bg: '#ffffff' })
    const a = document.createElement('a')
    a.href = png
    a.download = `graph_case_${caseId}.png`
    a.click()
  }

  const syncGoszakup = async () => {
    setMsg('Синхронизация с goszakup…')
    try {
      const { data } = await graphApi.syncProcurement(caseId)
      setMsg(`Загружено: ${data.fetched}, создано: ${data.created}, пропущено: ${data.skipped}`)
      setProcurement((await graphApi.listProcurement(caseId)).data)
      await loadGraph()
    } catch (e: any) {
      setMsg(e.response?.data?.error || e.message || 'Ошибка sync')
    }
  }

  const saveNewRelation = async () => {
    try {
      await graphApi.createRelation(caseId, {
        relation_type: relForm.relation_type,
        from_entity_type: 'organization',
        from_entity_label: relForm.from_entity_label,
        from_entity_id: relForm.from_entity_id,
        to_entity_type: 'organization',
        to_entity_label: relForm.to_entity_label,
        to_entity_id: relForm.to_entity_id,
        comment: relForm.comment,
        status: relForm.status,
        source: 'ручной ввод (схема)',
      })
      setMsg('Связь добавлена')
      setSelected(null)
      setRelForm({
        relation_type: 'manual',
        from_entity_label: '',
        from_entity_id: '',
        to_entity_label: '',
        to_entity_id: '',
        comment: '',
        status: 'unverified',
      })
      await loadGraph()
    } catch (e: any) {
      setMsg(e.response?.data?.error || 'Не удалось сохранить связь')
    }
  }

  const saveEdgeEdit = async () => {
    const rid = selected?.relation_id || selected?.meta?.relation_id
    if (!rid) {
      setMsg('Эту стрелку (из ЭСФ/договоров) нельзя менять. Добавьте ручную связь.')
      return
    }
    try {
      await graphApi.updateRelation(Number(rid), {
        comment: editComment,
        status: editStatus,
        relation_type: editType,
      })
      setMsg('Связь обновлена')
      await loadGraph()
    } catch (e: any) {
      setMsg(e.response?.data?.error || 'Ошибка сохранения')
    }
  }

  const deleteEdge = async () => {
    const rid = selected?.relation_id || selected?.meta?.relation_id
    if (!rid) {
      setMsg('Удалить можно только ручную связь')
      return
    }
    if (!confirm('Удалить эту связь?')) return
    try {
      await graphApi.deleteRelation(Number(rid))
      setSelected(null)
      setMsg('Связь удалена')
      await loadGraph()
    } catch (e: any) {
      setMsg(e.response?.data?.error || 'Ошибка удаления')
    }
  }

  const startLinkMode = () => {
    setLinkMode(true)
    setLinkFrom(null)
    setSelected(null)
    setMsg('Режим связи: кликните первый узел, затем второй')
  }

  return (
    <div>
      {/* Toolbar */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginBottom: 12, alignItems: 'center' }}>
        <label style={{ fontSize: 13 }}>
          Мин. сумма ₸{' '}
          <input
            type="number"
            value={minAmount}
            onChange={(e) => setMinAmount(Number(e.target.value) || 0)}
            style={{ width: 100, padding: 6, border: '1px solid var(--border)', borderRadius: 6 }}
          />
        </label>
        <label style={{ fontSize: 13 }}>
          Глубина{' '}
          <select value={depth} onChange={(e) => setDepth(Number(e.target.value))} style={{ padding: 6, borderRadius: 6 }}>
            <option value={1}>1</option>
            <option value={2}>2</option>
            <option value={3}>3</option>
          </select>
        </label>
        <label style={{ fontSize: 12, display: 'flex', gap: 4, alignItems: 'center' }}>
          <input type="checkbox" checked={showNamesFull} onChange={(e) => setShowNamesFull(e.target.checked)} />
          Полные названия
        </label>
        {(['esf_purchase', 'esf_sale', 'gov_contract', 'manual'] as const).map((k) => (
          <label key={k} style={{ fontSize: 12, display: 'flex', gap: 4, alignItems: 'center' }}>
            <span style={{ width: 10, height: 10, borderRadius: 2, background: EDGE_META[k].color, display: 'inline-block' }} />
            <input
              type="checkbox"
              checked={(edgeFilters as any)[k]}
              onChange={(e) => setEdgeFilters({ ...edgeFilters, [k]: e.target.checked })}
            />
            {EDGE_META[k].label}
          </label>
        ))}
        <button className="btn btn-primary btn-sm" onClick={loadGraph} disabled={loading}>
          <RefreshCw size={14} /> {loading ? '…' : 'Обновить'}
        </button>
        <button className={`btn btn-sm ${linkMode ? 'btn-primary' : 'btn-outline'}`} onClick={startLinkMode}>
          <Plus size={14} /> Новая связь
        </button>
        <button className="btn btn-outline btn-sm" onClick={() => zoomBy(1.25)} title="Крупнее">
          <ZoomIn size={14} />
        </button>
        <button className="btn btn-outline btn-sm" onClick={() => zoomBy(0.8)} title="Мельче">
          <ZoomOut size={14} />
        </button>
        <button className="btn btn-outline btn-sm" onClick={fitView} title="Вписать">
          <Maximize2 size={14} />
        </button>
        <button className="btn btn-outline btn-sm" onClick={exportPng}>
          <Download size={14} /> PNG
        </button>
        <button className="btn btn-outline btn-sm" onClick={syncGoszakup}>
          <Link2 size={14} /> Goszakup {goszakupOk === false ? '(нет токена)' : ''}
        </button>
      </div>

      {/* Legend */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, marginBottom: 10, fontSize: 12, color: 'var(--text-muted)' }}>
        {Object.entries(EDGE_META).slice(0, 6).map(([k, v]) => (
          <span key={k} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ width: 18, height: 3, background: v.color, display: 'inline-block', borderRadius: 2 }} />
            {v.label}
          </span>
        ))}
        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ width: 12, height: 12, borderRadius: '50%', background: '#3b82f6' }} /> Организация
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ width: 12, height: 12, borderRadius: 2, background: '#16a34a' }} /> Госорган
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ width: 10, height: 10, background: '#f59e0b', transform: 'rotate(45deg)' }} /> Договор
        </span>
      </div>

      {msg && (
        <div className={/ошибк|не /i.test(msg) ? 'error-msg' : 'success-msg'} style={{ marginBottom: 8 }}>
          {msg}
        </div>
      )}

      {stats && (
        <div className="stats-grid" style={{ marginBottom: 12 }}>
          <div className="stat-card">
            <div className="label">K_gos</div>
            <div className="value" style={{ fontSize: 18 }}>{(stats.k_gos * 100).toFixed(0)}%</div>
          </div>
          <div className="stat-card">
            <div className="label">Договоры гос.</div>
            <div className="value" style={{ fontSize: 15 }}>{Number(stats.gov_contracts_sum || 0).toLocaleString('ru')} ₸</div>
          </div>
          <div className="stat-card">
            <div className="label">Узлы / рёбра</div>
            <div className="value" style={{ fontSize: 18 }}>{stats.nodes_count} / {stats.edges_count}</div>
          </div>
          <div className="stat-card">
            <div className="label">Договоров</div>
            <div className="value" style={{ fontSize: 18 }}>{procurement.length}</div>
          </div>
        </div>
      )}

      {risks.length > 0 && (
        <div className="card" style={{ marginBottom: 12 }}>
          <div className="card-title">Сигналы по схеме</div>
          {risks.map((r, i) => (
            <div key={i} style={{ padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
              <strong>{r.title}</strong>
              <span className={`badge badge-${r.severity === 'high' ? 'review' : 'open'}`} style={{ marginLeft: 8 }}>{r.severity}</span>
              <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>{r.description}</div>
            </div>
          ))}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: selected ? '1fr 300px' : '1fr', gap: 12 }}>
        <div
          ref={containerRef}
          style={{
            height: 560,
            border: linkMode ? '2px solid #7c3aed' : '1px solid var(--border)',
            borderRadius: 8,
            background: '#f1f5f9',
            boxShadow: 'inset 0 1px 2px rgba(0,0,0,.04)',
          }}
        />

        {selected && (
          <div className="card" style={{ maxHeight: 560, overflow: 'auto' }}>
            {selected.kind === 'node' && (
              <>
                <div className="card-title">Компания / узел</div>
                <p style={{ fontWeight: 600, marginBottom: 8, wordBreak: 'break-word' }}>{selected.fullLabel}</p>
                <table>
                  <tbody>
                    <tr><td style={{ color: 'var(--text-muted)' }}>Тип</td><td>{TYPE_LABELS[selected.type] || selected.type}</td></tr>
                    <tr><td style={{ color: 'var(--text-muted)' }}>БИН/ключ</td><td style={{ wordBreak: 'break-all' }}>{selected.bin || '—'}</td></tr>
                    <tr><td style={{ color: 'var(--text-muted)' }}>ID</td><td style={{ fontSize: 11, wordBreak: 'break-all' }}>{selected.id}</td></tr>
                  </tbody>
                </table>
                <button className="btn btn-outline btn-sm" style={{ marginTop: 12 }} onClick={() => {
                  setLinkMode(true)
                  setLinkFrom(selected)
                  setMsg(`От «${selected.fullLabel}» — кликните второй узел`)
                }}>
                  <Plus size={14} /> Связь от этого узла
                </button>
              </>
            )}

            {selected.kind === 'edge' && (
              <>
                <div className="card-title">Связь (стрелка)</div>
                <p style={{ fontSize: 13, marginBottom: 8 }}>
                  <span style={{ color: selected.color || '#64748b' }}>●</span>{' '}
                  {EDGE_META[selected.type]?.label || selected.type}
                  {selected.weight ? ` · ${Number(selected.weight).toLocaleString('ru')} ₸` : ''}
                </p>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 10, wordBreak: 'break-all' }}>
                  {selected.source} → {selected.target}
                </div>

                {(selected.relation_id || selected.meta?.relation_id) ? (
                  <>
                    <div className="form-group">
                      <label>Тип</label>
                      <select value={editType} onChange={(e) => setEditType(e.target.value)}>
                        <option value="manual">Ручная</option>
                        <option value="management">Руководство</option>
                        <option value="founder">Учредитель</option>
                        <option value="same_address">Один адрес</option>
                      </select>
                    </div>
                    <div className="form-group">
                      <label>Статус</label>
                      <select value={editStatus} onChange={(e) => setEditStatus(e.target.value)}>
                        <option value="unverified">Не проверено</option>
                        <option value="confirmed">Подтверждено</option>
                        <option value="rejected">Отклонено</option>
                      </select>
                    </div>
                    <div className="form-group">
                      <label>Комментарий</label>
                      <textarea
                        rows={3}
                        value={editComment}
                        onChange={(e) => setEditComment(e.target.value)}
                        style={{ width: '100%', padding: 8, borderRadius: 6, border: '1px solid var(--border)' }}
                      />
                    </div>
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                      <button className="btn btn-primary btn-sm" onClick={saveEdgeEdit}><Save size={14} /> Сохранить</button>
                      <button className="btn btn-outline btn-sm" onClick={deleteEdge}><Trash2 size={14} /> Удалить</button>
                    </div>
                  </>
                ) : (
                  <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                    Связь из ЭСФ или договора — только просмотр. Для правок создайте <b>новую ручную связь</b> между узлами.
                  </p>
                )}
              </>
            )}

            {selected.kind === 'new-link' && (
              <>
                <div className="card-title">Новая связь</div>
                <p style={{ fontSize: 13, marginBottom: 8 }}>
                  <b>{relForm.from_entity_label}</b>
                  <br />→<br />
                  <b>{relForm.to_entity_label}</b>
                </p>
                <div className="form-group">
                  <label>Тип связи</label>
                  <select
                    value={relForm.relation_type}
                    onChange={(e) => setRelForm({ ...relForm, relation_type: e.target.value })}
                  >
                    <option value="manual">Ручная</option>
                    <option value="management">Руководство</option>
                    <option value="founder">Учредитель</option>
                    <option value="same_address">Один адрес</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Статус</label>
                  <select
                    value={relForm.status}
                    onChange={(e) => setRelForm({ ...relForm, status: e.target.value })}
                  >
                    <option value="unverified">Не проверено</option>
                    <option value="confirmed">Подтверждено</option>
                    <option value="rejected">Отклонено</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Комментарий</label>
                  <textarea
                    rows={3}
                    value={relForm.comment}
                    onChange={(e) => setRelForm({ ...relForm, comment: e.target.value })}
                    style={{ width: '100%', padding: 8, borderRadius: 6, border: '1px solid var(--border)' }}
                  />
                </div>
                <button className="btn btn-primary btn-sm" onClick={saveNewRelation}>
                  <Save size={14} /> Сохранить связь
                </button>
              </>
            )}
          </div>
        )}
      </div>

      {procurement.length > 0 && (
        <div className="card" style={{ marginTop: 16 }}>
          <div className="card-title">Договоры госзакупок ({procurement.length})</div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Номер</th>
                  <th>Заказчик</th>
                  <th>Поставщик</th>
                  <th>Предмет</th>
                  <th>Сумма</th>
                </tr>
              </thead>
              <tbody>
                {procurement.slice(0, 50).map((p) => (
                  <tr key={p.id}>
                    <td>{p.contract_number || p.procurement_number || '—'}</td>
                    <td>{p.customer_name || p.customer_bin}</td>
                    <td>{p.supplier_name || p.supplier_bin}</td>
                    <td style={{ maxWidth: 220 }}>{(p.subject || '').slice(0, 80)}</td>
                    <td>{p.amount != null ? Number(p.amount).toLocaleString('ru') : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
