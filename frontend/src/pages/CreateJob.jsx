/**
 * Create Job — multi-step form.
 *
 * Steps:
 *  1. Certificate Details
 *  2. Recipients (manual or CSV)
 *  3. Validate & Preview
 *  4. Generate (submit)
 */
import {
  AlertCircle, Check, CheckCircle, Download, FilePlus,
  Plus, Trash2, Upload, X
} from 'lucide-react'
import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import Header from '../components/Header'
import { createJob, csvTemplateUrl, validateCSV } from '../services/api'

// ── Stepper indicator ─────────────────────────────────────────────────────────
const STEPS = ['Certificate Details', 'Recipients', 'Preview & Validate', 'Generate']

function Stepper({ current }) {
  return (
    <div className="stepper">
      {STEPS.map((label, i) => {
        const done = i < current
        const active = i === current
        return (
          <div key={label} className="step-item">
            <div className={`step-num ${done ? 'done' : active ? 'active' : ''}`}>
              {done ? <Check size={14} /> : i + 1}
            </div>
            <div className={`step-label ${active ? 'active' : ''}`}>{label}</div>
            {i < STEPS.length - 1 && (
              <div className={`step-connector ${done ? 'done' : ''}`} />
            )}
          </div>
        )
      })}
    </div>
  )
}

// ── Recipient row (manual) ────────────────────────────────────────────────────
function RecipientRow({ row, index, onChange, onRemove, errors }) {
  const rowErrors = errors.filter(e => e.row === index + 1)
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr auto', gap: 10, alignItems: 'start', padding: '10px 0', borderBottom: '1px solid var(--border-subtle)' }}>
      <div>
        <input
          className={`form-input${rowErrors.some(e=>e.field==='name')?' form-input-error':''}`}
          placeholder="Full Name *"
          value={row.name}
          onChange={e => onChange(index, 'name', e.target.value)}
        />
        {rowErrors.filter(e=>e.field==='name').map((e,i)=><div key={i} className="form-error">{e.message}</div>)}
      </div>
      <div>
        <input
          className={`form-input${rowErrors.some(e=>e.field==='email')?' form-input-error':''}`}
          placeholder="Email *"
          value={row.email}
          onChange={e => onChange(index, 'email', e.target.value)}
        />
        {rowErrors.filter(e=>e.field==='email').map((e,i)=><div key={i} className="form-error">{e.message}</div>)}
      </div>
      <div>
        <input
          className={`form-input${rowErrors.some(e=>e.field==='certificate_id')?' form-input-error':''}`}
          placeholder="Certificate ID *"
          value={row.certificate_id}
          onChange={e => onChange(index, 'certificate_id', e.target.value)}
        />
        {rowErrors.filter(e=>e.field==='certificate_id').map((e,i)=><div key={i} className="form-error">{e.message}</div>)}
      </div>
      <button className="btn btn-ghost btn-sm" onClick={() => onRemove(index)} title="Remove">
        <Trash2 size={14} style={{ color: 'var(--danger)' }} />
      </button>
    </div>
  )
}

// ── Step 1: Certificate Details ───────────────────────────────────────────────
function StepDetails({ data, onChange, errors }) {
  const f = (field) => errors.find(e => e.field === field)
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
      <div className="form-grid-2">
        <div className="form-group">
          <label className="form-label">Event / Course Name <span className="required">*</span></label>
          <input className="form-input" placeholder="e.g. Python Backend Workshop"
            value={data.event_name} onChange={e => onChange('event_name', e.target.value)} />
          {f('event_name') && <div className="form-error">{f('event_name').message}</div>}
        </div>
        <div className="form-group">
          <label className="form-label">Certificate Title <span className="required">*</span></label>
          <input className="form-input" placeholder="e.g. Certificate of Completion"
            value={data.certificate_title} onChange={e => onChange('certificate_title', e.target.value)} />
          {f('certificate_title') && <div className="form-error">{f('certificate_title').message}</div>}
        </div>
      </div>
      <div className="form-grid-2">
        <div className="form-group">
          <label className="form-label">Issuing Organisation <span className="required">*</span></label>
          <input className="form-input" placeholder="e.g. ABC Organisation"
            value={data.organization} onChange={e => onChange('organization', e.target.value)} />
          {f('organization') && <div className="form-error">{f('organization').message}</div>}
        </div>
        <div className="form-group">
          <label className="form-label">Issue Date <span className="required">*</span></label>
          <input className="form-input" type="date"
            value={data.issue_date} onChange={e => onChange('issue_date', e.target.value)} />
          {f('issue_date') && <div className="form-error">{f('issue_date').message}</div>}
        </div>
      </div>
      <div className="form-group">
        <label className="form-label">Description (optional)</label>
        <textarea className="form-textarea" placeholder="Optional subtitle or description…"
          value={data.description} onChange={e => onChange('description', e.target.value)} />
      </div>
    </div>
  )
}

