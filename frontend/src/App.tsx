import { useCallback, useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { BrowserRouter, Link, NavLink, Route, Routes, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import {
  Activity, ArrowLeft, ArrowRight, BadgeCheck, Bell, BriefcaseBusiness,
  Check, CheckCircle2, ChevronRight, CircleAlert, ClipboardCheck, Clock3, FileCheck2,
  FilePlus2, FileSearch, FileText, Fingerprint, LayoutDashboard, LoaderCircle, LogOut,
  Menu, Plus, RefreshCw, Search, Shield, ShieldAlert, Sparkles, Upload, X,
} from 'lucide-react'
import {
  client, errorMessage, getRole, getUsername, isAuthenticated, login, logout, type Application,
  type AuditEntry, type DashboardSummary, type DocumentRecord, type Finding, type ReviewAction, type VerificationRecord,
} from './api'
import './App.css'

function formatDate(value?: string | null) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

function humanize(value?: string | null) {
  return value ? value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase()) : 'Unknown'
}

function StatusPill({ value }: { value?: string | null }) {
  const status = (value || 'unknown').toLowerCase().replaceAll(' ', '-')
  return <span className={`status-pill status-${status}`}>{humanize(value)}</span>
}

function Notice({ children, onDismiss }: { children: ReactNode; onDismiss?: () => void }) {
  return <div className="notice" role="alert"><CircleAlert size={17} /><span>{children}</span>{onDismiss && <button className="icon-button" onClick={onDismiss} aria-label="Dismiss error"><X size={16} /></button>}</div>
}

function Loading({ label = 'Loading workspace' }: { label?: string }) {
  return <div className="loading-state"><LoaderCircle className="spin" size={23} /><span>{label}</span></div>
}

function EmptyState({ icon: Icon = FileSearch, title, text, action }: { icon?: typeof FileSearch; title: string; text: string; action?: ReactNode }) {
  return <div className="empty-state"><div className="empty-icon"><Icon size={22} /></div><h3>{title}</h3><p>{text}</p>{action}</div>
}

function LoginPage({ onLogin }: { onLogin: () => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      await login(username.trim(), password)
      onLogin()
    } catch (cause) {
      setError(errorMessage(cause))
    } finally {
      setBusy(false)
    }
  }
  return (
    <main className="login-shell">
      <div className="login-aside">
        <div className="brand brand-inverse"><div className="brand-mark"><Shield size={19} /></div><span>pramaan<span className="brand-ai">.ai</span></span></div>
        <div className="login-message"><span className="eyebrow">TRUST, VERIFIED</span><h1>Documents<br />tell a story.<br /><em>We help you<br />see the truth.</em></h1><p>One clear view of every credential, check, and decision.</p></div>
        <div className="login-footer"><span className="brand-dot" /> Secure verification workspace</div>
      </div>
      <section className="login-panel">
        <div className="login-form-wrap">
          <span className="eyebrow">WELCOME BACK</span><h2>Sign in to your workspace</h2><p className="muted">Use your Pramaan AI account credentials to continue.</p>
          {error && <Notice>{error}</Notice>}
          <form onSubmit={submit} className="form-stack">
            <label>Username<input autoComplete="username" required value={username} onChange={(event) => setUsername(event.target.value)} placeholder="Your username" /></label>
            <label>Password<input autoComplete="current-password" type="password" required value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Your password" /></label>
            <button className="button button-primary button-wide" type="submit" disabled={busy}>{busy ? <LoaderCircle className="spin" size={17} /> : <ArrowRight size={17} />}{busy ? 'Signing in…' : 'Sign in'}</button>
          </form>
          <p className="secure-note"><Shield size={14} /> Credentials are kept only for this browser session.</p>
        </div>
        <span className="login-copyright">Pramaan AI · Verification made clear</span>
      </section>
    </main>
  )
}

