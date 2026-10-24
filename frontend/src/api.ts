import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  headers: { Accept: 'application/json' },
})

const TOKEN_KEY = 'pramaan.accessToken'
const USER_KEY = 'pramaan.username'
const ROLE_KEY = 'pramaan.role'

api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem(TOKEN_KEY)
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export interface LoginResponse {
  access_token: string
  token_type: string
  role: string
}

export interface Application {
  id: string | number
  name: string
  reference_number?: string | null
  status?: string | null
  created_at?: string | null
  documents_count?: number
  findings_count?: number
  [key: string]: unknown
}

export interface ExtractedField {
  name: string
  value?: unknown
  confidence?: number | null
  status?: string | null
  page?: number | null
}

export interface DocumentRecord {
  id: string | number
  original_filename?: string | null
  document_type?: string | null
  status?: string | null
  sha256?: string | null
  extracted_text?: string | null
  fields?: ExtractedField[] | null
  pages?: number | null
  metadata?: { ocr_message?: string; warnings?: string[]; ocr_used?: boolean }
  [key: string]: unknown
}

export interface VerificationRecord {
  id: string
  application_id: string
  document_id: string
  source_type: string
  label: string
  result: string
  compared_fields: Array<Record<string, unknown>>
  created_at: string
}

export type ReviewAction = 'acknowledge' | 'confirm' | 'resolve' | 'request_correction' | 'manual_verification'

export interface Finding {
  id: string | number
  rule_id?: string | null
  rule_name?: string | null
  severity?: string | null
  status?: string | null
  reason?: string | null
  source_document_id?: string | number | null
  source_filename?: string | null
  page?: number | null
  field_name?: string | null
  evidence?: string | null
  recommended_action?: string | null
  manual_review_required?: boolean
  [key: string]: unknown
}

export interface AuditEntry {
  action?: string | null
  actor?: string | null
  created_at?: string | null
  details?: string | Record<string, unknown> | null
}

export interface DashboardSummary {
  [key: string]: unknown
}

export function unwrapList<T>(value: unknown): T[] {
  if (Array.isArray(value)) return value as T[]
  if (value && typeof value === 'object') {
    const record = value as Record<string, unknown>
    for (const key of ['items', 'results', 'applications', 'documents', 'findings', 'entries', 'audit']) {
      if (Array.isArray(record[key])) return record[key] as T[]
    }
  }
  return []
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const { data } = await api.post<LoginResponse>('/auth/login', { username, password })
  sessionStorage.setItem(TOKEN_KEY, data.access_token)
  sessionStorage.setItem(USER_KEY, username)
  sessionStorage.setItem(ROLE_KEY, data.role)
  return data
}

export function logout() {
  sessionStorage.removeItem(TOKEN_KEY)
  sessionStorage.removeItem(USER_KEY)
  sessionStorage.removeItem(ROLE_KEY)
}

export function getUsername() {
  return sessionStorage.getItem(USER_KEY) || ''
}

export function getRole() {
  return sessionStorage.getItem(ROLE_KEY) || ''
}

export function isAuthenticated() {
  return Boolean(sessionStorage.getItem(TOKEN_KEY))
}

export const client = {
  dashboard: () => api.get<DashboardSummary>('/api/dashboard/summary').then((r) => r.data),
  applications: () => api.get<unknown>('/api/applications').then((r) => unwrapList<Application>(r.data)),
  createApplication: (body: { institution_name: string; reference_number?: string }) =>
    api.post<Application>('/api/applications', body).then((r) => r.data),
  application: (id: string) => api.get<Application>(`/api/applications/${encodeURIComponent(id)}`).then((r) => r.data),
  documents: (id: string) => api.get<unknown>(`/api/applications/${encodeURIComponent(id)}/documents`).then((r) => unwrapList<DocumentRecord>(r.data)),
  upload: (id: string, file: File, documentType: string) => {
    const body = new FormData()
    body.append('file', file)
    body.append('document_type', documentType)
    return api.post<DocumentRecord>(`/api/applications/${encodeURIComponent(id)}/documents`, body).then((r) => r.data)
  },
  downloadDocument: async (id: string | number, filename: string) => {
    const response = await api.get<Blob>(`/api/documents/${encodeURIComponent(String(id))}/file`, { responseType: 'blob' })
    const url = URL.createObjectURL(response.data)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    link.click()
    window.setTimeout(() => URL.revokeObjectURL(url), 1000)
  },
  validate: (id: string) => api.post<unknown>(`/api/applications/${encodeURIComponent(id)}/validate`).then((r) => r.data),
  findings: (id: string) => api.get<unknown>(`/api/applications/${encodeURIComponent(id)}/findings`).then((r) => unwrapList<Finding>(r.data)),
  verifyDocument: (id: string | number) => api.post<unknown>(`/api/documents/${encodeURIComponent(String(id))}/verify`).then((r) => r.data),
  verifications: (id: string) =>
    api.get<unknown>(`/api/applications/${encodeURIComponent(id)}/verifications`).then((r) => unwrapList<VerificationRecord>(r.data)),
  findingAction: (id: string | number, action: ReviewAction, note: string) =>
    api.post<unknown>(`/api/findings/${encodeURIComponent(String(id))}/actions`, { action, note }).then((r) => r.data),
  audit: (id: string) => api.get<unknown>(`/api/applications/${encodeURIComponent(id)}/audit`).then((r) => unwrapList<AuditEntry>(r.data)),
}

export function errorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data as { detail?: unknown; message?: unknown } | undefined
    if (typeof detail?.detail === 'string') return detail.detail
    if (typeof detail?.message === 'string') return detail.message
    if (!error.response) return 'Could not reach the API. Check that the service is running and the API URL is correct.'
    return `The request failed (${error.response.status}). Please try again.`
  }
  return error instanceof Error ? error.message : 'Something went wrong. Please try again.'
}
