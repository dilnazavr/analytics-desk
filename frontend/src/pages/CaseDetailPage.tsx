import { useEffect, useState } from 'react'
import { useParams, NavLink, Routes, Route, Navigate } from 'react-router-dom'
import { casesApi, filesApi, invoicesApi, matchesApi, reportsApi } from '../api/client'
import GraphTab from '../components/GraphTab'
import { Play, Check, X, FileText, Download } from 'lucide-react'

function Overview({ caseData, summary }: { caseData: any; summary: any }) {
  return (
    <div>
      <div className="stats-grid">
        <div className="stat-card">
          <div className="label">Приобретение</div>
          <div className="value" style={{ fontSize: 20 }}>
            {(summary?.purchase?.amount ?? 0).toLocaleString('ru')} ₸
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{summary?.purchase?.count ?? 0} позиций</div>
        </div>
        <div className="stat-card">
          <div className="label">Реализация</div>
          <div className="value" style={{ fontSize: 20 }}>
            {(summary?.sale?.amount ?? 0).toLocaleString('ru')} ₸
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{summary?.sale?.count ?? 0} позиций</div>
        </div>
      </div>
      <div className="card">
        <div className="card-title">Сведения о деле</div>
        <table>
          <tbody>
            <tr><td style={{ width: 180, color: 'var(--text-muted)' }}>Номер</td><td>{caseData.number}</td></tr>
            <tr><td style={{ color: 'var(--text-muted)' }}>Организация</td><td>{caseData.organization_name}</td></tr>
            <tr><td style={{ color: 'var(--text-muted)' }}>БИН</td><td>{caseData.bin}</td></tr>
            <tr><td style={{ color: 'var(--text-muted)' }}>Основание</td><td>{caseData.basis || '—'}</td></tr>
            <tr><td style={{ color: 'var(--text-muted)' }}>Период</td><td>{caseData.period_start} — {caseData.period_end}</td></tr>
            <tr><td style={{ color: 'var(--text-muted)' }}>Ответственный</td><td>{caseData.responsible_name}</td></tr>
            <tr><td style={{ color: 'var(--text-muted)' }}>Статус</td><td><span className={`badge badge-${caseData.status}`}>{caseData.status}</span></td></tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}

function FilesTab({ caseId }: { caseId: number }) {
  const [files, setFiles] = useState<any[]>([])
  const [uploading, setUploading] = useState(false)
  const [preview, setPreview] = useState<any>(null)
  const [mapping, setMapping] = useState<any>({})
  const [jobId, setJobId] = useState<number | null>(null)
  const [msg, setMsg] = useState('')
  const [defaultOp, setDefaultOp] = useState('purchase')

  const load = () => {
    filesApi.list(caseId).then((r) => setFiles(r.data))
  }

  useEffect(() => { load() }, [caseId])

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    setMsg('')
    try {
      const { data } = await filesApi.upload(caseId, file)
      setPreview(data)
      setMapping(data.suggested_mapping || {})
      setJobId(data.import_job_id)
      load()
    } catch (err: any) {
      setMsg(err.response?.data?.error || 'Ошибка загрузки')
    } finally {
      setUploading(false)
    }
  }

  const handleRun = async () => {
    if (!jobId) return
    setMsg('Обработка…')
    try {
      const { data } = await filesApi.runImport(jobId, mapping, defaultOp)
      setMsg(`Готово: загружено ${data.success_rows} из ${data.total_rows}, ошибок: ${data.error_rows}`)
      setPreview(null)
      load()
    } catch (err: any) {
      setMsg(err.response?.data?.error || 'Ошибка обработки')
    }
  }

  return (
    <div>
      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-title">Загрузка файла</div>
        <input type="file" accept=".xlsx,.xls,.csv" onChange={handleUpload} disabled={uploading} />
        {uploading && <p style={{ marginTop: 8 }}>Загрузка…</p>}
        {msg && <div className={msg.includes('Готово') ? 'success-msg' : 'error-msg'} style={{ marginTop: 12 }}>{msg}</div>}
      </div>

      {preview && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="card-title">Сопоставление колонок</div>
          <div className="form-group">
            <label>Тип операций по умолчанию</label>
            <select value={defaultOp} onChange={(e) => setDefaultOp(e.target.value)}>
              <option value="purchase">Приобретение</option>
              <option value="sale">Реализация</option>
              <option value="unknown">Неизвестно</option>
            </select>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            {Object.entries(mapping).map(([field, col]) => (
              <div className="form-group" key={field}>
                <label>{field}</label>
                <select
                  value={(col as string) || ''}
                  onChange={(e) => setMapping({ ...mapping, [field]: e.target.value || null })}
                >
                  <option value="">— не выбрано —</option>
                  {(preview.columns || []).map((c: string) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>
            ))}
          </div>
          <button className="btn btn-primary" onClick={handleRun}>
            <Play size={16} /> Запустить обработку
          </button>
        </div>
      )}

      <div className="card">
        <div className="card-title">Загруженные файлы</div>
        {files.length === 0 ? (
          <div className="empty">Файлов пока нет</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Файл</th>
                <th>Тип</th>
                <th>Размер</th>
                <th>Статус</th>
                <th>Загружен</th>
              </tr>
            </thead>
            <tbody>
              {files.map((f) => (
                <tr key={f.id}>
                  <td>{f.original_filename}</td>
                  <td>{f.data_type}</td>
                  <td>{f.file_size ? `${(f.file_size / 1024).toFixed(1)} KB` : '—'}</td>
                  <td>{f.status}</td>
                  <td>{f.uploaded_at ? new Date(f.uploaded_at).toLocaleString('ru') : '—'}</td>
                  <td>
                    <button
                      type="button"
                      className="btn btn-sm btn-outline"
                      style={{ color: '#dc2626' }}
                      title="Удалить файл"
                      onClick={async () => {
                        if (!confirm(`Удалить файл «${f.original_filename}»?`)) return
                        try {
                          await filesApi.delete(f.id)
                          setFiles((prev) => prev.filter((x) => x.id !== f.id))
                        } catch (err: any) {
                          alert(err.response?.data?.error || 'Ошибка удаления')
                        }
                      }}
                    >
                      Удалить
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

function LinesTab({ caseId, opType }: { caseId: number; opType: string }) {
  const [items, setItems] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    invoicesApi.lines(caseId, { operation_type: opType, page, per_page: 50 })
      .then((r) => {
        setItems(r.data.items)
        setTotal(r.data.total)
      })
      .finally(() => setLoading(false))
  }, [caseId, opType, page])

  if (loading) return <div className="empty">Загрузка…</div>
  if (items.length === 0) return <div className="empty">Нет данных. Загрузите файл ЭСФ.</div>

  return (
    <div className="card">
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Документ</th>
              <th>Дата</th>
              <th>Товар</th>
              <th>Кол-во</th>
              <th>Цена</th>
              <th>Сумма</th>
              <th>Контрагент</th>
            </tr>
          </thead>
          <tbody>
            {items.map((l) => (
              <tr key={l.id}>
                <td>{l.document_number || '—'}</td>
                <td>{l.document_date || '—'}</td>
                <td style={{ maxWidth: 280 }}>{l.product_name}</td>
                <td>{l.quantity ?? '—'}</td>
                <td>{l.unit_price != null ? Number(l.unit_price).toLocaleString('ru') : '—'}</td>
                <td>{l.amount != null ? Number(l.amount).toLocaleString('ru') : '—'}</td>
                <td>{opType === 'purchase' ? l.supplier_name : l.buyer_name}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div style={{ marginTop: 12, display: 'flex', gap: 8, alignItems: 'center' }}>
        <span style={{ color: 'var(--text-muted)' }}>Всего: {total}</span>
        <button className="btn btn-sm btn-outline" disabled={page <= 1} onClick={() => setPage(page - 1)}>←</button>
        <span>{page}</span>
        <button className="btn btn-sm btn-outline" disabled={page * 50 >= total} onClick={() => setPage(page + 1)}>→</button>
      </div>
    </div>
  )
}

function MatchesTab({ caseId }: { caseId: number }) {
  const [matches, setMatches] = useState<any[]>([])
  const [flags, setFlags] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [msg, setMsg] = useState('')

  const load = () => {
    setLoading(true)
    Promise.all([
      matchesApi.list(caseId),
      matchesApi.flags(caseId),
    ]).then(([m, f]) => {
      setMatches(m.data.items)
      setFlags(f.data)
    }).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [caseId])

  const runMatching = async () => {
    setMsg('Сопоставление…')
    try {
      const { data } = await matchesApi.run(caseId)
      setMsg(`Создано совпадений: ${data.created}`)
      load()
    } catch (err: any) {
      setMsg(err.response?.data?.error || 'Ошибка')
    }
  }

  const updateMatch = async (id: number, status: string) => {
    await matchesApi.update(id, { status })
    load()
  }

  if (loading) return <div className="empty">Загрузка…</div>

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', gap: 12, alignItems: 'center' }}>
        <button className="btn btn-primary" onClick={runMatching}>
          <Play size={16} /> Запустить сопоставление
        </button>
        {msg && <span style={{ color: 'var(--text-muted)' }}>{msg}</span>}
      </div>

      {flags.length > 0 && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="card-title">Аналитические сигналы ({flags.length})</div>
          {flags.map((f) => (
            <div key={f.id} style={{ padding: '10px 0', borderBottom: '1px solid var(--border)' }}>
              <strong>{f.title}</strong>
              <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>{f.description}</div>
              <span className={`badge badge-${f.status === 'new' ? 'review' : 'open'}`}>{f.status}</span>
            </div>
          ))}
        </div>
      )}

      <div className="card">
        <div className="card-title">Сопоставления ({matches.length})</div>
        {matches.length === 0 ? (
          <div className="empty">Нет сопоставлений. Загрузите приобретение и реализацию, затем запустите сопоставление.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Тип</th>
                <th>Сходство</th>
                <th>Приобретение</th>
                <th>Реализация</th>
                <th>Δ цены %</th>
                <th>Статус</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {matches.map((m) => (
                <tr key={m.id}>
                  <td>{m.match_type}</td>
                  <td>{m.similarity_score?.toFixed(0)}%</td>
                  <td style={{ maxWidth: 180 }}>{m.purchase?.product_name}</td>
                  <td style={{ maxWidth: 180 }}>{m.sale?.product_name}</td>
                  <td style={{ color: Math.abs(m.price_diff_percent || 0) > 50 ? 'var(--danger)' : undefined }}>
                    {m.price_diff_percent != null ? `${m.price_diff_percent.toFixed(1)}%` : '—'}
                  </td>
                  <td>{m.status}</td>
                  <td style={{ whiteSpace: 'nowrap' }}>
                    {m.status === 'proposed' && (
                      <>
                        <button className="btn btn-sm btn-outline" onClick={() => updateMatch(m.id, 'confirmed')} title="Подтвердить">
                          <Check size={14} />
                        </button>
                        <button className="btn btn-sm btn-outline" onClick={() => updateMatch(m.id, 'rejected')} title="Отклонить">
                          <X size={14} />
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

function ReportTab({ caseId }: { caseId: number }) {
  const [reports, setReports] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [msg, setMsg] = useState('')

  const load = () => reportsApi.list(caseId).then((r) => setReports(r.data))
  useEffect(() => { load() }, [caseId])

  const generate = async () => {
    setLoading(true)
    setMsg('')
    try {
      await reportsApi.create(caseId)
      setMsg('Черновик справки сформирован')
      load()
    } catch (err: any) {
      setMsg(err.response?.data?.error || 'Ошибка')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <button className="btn btn-primary" onClick={generate} disabled={loading} style={{ marginBottom: 16 }}>
        <FileText size={16} /> {loading ? 'Формирование…' : 'Сформировать черновик Word'}
      </button>
      {msg && <div className="success-msg">{msg}</div>}
      <div className="card">
        <div className="card-title">Версии справки</div>
        {reports.length === 0 ? (
          <div className="empty">Справок пока нет</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Версия</th>
                <th>Название</th>
                <th>Статус</th>
                <th>Создана</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {reports.map((r) => (
                <tr key={r.id}>
                  <td>v{r.version}</td>
                  <td>{r.title}</td>
                  <td>{r.status}</td>
                  <td>{r.created_at ? new Date(r.created_at).toLocaleString('ru') : '—'}</td>
                  <td>
                    <button
                      className="btn btn-sm btn-outline"
                      onClick={() => {
                        const token = localStorage.getItem('access_token')
                        fetch(reportsApi.downloadUrl(r.id), {
                          headers: { Authorization: `Bearer ${token}` },
                        })
                          .then((res) => res.blob())
                          .then((blob) => {
                            const url = URL.createObjectURL(blob)
                            const a = document.createElement('a')
                            a.href = url
                            a.download = `report_v${r.version}.docx`
                            a.click()
                          })
                      }}
                    >
                      <Download size={14} /> Скачать
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

export default function CaseDetailPage() {
  const { id } = useParams()
  const caseId = Number(id)
  const [caseData, setCaseData] = useState<any>(null)
  const [summary, setSummary] = useState<any>(null)

  useEffect(() => {
    casesApi.get(caseId).then((r) => setCaseData(r.data))
    invoicesApi.summary(caseId).then((r) => setSummary(r.data)).catch(() => {})
  }, [caseId])

  if (!caseData) return <div className="content">Загрузка…</div>

  return (
    <>
      <header className="header">
        <div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{caseData.number}</div>
          <h2 style={{ fontSize: 18, fontWeight: 600 }}>{caseData.title}</h2>
        </div>
        <span className={`badge badge-${caseData.status}`}>{caseData.status}</span>
      </header>
      <div className="content">
        <div className="tabs">
          <NavLink to={`/cases/${caseId}`} end>Обзор</NavLink>
          <NavLink to={`/cases/${caseId}/files`}>Файлы</NavLink>
          <NavLink to={`/cases/${caseId}/purchase`}>Приобретение</NavLink>
          <NavLink to={`/cases/${caseId}/sale`}>Реализация</NavLink>
          <NavLink to={`/cases/${caseId}/matches`}>Сопоставление</NavLink>
          <NavLink to={`/cases/${caseId}/graph`}>Связи</NavLink>
          <NavLink to={`/cases/${caseId}/report`}>Справка</NavLink>
        </div>

        <Routes>
          <Route index element={<Overview caseData={caseData} summary={summary} />} />
          <Route path="files" element={<FilesTab caseId={caseId} />} />
          <Route path="purchase" element={<LinesTab caseId={caseId} opType="purchase" />} />
          <Route path="sale" element={<LinesTab caseId={caseId} opType="sale" />} />
          <Route path="matches" element={<MatchesTab caseId={caseId} />} />
          <Route path="graph" element={<GraphTab caseId={caseId} />} />
          <Route path="report" element={<ReportTab caseId={caseId} />} />
          <Route path="*" element={<Navigate to={`/cases/${caseId}`} replace />} />
        </Routes>
      </div>
    </>
  )
}