function Shell({ onLogout, children }: { onLogout: () => void; children: ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false)
  const location = useLocation()
  const applicationId = location.pathname.match(/^\/applications\/([^/]+)/)?.[1]
  const navClass = ({ isActive }: { isActive: boolean }) => `nav-link${isActive ? ' nav-active' : ''}`
  return (
    <div className="app-shell">
      <aside className={`sidebar${mobileOpen ? ' sidebar-open' : ''}`}>
        <Link to="/" className="brand"><div className="brand-mark"><Shield size={19} /></div><span>pramaan<span className="brand-ai">.ai</span></span></Link>
        <div className="workspace-label">WORKSPACE</div>
        <nav className="primary-nav" aria-label="Main navigation">
          <NavLink to="/" end className={navClass} onClick={() => setMobileOpen(false)}><LayoutDashboard size={18} />Overview</NavLink>
          <NavLink to="/applications" className={navClass} onClick={() => setMobileOpen(false)}><BriefcaseBusiness size={18} />Applications</NavLink>
          {applicationId && <Link to={`/applications/${applicationId}?tab=audit`} className="nav-link"><Activity size={18} />Audit trail</Link>}
        </nav>
        <div className="sidebar-bottom">
          <div className="security-card"><div className="security-icon"><Fingerprint size={19} /></div><div><strong>Secure by design</strong><span>Session-protected access</span></div></div>
          <div className="profile-row"><div className="avatar">{(getUsername()[0] || 'U').toUpperCase()}</div><div className="profile-text"><strong>{getUsername() || 'Workspace user'}</strong><span>{humanize(getRole())}</span></div><button className="icon-button logout-button" onClick={onLogout} aria-label="Sign out"><LogOut size={17} /></button></div>
        </div>
      </aside>
      {mobileOpen && <button className="mobile-scrim" onClick={() => setMobileOpen(false)} aria-label="Close menu" />}
      <div className="main-column">
        <header className="topbar">
          <button className="icon-button menu-button" onClick={() => setMobileOpen(!mobileOpen)} aria-label="Toggle navigation"><Menu size={19} /></button>
          <div className="breadcrumb">Pramaan AI <ChevronRight size={14} /> <span>Verification workspace</span></div>
          <div className="topbar-end"><span className="live-tag"><span /> API workspace</span><div className="topbar-divider" /><button className="icon-button" aria-label="Notifications are not configured" title="Notifications are not configured"><Bell size={18} /></button></div>
        </header>
        <main className="page-content">{children}</main>
        <footer className="app-footer"><span>Pramaan AI</span><span>Evidence-led verification</span></footer>
      </div>
    </div>
  )
}

function PageHeading({ eyebrow, title, description, action }: { eyebrow: string; title: string; description?: string; action?: ReactNode }) {
  return <div className="page-heading"><div><span className="eyebrow">{eyebrow}</span><h1>{title}</h1>{description && <p>{description}</p>}</div>{action && <div className="heading-actions">{action}</div>}</div>
}

function Dashboard() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [applications, setApplications] = useState<Application[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const load = useCallback(async () => {
    try {
      const [nextSummary, nextApps] = await Promise.all([client.dashboard(), client.applications()])
      setSummary(nextSummary)
      setApplications(nextApps)
    } catch (cause) {
      setError(errorMessage(cause))
    } finally {
      setLoading(false)
    }
  }, [])
  useEffect(() => { void Promise.resolve().then(load) }, [load])
  const summaryValues = summary ? Object.entries(summary).filter(([, value]) => typeof value === 'number' || typeof value === 'string').slice(0, 4) : []
  return (
    <>
      <PageHeading eyebrow="OVERVIEW" title="Good to see you." description="A clear picture of your verification work, all in one place." action={<button className="button button-secondary" onClick={() => { setError(''); setLoading(true); void load() }} disabled={loading}><RefreshCw size={16} />Refresh</button>} />
      {error && <Notice onDismiss={() => setError('')}>{error}</Notice>}
      {loading ? <Loading label="Loading your dashboard…" /> : <>
        <section className="welcome-banner"><div className="welcome-orb"><Sparkles size={20} /></div><div><span className="eyebrow">YOUR WORKSPACE</span><h2>Verification, without the guesswork.</h2><p>Review submitted documents, surface inconsistencies, and keep every decision traceable.</p></div><Link className="banner-link" to="/applications">Go to applications <ArrowRight size={16} /></Link></section>
        <section className="metric-grid" aria-label="Dashboard summary">
          {summaryValues.length ? summaryValues.map(([key, value], index) => {
            const icons = [BriefcaseBusiness, FileCheck2, ShieldAlert, ClipboardCheck]
            const Icon = icons[index] || Activity
            return <div className="metric-card" key={key}><div className={`metric-icon metric-icon-${index}`}><Icon size={18} /></div><span className="metric-label">{humanize(key)}</span><strong>{String(value)}</strong><span className="metric-caption">Reported by your workspace</span></div>
          }) : <div className="metric-empty"><Activity size={18} /><span>Summary metrics will appear when the API returns them.</span></div>}
        </section>
        <section className="panel recent-panel">
          <div className="panel-heading"><div><span className="eyebrow">RECENT WORK</span><h2>Applications</h2></div><Link className="text-link" to="/applications">View all <ArrowRight size={15} /></Link></div>
          {applications.length ? <ApplicationsTable applications={applications.slice(0, 5)} /> : <EmptyState icon={BriefcaseBusiness} title="Nothing here yet" text="Create an application to start reviewing documents and verification findings." action={<Link className="button button-primary" to="/applications"><Plus size={16} />Create application</Link>} />}
        </section>
      </>}
    </>
  )
}

