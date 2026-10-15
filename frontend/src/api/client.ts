import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || '/api'

const client = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
})

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

client.interceptors.response.use(
  (r) => r,
  async (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('user')
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default client

export const authApi = {
  login: (email: string, password: string) =>
    client.post('/auth/login', { email, password }),
  me: () => client.get('/auth/me'),
}

export const casesApi = {
  list: (params?: Record<string, any>) => client.get('/cases', { params }),
  get: (id: number) => client.get(`/cases/${id}`),
  create: (data: any) => client.post('/cases', data),
  update: (id: number, data: any) => client.patch(`/cases/${id}`, data),
  delete: (id: number) => client.delete(`/cases/${id}`),
}

export const filesApi = {
  upload: (caseId: number, file: File, dataType = 'esf') => {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('data_type', dataType)
    return client.post(`/files/cases/${caseId}/upload`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  runImport: (jobId: number, mapping: any, defaultOp = 'purchase') =>
    client.post(`/files/import-jobs/${jobId}/run`, {
      column_mapping: mapping,
      default_operation_type: defaultOp,
    }),
  list: (caseId: number) => client.get(`/files/cases/${caseId}/files`),
  imports: (caseId: number) => client.get(`/files/cases/${caseId}/imports`),
  delete: (fileId: number) => client.delete(`/files/${fileId}`),
}

export const invoicesApi = {
  list: (caseId: number, params?: any) =>
    client.get(`/invoices/cases/${caseId}/invoices`, { params }),
  lines: (caseId: number, params?: any) =>
    client.get(`/invoices/cases/${caseId}/lines`, { params }),
  summary: (caseId: number) => client.get(`/invoices/cases/${caseId}/summary`),
}

export const matchesApi = {
  list: (caseId: number, params?: any) =>
    client.get(`/matches/cases/${caseId}/matches`, { params }),
  run: (caseId: number, threshold = 85) =>
    client.post(`/matches/cases/${caseId}/matches/run`, { fuzzy_threshold: threshold }),
  update: (id: number, data: any) => client.patch(`/matches/${id}`, data),
  flags: (caseId: number) => client.get(`/matches/cases/${caseId}/flags`),
  updateFlag: (id: number, data: any) => client.patch(`/matches/flags/${id}`, data),
}

export const reportsApi = {
  list: (caseId: number) => client.get(`/reports/cases/${caseId}/reports`),
  create: (caseId: number) => client.post(`/reports/cases/${caseId}/reports`),
  downloadUrl: (id: number) => `${API_URL}/reports/${id}/download`,
}

export const dashboardApi = {
  stats: () => client.get('/dashboard/stats'),
}

export const graphApi = {
  getGraph: (caseId: number, params?: Record<string, any>) =>
    client.get(`/cases/${caseId}/graph`, { params }),
  listProcurement: (caseId: number) => client.get(`/cases/${caseId}/procurement`),
  createProcurement: (caseId: number, data: any) => client.post(`/cases/${caseId}/procurement`, data),
  syncProcurement: (caseId: number, data?: any) => client.post(`/cases/${caseId}/procurement/sync`, data || {}),
  listRelations: (caseId: number) => client.get(`/cases/${caseId}/relations`),
  createRelation: (caseId: number, data: any) => client.post(`/cases/${caseId}/relations`, data),
  updateRelation: (id: number, data: any) => client.patch(`/relations/${id}`, data),
  deleteRelation: (id: number) => client.delete(`/relations/${id}`),
  goszakupStatus: () => client.get('/goszakup/status'),
}

export const usersApi = {
  list: () => client.get('/users'),
  roles: () => client.get('/users/roles'),
  create: (data: any) => client.post('/users', data),
  update: (id: number, data: any) => client.patch(`/users/${id}`, data),
  delete: (id: number) => client.delete(`/users/${id}`),
}