// ── Step 2: Recipients ────────────────────────────────────────────────────────
function StepRecipients({ recipients, onRecipientsChange, errors }) {
  const [mode, setMode] = useState('manual') // 'manual' | 'csv'
  const [dragOver, setDragOver] = useState(false)
  const [csvLoading, setCsvLoading] = useState(false)
  const [csvErrors, setCsvErrors] = useState([])
  const fileInputRef = useRef(null)

  const addRow = () => {
    onRecipientsChange([...recipients, { name: '', email: '', certificate_id: '' }])
  }

  const removeRow = (i) => {
    onRecipientsChange(recipients.filter((_, idx) => idx !== i))
  }

  const updateRow = (i, field, value) => {
    const updated = [...recipients]
    updated[i] = { ...updated[i], [field]: value }
    onRecipientsChange(updated)
  }

  const autoGenId = () => {
    const updated = recipients.map((r, i) => ({
      ...r,
      certificate_id: r.certificate_id || `CERT-${String(i + 1).padStart(4, '0')}`,
    }))
    onRecipientsChange(updated)
  }

  const handleCSV = async (file) => {
    setCsvLoading(true)
    setCsvErrors([])
    try {
      const result = await validateCSV(file)
      onRecipientsChange(result.recipients.map(r => ({
        name: r.name, email: r.email, certificate_id: r.certificate_id,
      })))
      setCsvErrors(result.errors)
      if (result.invalid > 0) toast(`${result.invalid} row(s) had errors and were excluded.`, { icon: '⚠️' })
      else toast.success(`Loaded ${result.valid} recipients from CSV`)
    } catch (e) {
      toast.error(e.displayMessage || 'CSV parsing failed')
    } finally {
      setCsvLoading(false)
    }
  }

  return (
    <div>
      <div className="tabs" style={{ marginBottom: 20 }}>
        <button className={`tab-btn${mode==='manual'?' active':''}`} onClick={()=>setMode('manual')}>Add Manually</button>
        <button className={`tab-btn${mode==='csv'?' active':''}`} onClick={()=>setMode('csv')}>Upload CSV</button>
      </div>

      {mode === 'csv' && (
        <div>
          <div
            className={`drop-zone${dragOver?' drag-over':''}`}
            onDragOver={e=>{e.preventDefault();setDragOver(true)}}
            onDragLeave={()=>setDragOver(false)}
            onDrop={e=>{e.preventDefault();setDragOver(false);const f=e.dataTransfer.files[0];if(f)handleCSV(f)}}
            onClick={()=>fileInputRef.current?.click()}
          >
            <div className="drop-zone-icon"><Upload size={36} /></div>
            <div className="drop-zone-title">{csvLoading ? 'Processing…' : 'Drop CSV file here or click to browse'}</div>
            <div className="drop-zone-sub">Required columns: name, email, certificate_id · Max 5 MB</div>
          </div>
          <input ref={fileInputRef} type="file" accept=".csv" style={{display:'none'}}
            onChange={e=>{if(e.target.files[0])handleCSV(e.target.files[0])}} />

          <div style={{ display:'flex', gap:10, marginTop:12 }}>
            <a href={csvTemplateUrl()} className="btn btn-ghost btn-sm">
              <Download size={13} /> Download Template
            </a>
          </div>

          {csvErrors.length > 0 && (
            <div style={{ marginTop:16 }}>
              <div style={{ fontSize:13, fontWeight:600, color:'var(--danger)', marginBottom:8 }}>
                CSV Errors ({csvErrors.length})
              </div>
              <div className="error-list" style={{ maxHeight:200, overflowY:'auto' }}>
                {csvErrors.map((e,i)=>(
                  <div key={i} className="error-item">
                    <AlertCircle size={13} />
                    Row {e.row} · {e.field}: {e.message}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Manual recipients */}
      <div style={{ marginTop: mode==='csv' && recipients.length>0 ? 20 : 0 }}>
        {recipients.length > 0 && (
          <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:12 }}>
            <div style={{ fontSize:13, color:'var(--text-muted)' }}>{recipients.length} recipient{recipients.length!==1?'s':''}</div>
            <div style={{ display:'flex', gap:8 }}>
              <button className="btn btn-ghost btn-sm" onClick={autoGenId} title="Auto-fill missing Certificate IDs">
                Auto-generate IDs
              </button>
              {mode==='manual' && (
                <button className="btn btn-secondary btn-sm" onClick={addRow}>
                  <Plus size={13} /> Add Row
                </button>
              )}
            </div>
          </div>
        )}

        {mode === 'manual' && (
          <div>
            {/* Column headers */}
            {recipients.length > 0 && (
              <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr 1fr auto', gap:10, paddingBottom:8, borderBottom:'1px solid var(--border)' }}>
                {['Full Name', 'Email', 'Certificate ID', ''].map(h=>(
                  <div key={h} style={{ fontSize:11.5, fontWeight:600, color:'var(--text-muted)', textTransform:'uppercase', letterSpacing:'0.05em' }}>{h}</div>
                ))}
              </div>
            )}
            <div style={{ maxHeight:360, overflowY:'auto' }}>
              {recipients.map((row, i) => (
                <RecipientRow key={i} row={row} index={i} onChange={updateRow} onRemove={removeRow} errors={errors} />
              ))}
            </div>
            <button className="btn btn-secondary mt-12" onClick={addRow} style={{ width:'100%' }}>
              <Plus size={14} /> Add Recipient
            </button>
          </div>
        )}

        {/* CSV mode — show preview table */}
        {mode === 'csv' && recipients.length > 0 && (
          <div className="table-wrap">
            <div style={{ fontSize:13, fontWeight:600, marginBottom:12 }}>Preview ({recipients.length} valid recipients)</div>
            <table className="table">
              <thead><tr><th>#</th><th>Name</th><th>Email</th><th>Certificate ID</th></tr></thead>
              <tbody>
                {recipients.slice(0, 10).map((r,i)=>(
                  <tr key={i}><td>{i+1}</td><td>{r.name}</td><td>{r.email}</td><td>{r.certificate_id}</td></tr>
                ))}
              </tbody>
            </table>
            {recipients.length > 10 && (
              <div style={{ fontSize:12, color:'var(--text-muted)', textAlign:'center', padding:'10px 0' }}>
                …and {recipients.length - 10} more
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Step 3: Preview & Validate ────────────────────────────────────────────────
function StepPreview({ details, recipients, validationErrors }) {
  const totalErrors = validationErrors.length
  const invalidRows = [...new Set(validationErrors.map(e=>e.row))].length
  const validCount = recipients.length - invalidRows

  return (
    <div>
      <div style={{ background:'var(--bg-elevated)', borderRadius:'var(--radius-lg)', padding:'20px 24px', marginBottom:20 }}>
        <div style={{ fontSize:15, fontWeight:700, marginBottom:16 }}>Certificate Details</div>
        <div className="form-grid-2" style={{ gap:10 }}>
          {[
            ['Event', details.event_name],
            ['Title', details.certificate_title],
            ['Organisation', details.organization],
            ['Issue Date', details.issue_date],
            ['Description', details.description || '—'],
          ].map(([k,v])=>(
            <div key={k} style={{ display:'flex', flexDirection:'column', gap:2 }}>
              <span style={{ fontSize:11.5, color:'var(--text-muted)', textTransform:'uppercase', letterSpacing:'0.05em' }}>{k}</span>
              <span style={{ fontSize:14, fontWeight:500 }}>{v}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="summary-grid">
        <div className="summary-item"><div className="num">{recipients.length}</div><div className="lbl">Total</div></div>
        <div className="summary-item"><div className="num success">{validCount}</div><div className="lbl">Valid</div></div>
        <div className="summary-item"><div className="num danger">{invalidRows}</div><div className="lbl">Invalid</div></div>
      </div>

      {validationErrors.length > 0 && (
        <div style={{ marginTop:16 }}>
          <div style={{ fontSize:13, fontWeight:600, color:'var(--danger)', marginBottom:8 }}>Validation Errors</div>
          <div className="error-list" style={{ maxHeight:200, overflowY:'auto' }}>
            {validationErrors.map((e,i)=>(
              <div key={i} className="error-item">
                <AlertCircle size={13} />
                Row {e.row} · <strong>{e.field}</strong>: {e.message}
              </div>
            ))}
          </div>
        </div>
      )}

      {validCount === 0 && (
        <div className="error-item mt-12">
          <AlertCircle size={13} /> No valid recipients. Please go back and fix the errors.
        </div>
      )}
    </div>
  )
}

// ── Main Component ────────────────────────────────────────────────────────────
export default function CreateJob() {
  const nav = useNavigate()
  const [step, setStep] = useState(0)
  const [submitting, setSubmitting] = useState(false)

  const [details, setDetails] = useState({
    event_name: '',
    certificate_title: 'Certificate of Completion',
    organization: '',
    issue_date: new Date().toISOString().slice(0, 10),
    description: '',
  })

  const [recipients, setRecipients] = useState([
    { name: '', email: '', certificate_id: '' }
  ])

  const [detailErrors, setDetailErrors] = useState([])
  const [recipientErrors, setRecipientErrors] = useState([])

  const updateDetail = (field, value) => {
    setDetails(d => ({ ...d, [field]: value }))
    setDetailErrors(e => e.filter(err => err.field !== field))
  }

  // ── Validate step 1 ──────────────────────────────────────────────────────
  const validateDetails = () => {
    const errs = []
    if (!details.event_name.trim()) errs.push({ field: 'event_name', message: 'Event name is required' })
    if (!details.certificate_title.trim()) errs.push({ field: 'certificate_title', message: 'Certificate title is required' })
    if (!details.organization.trim()) errs.push({ field: 'organization', message: 'Organisation is required' })
    if (!details.issue_date) errs.push({ field: 'issue_date', message: 'Issue date is required' })
    setDetailErrors(errs)
    return errs.length === 0
  }

  // ── Validate step 2 ──────────────────────────────────────────────────────
  const validateRecipients = () => {
    const errs = []
    const seenIds = {}
    recipients.forEach((r, i) => {
      const row = i + 1
      if (!r.name || !r.name.trim()) errs.push({ row, field: 'name', message: 'Name is required' })
      if (!r.email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(r.email)) errs.push({ row, field: 'email', message: 'Valid email required' })
      if (!r.certificate_id || !r.certificate_id.trim()) errs.push({ row, field: 'certificate_id', message: 'Certificate ID is required' })
      else {
        if (seenIds[r.certificate_id]) errs.push({ row, field: 'certificate_id', message: `Duplicate ID: ${r.certificate_id}` })
        seenIds[r.certificate_id] = true
      }
    })
    setRecipientErrors(errs)
    return errs.length === 0
  }

  const next = () => {
    if (step === 0 && !validateDetails()) return
    if (step === 1) {
      if (recipients.length === 0) { toast.error('Add at least one recipient'); return }
      validateRecipients() // show errors but still allow next (invalid rows shown in preview)
    }
    setStep(s => s + 1)
  }

  const back = () => setStep(s => s - 1)

  // ── Submit ───────────────────────────────────────────────────────────────
  const handleSubmit = async () => {
    // Filter out invalid recipients
    const invalidRows = new Set(recipientErrors.map(e => e.row - 1))
    const validRecipients = recipients.filter((_, i) => !invalidRows.has(i))

    if (validRecipients.length === 0) {
      toast.error('No valid recipients to generate certificates for.')
      return
    }

    setSubmitting(true)
    try {
      const payload = {
        event_name: details.event_name,
        certificate_title: details.certificate_title,
        organization: details.organization,
        issue_date: details.issue_date,
        description: details.description || null,
        recipients: validRecipients,
      }
      const job = await createJob(payload)
      toast.success(`Job created! Generating ${job.total} certificate(s)…`)
      nav(`/jobs/${job.job_id}`)
    } catch (e) {
      toast.error(e.displayMessage || 'Failed to create job')
    } finally {
      setSubmitting(false)
    }
  }

  // ── Render ───────────────────────────────────────────────────────────────
  const invalidRows = new Set(recipientErrors.map(e => e.row - 1))
  const validCount = recipients.length - invalidRows.size
  const canGenerate = validCount > 0

  return (
    <>
      <Header title="Create Certificate Job" subtitle="Generate bulk certificates in bulk" />
      <main className="main-content">
        <div className="card" style={{ maxWidth: 860, margin: '0 auto' }}>
          <Stepper current={step} />

          {step === 0 && (
            <StepDetails data={details} onChange={updateDetail} errors={detailErrors} />
          )}
          {step === 1 && (
            <StepRecipients recipients={recipients} onRecipientsChange={setRecipients} errors={recipientErrors} />
          )}
          {step === 2 && (
            <StepPreview details={details} recipients={recipients} validationErrors={recipientErrors} />
          )}
          {step === 3 && (
            <div style={{ textAlign: 'center', padding: '32px 0' }}>
              <CheckCircle size={56} style={{ color: 'var(--success)', marginBottom: 16 }} />
              <div style={{ fontFamily:'Sora,sans-serif', fontSize:22, fontWeight:700, marginBottom:8 }}>
                Ready to Generate
              </div>
              <div style={{ color:'var(--text-muted)', fontSize:14, marginBottom:28 }}>
                {validCount} certificate{validCount !== 1 ? 's' : ''} will be generated in the background.
                You'll be taken to the job page to monitor progress.
              </div>
              <div className="summary-grid" style={{ maxWidth: 400, margin: '0 auto 28px' }}>
                <div className="summary-item">
                  <div className="num">{validCount}</div><div className="lbl">Valid</div>
                </div>
                <div className="summary-item">
                  <div className="num danger">{invalidRows.size}</div><div className="lbl">Skipped</div>
                </div>
              </div>
              <button
                className="btn btn-primary btn-lg"
                onClick={handleSubmit}
                disabled={submitting || !canGenerate}
              >
                <FilePlus size={18} />
                {submitting ? 'Creating Job…' : `Generate ${validCount} Certificate${validCount !== 1 ? 's' : ''}`}
              </button>
              {!canGenerate && (
                <div className="form-error mt-12">No valid recipients. Please go back and fix the errors.</div>
              )}
            </div>
          )}

          {/* Navigation buttons */}
          <div style={{ display:'flex', justifyContent:'space-between', marginTop:32, paddingTop:20, borderTop:'1px solid var(--border)' }}>
            <button
              className="btn btn-ghost"
              onClick={step === 0 ? () => nav('/jobs') : back}
            >
              {step === 0 ? 'Cancel' : '← Back'}
            </button>
            {step < 3 && (
              <button className="btn btn-primary" onClick={next}>
                {step === 2 ? 'Confirm & Proceed →' : 'Next →'}
              </button>
            )}
          </div>
        </div>
      </main>

      <style>{`
        .form-input-error { border-color: var(--danger) !important; }
      `}</style>
    </>
  )
}