function ApplicationsTable({ applications }: { applications: Application[] }) {
  return <div className="table-scroll"><table><thead><tr><th>Application</th><th>Reference</th><th>Status</th><th>Documents</th><th>Findings</th><th>Created</th><th><span className="sr-only">Open</span></th></tr></thead><tbody>{applications.map((application) => <tr key={application.id}><td><Link className="table-primary" to={`/applications/${application.id}`}>{application.name || 'Untitled application'}</Link></td><td>{application.reference_number || '—'}</td><td><StatusPill value={application.status} /></td><td>{application.documents_count ?? '—'}</td><td>{application.findings_count ?? '—'}</td><td>{formatDate(application.created_at)}</td><td><Link className="row-arrow" to={`/applications/${application.id}`} aria-label={`Open ${application.name}`}><ChevronRight size={17} /></Link></td></tr>)}</tbody></table></div>
}

function ApplicationsPage() {
  const isAdmin = getRole() === 'admin'
  const [apps, setApps] = useState<Application[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [creating, setCreating] = useState(false)
  const [name, setName] = useState('')
  const [reference, setReference] = useState('')
  const [query, setQuery] = useState('')
  const [busy, setBusy] = useState(false)
  const load = useCallback(async () => {
    try { setApps(await client.applications()) } catch (cause) { setError(errorMessage(cause)) } finally { setLoading(false) }
  }, [])
  useEffect(() => { void Promise.resolve().then(load) }, [load])
  async function create(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      await client.createApplication({ institution_name: name.trim(), ...(reference.trim() ? { reference_number: reference.trim() } : {}) })
      setName('')
      setReference('')
      setCreating(false)
      await load()
    } catch (cause) { setError(errorMessage(cause)) } finally { setBusy(false) }
  }
  const filtered = apps.filter((app) => `${app.name} ${app.reference_number || ''} ${app.status || ''}`.toLowerCase().includes(query.toLowerCase()))
  return <>
    <PageHeading eyebrow="WORKSPACE / APPLICATIONS" title="Applications" description="Track documents, checks, and reviewer decisions for each case." action={isAdmin && <button className="button button-primary" onClick={() => setCreating(!creating)}><Plus size={17} />New application</button>} />
    {error && <Notice onDismiss={() => setError('')}>{error}</Notice>}
    {creating && isAdmin && <form className="create-card" onSubmit={create}><div><span className="eyebrow">NEW CASE</span><h2>Create an application</h2><p className="muted">Enter the applicant or case name. Reference number is optional.</p></div><div className="create-fields"><label>Application name<input required value={name} onChange={(event) => setName(event.target.value)} placeholder="Applicant or case name" /></label><label>Reference number <span className="optional-label">Optional</span><input value={reference} onChange={(event) => setReference(event.target.value)} placeholder="External case reference" /></label></div><div className="create-actions"><button type="button" className="button button-secondary" onClick={() => setCreating(false)}>Cancel</button><button className="button button-primary" disabled={busy}>{busy ? <LoaderCircle className="spin" size={16} /> : <Plus size={16} />}{busy ? 'Creating…' : 'Create application'}</button></div></form>}
    <section className="panel applications-panel"><div className="list-toolbar"><div><h2>All applications <span className="count-badge">{apps.length}</span></h2><p className="muted">Cases returned by your workspace API</p></div><label className="search-field"><Search size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search applications" aria-label="Search applications" /></label></div>
      {loading ? <Loading label="Loading applications…" /> : filtered.length ? <ApplicationsTable applications={filtered} /> : apps.length ? <EmptyState title="No matches" text="Try another search term." /> : <EmptyState icon={BriefcaseBusiness} title="No applications yet" text="When applications are created, they will appear here. Start a case to begin document verification." action={isAdmin && <button className="button button-primary" onClick={() => setCreating(true)}><Plus size={16} />Create application</button>} />}
    </section>
  </>
}

function ApplicationPage() {
  const { id = '' } = useParams()
  const [params, setParams] = useSearchParams()
  const [application, setApplication] = useState<Application | null>(null)
  const [documents, setDocuments] = useState<DocumentRecord[]>([])
  const [findings, setFindings] = useState<Finding[]>([])
  const [verifications, setVerifications] = useState<VerificationRecord[]>([])
  const [audit, setAudit] = useState<AuditEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState('')
  const [notice, setNotice] = useState('')
  const [documentType, setDocumentType] = useState('institution_certificate')
  const [file, setFile] = useState<File | null>(null)
  const [note, setNote] = useState<Record<string, string>>({})
  const [reviewChoice, setReviewChoice] = useState<Record<string, ReviewAction>>({})
  const [verifyResult, setVerifyResult] = useState<Record<string, unknown> | null>(null)
  const isAdmin = getRole() === 'admin'
  const location = useLocation()
  const tab = params.get('tab') || 'documents'
  const load = useCallback(async () => {
    try {
      const [app, docs, nextFindings, nextVerifications] = await Promise.all([
        client.application(id),
        client.documents(id),
        client.findings(id),
        client.verifications(id),
      ])
      setApplication(app)
      setDocuments(docs)
      setFindings(nextFindings)
      setVerifications(nextVerifications)
      if (params.get('tab') === 'audit') {
        setAudit(await client.audit(id))
      }
    } catch (cause) { setError(errorMessage(cause)) } finally { setLoading(false) }
  }, [id, params])
  useEffect(() => { void Promise.resolve().then(load) }, [load])
  useEffect(() => {
    if (tab !== 'documents' || !location.hash) return
    const documentId = decodeURIComponent(location.hash.slice(1))
    requestAnimationFrame(() => document.getElementById(documentId)?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
  }, [tab, location.hash, documents])
  function selectTab(next: string) { setParams(next === 'documents' ? {} : { tab: next }) }
  async function upload(event: FormEvent) {
    event.preventDefault()
    if (!file || !documentType.trim()) return
    setBusy('upload')
    setError('')
    try {
      await client.upload(id, file, documentType.trim())
      setFile(null)
      setDocumentType('')
      const input = document.getElementById('document-file') as HTMLInputElement | null
      if (input) input.value = ''
      setNotice('Document uploaded. The displayed status and extracted values will reflect the API response.')
      await load()
    } catch (cause) { setError(errorMessage(cause)) } finally { setBusy('') }
  }
  async function runValidation() {
    setBusy('validate')
    setError('')
    try {
      await client.validate(id)
      setNotice('Validation request completed. Findings below are loaded from the API.')
      await load()
    } catch (cause) { setError(errorMessage(cause)) } finally { setBusy('') }
  }
  async function verify(doc: DocumentRecord) {
    setBusy(`verify-${doc.id}`)
    setError('')
    try {
      const result = await client.verifyDocument(doc.id)
      setVerifyResult(result && typeof result === 'object' ? result as Record<string, unknown> : { result })
      setNotice('')
      await load()
    } catch (cause) { setError(errorMessage(cause)) } finally { setBusy('') }
  }
  async function download(doc: DocumentRecord) {
    setError('')
    try {
      await client.downloadDocument(doc.id, doc.original_filename || `document-${doc.id}`)
    } catch (cause) {
      setError(errorMessage(cause))
    }
  }
  async function action(finding: Finding, actionName: ReviewAction) {
    setBusy(`finding-${finding.id}`)
    setError('')
    try {
      await client.findingAction(finding.id, actionName, note[String(finding.id)] || '')
      setNotice(`Reviewer action "${humanize(actionName)}" submitted.`)
      setNote((current) => ({ ...current, [String(finding.id)]: '' }))
      await load()
    } catch (cause) { setError(errorMessage(cause)) } finally { setBusy('') }
  }
  if (loading) return <Loading label="Loading application details…" />
  if (error && !application) return <><Link className="back-link" to="/applications"><ArrowLeft size={16} />All applications</Link><Notice>{error}</Notice></>
  if (!application) return <EmptyState title="Application unavailable" text="The API did not return this application." action={<Link className="button button-secondary" to="/applications">Back to applications</Link>} />
  return <>
    <Link className="back-link" to="/applications"><ArrowLeft size={16} />All applications</Link>
    <div className="detail-heading"><div><span className="eyebrow">APPLICATION / {application.reference_number || `#${application.id}`}</span><h1>{application.name || 'Untitled application'}</h1><div className="detail-meta"><StatusPill value={application.status} /><span>Created {formatDate(application.created_at)}</span></div></div><button className="button button-secondary" onClick={() => { setLoading(true); void load() }} disabled={Boolean(busy)}><RefreshCw size={16} />Refresh</button></div>
    {error && <Notice onDismiss={() => setError('')}>{error}</Notice>}
    {notice && <div className="success-notice" role="status"><CheckCircle2 size={17} />{notice}<button className="icon-button" onClick={() => setNotice('')} aria-label="Dismiss message"><X size={16} /></button></div>}
    <div className="detail-stats"><div><FileText size={17} /><strong>{application.documents_count ?? documents.length}</strong><span>Documents</span></div><div><ShieldAlert size={17} /><strong>{application.findings_count ?? findings.length}</strong><span>Findings</span></div><div><Clock3 size={17} /><strong>{humanize(application.status)}</strong><span>Current status</span></div></div>
    <div className="tabs" role="tablist" aria-label="Application sections">
      <button role="tab" aria-selected={tab === 'documents'} className={tab === 'documents' ? 'tab active-tab' : 'tab'} onClick={() => selectTab('documents')}><FileText size={16} />Documents <span>{documents.length}</span></button>
      <button role="tab" aria-selected={tab === 'findings'} className={tab === 'findings' ? 'tab active-tab' : 'tab'} onClick={() => selectTab('findings')}><ShieldAlert size={16} />Findings <span>{findings.length}</span></button>
      <button role="tab" aria-selected={tab === 'audit'} className={tab === 'audit' ? 'tab active-tab' : 'tab'} onClick={() => selectTab('audit')}><Activity size={16} />Audit trail</button>
    </div>
    {tab === 'documents' && <div className="detail-layout"><section className="panel document-panel"><div className="panel-heading"><div><span className="eyebrow">EVIDENCE</span><h2>Submitted documents</h2></div><button className="button button-secondary button-small" onClick={runValidation} disabled={Boolean(busy)}>{busy === 'validate' ? <LoaderCircle className="spin" size={15} /> : <ClipboardCheck size={15} />}{busy === 'validate' ? 'Checking…' : 'Run validation'}</button></div>
        {documents.length ? <div className="document-list">{documents.map((doc) => {
          const documentVerifications = verifications.filter((record) => record.document_id === String(doc.id))
          return <article className="document-card" id={`document-${doc.id}`} key={doc.id}><div className="doc-title-row"><div className="file-icon"><FileText size={19} /></div><div className="doc-title"><strong>{doc.original_filename || `Document ${doc.id}`}</strong><span>{humanize(doc.document_type)}{doc.pages ? ` · ${doc.pages} pages` : ''}</span></div><StatusPill value={doc.status} /></div>
          {doc.fields?.length ? <div className="fields-table"><div className="fields-header"><span>EXTRACTED VALUE</span><span>VALUE</span><span>CONFIDENCE</span><span>PAGE</span></div>{doc.fields.map((field, index) => <div className="field-row" key={`${field.name}-${index}`}><strong>{humanize(field.name)}</strong><span>{field.value == null || field.value === '' ? '—' : String(field.value)}</span><span>{field.confidence == null ? '—' : `${Math.round(field.confidence <= 1 ? field.confidence * 100 : field.confidence)}%`}</span><span>{field.page ?? '—'}</span></div>)}</div> : <div className="extraction-empty"><FileSearch size={16} />No extracted fields returned for this document.</div>}
          {doc.metadata?.ocr_message && <div className="review-needed"><CircleAlert size={14} />{doc.metadata.ocr_message}</div>}
          {doc.sha256 && <div className="hash-row"><Fingerprint size={14} />SHA-256 <code>{doc.sha256}</code></div>}
          <div className="doc-actions"><button className="button button-secondary button-small" onClick={() => void download(doc)}><FileText size={14} />Download original</button><span>Issuer check <b className="simulated-label">SIMULATED — SYNTHETIC TEST DATA</b></span><button className="button button-secondary button-small" onClick={() => void verify(doc)} disabled={Boolean(busy)}>{busy === `verify-${doc.id}` ? <LoaderCircle className="spin" size={14} /> : <BadgeCheck size={15} />}Run simulated check</button></div>
          {documentVerifications.map((record) => <div className="verification-record" key={record.id}><span>{record.label}</span><StatusPill value={record.result} /><small>{formatDate(record.created_at)}</small></div>)}
          {doc.extracted_text && <details className="extracted-text"><summary>View extracted text</summary><pre>{doc.extracted_text}</pre></details>}
          </article>
        })}</div> : <EmptyState icon={FileText} title="No documents submitted" text="Upload a document to see its API-reported status and extracted fields here." />}
      </section>
      {isAdmin && <section className="panel upload-panel"><div className="panel-heading"><div><span className="eyebrow">ADD EVIDENCE</span><h2>Upload a document</h2></div><div className="upload-badge"><Upload size={16} /></div></div><form className="form-stack" onSubmit={upload}><label>Document type<input required value={documentType} onChange={(event) => setDocumentType(event.target.value)} placeholder="e.g. institution_certificate" /></label><label className="file-drop"><input id="document-file" type="file" accept="application/pdf,image/png,image/jpeg,.pdf,.png,.jpg,.jpeg" required onChange={(event) => setFile(event.target.files?.[0] || null)} /><span className="upload-placeholder"><Upload size={19} /><strong>{file?.name || 'Choose a file to upload'}</strong><small>PDF, PNG or JPEG · sent directly to the private API</small></span></label><button className="button button-primary button-wide" disabled={busy === 'upload' || !file || !documentType.trim()}>{busy === 'upload' ? <LoaderCircle className="spin" size={16} /> : <FilePlus2 size={16} />}{busy === 'upload' ? 'Uploading…' : 'Upload document'}</button></form><p className="panel-footnote"><Shield size={14} />Accepted file types and limits are enforced by the API.</p></section>}</div>}
    {tab === 'findings' && <section className="panel findings-panel"><div className="panel-heading"><div><span className="eyebrow">REVIEW QUEUE</span><h2>Validation findings</h2></div><button className="button button-secondary button-small" onClick={runValidation} disabled={Boolean(busy)}><ClipboardCheck size={15} />{busy === 'validate' ? 'Checking…' : 'Run validation'}</button></div>
      {findings.length ? <div className="finding-list">{findings.map((finding) => <article className="finding-card" key={finding.id}>      <div className="finding-top"><div className={`severity-icon severity-${(finding.severity || '').toLowerCase()}`}><ShieldAlert size={18} /></div><div className="finding-title"><strong>{finding.rule_name || finding.rule_id || 'Validation finding'}</strong><span>{finding.rule_id ? `${finding.rule_id} · ` : ''}{finding.field_name ? `${humanize(finding.field_name)} · ` : ''}{finding.source_document_id ? <Link to={`/applications/${id}?tab=documents#document-${finding.source_document_id}`}>{finding.source_filename || 'View source document'}</Link> : finding.source_filename || 'Source not specified'}</span></div><StatusPill value={finding.severity} /><StatusPill value={finding.status} /></div>
        <p className="finding-reason">{finding.reason || 'The API did not provide a reason for this finding.'}</p>
        {finding.evidence && <blockquote className="evidence"><span>“{finding.evidence}”</span><small>{finding.source_filename || 'Evidence'}{finding.page ? ` · Page ${finding.page}` : ''}</small></blockquote>}
        {finding.recommended_action && <div className="recommendation"><Sparkles size={15} /><span><b>Suggested next step</b>{finding.recommended_action}</span></div>}
        {finding.manual_review_required && <div className="review-needed"><CircleAlert size={14} />Manual review required</div>}
        <div className="review-controls"><label className="note-input">Reviewer note<input value={note[String(finding.id)] || ''} onChange={(event) => setNote((current) => ({ ...current, [String(finding.id)]: event.target.value }))} placeholder="Add context for the audit trail" /></label><div className="review-actions"><label className="review-action-select">Action<select value={reviewChoice[String(finding.id)] || 'acknowledge'} onChange={(event) => setReviewChoice((current) => ({ ...current, [String(finding.id)]: event.target.value as ReviewAction }))}><option value="acknowledge">Acknowledge</option><option value="confirm">Confirm finding</option><option value="resolve">Mark resolved</option><option value="request_correction">Request correction</option><option value="manual_verification">Send for manual verification</option></select></label><button className="button button-primary button-small" onClick={() => void action(finding, reviewChoice[String(finding.id)] || 'acknowledge')} disabled={Boolean(busy)}>{busy === `finding-${finding.id}` ? <LoaderCircle className="spin" size={14} /> : <Check size={14} />}Record action</button></div></div>
      </article>)}</div> : <EmptyState icon={CheckCircle2} title="No findings returned" text="Run validation to request checks. If the API returns no findings, this queue will remain clear." />}</section>}
    {tab === 'audit' && <section className="panel audit-panel"><div className="panel-heading"><div><span className="eyebrow">TRACEABILITY</span><h2>Audit trail</h2></div><button className="button button-secondary button-small" onClick={() => void load()}><RefreshCw size={15} />Refresh</button></div>{audit.length ? <div className="timeline">{audit.map((entry, index) => <div className="timeline-item" key={`${entry.created_at}-${index}`}><span className="timeline-dot"><Activity size={13} /></span><div className="timeline-content"><div><strong>{humanize(entry.action)}</strong><span>{formatDate(entry.created_at)}</span></div><p>{typeof entry.details === 'string' ? entry.details : entry.details ? JSON.stringify(entry.details) : 'No additional details provided.'}</p><small>Actor: {entry.actor || 'Not specified'}</small></div></div>)}</div> : <EmptyState icon={Activity} title="No audit activity returned" text="Actions recorded by the API for this application will appear here." />}</section>}
    {verifyResult && <div className="modal-backdrop" role="presentation" onClick={() => setVerifyResult(null)}><section className="result-modal" role="dialog" aria-modal="true" aria-labelledby="verify-title" onClick={(event) => event.stopPropagation()}><button className="icon-button modal-close" onClick={() => setVerifyResult(null)} aria-label="Close"><X size={18} /></button><div className="modal-symbol"><BadgeCheck size={22} /></div><span className="eyebrow">SIMULATED — SYNTHETIC TEST DATA</span><h2 id="verify-title">Issuer check response</h2><p className="muted">This check is a simulation. It does not contact a real issuer or confirm document authenticity.</p><pre className="json-result">{JSON.stringify(verifyResult, null, 2)}</pre><button className="button button-primary button-wide" onClick={() => setVerifyResult(null)}>Done</button></section></div>}
  </>
}

function AppRoutes({ onLogout }: { onLogout: () => void }) {
  return <Shell onLogout={onLogout}><Routes><Route path="/" element={<Dashboard />} /><Route path="/applications" element={<ApplicationsPage />} /><Route path="/applications/:id" element={<ApplicationPage />} /><Route path="*" element={<EmptyState title="Page not found" text="This workspace page does not exist." action={<Link to="/" className="button button-secondary">Return to overview</Link>} />} /></Routes></Shell>
}

function App() {
  const [authenticated, setAuthenticated] = useState(isAuthenticated)
  const navigate = useNavigate()
  function signOut() {
    logout()
    setAuthenticated(false)
    navigate('/')
  }
  if (!authenticated) return <LoginPage onLogin={() => setAuthenticated(true)} />
  return <AppRoutes onLogout={signOut} />
}

export default function AppRoot() {
  return <BrowserRouter><App /></BrowserRouter>
}
