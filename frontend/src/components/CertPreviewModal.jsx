/** Certificate preview/download modal. Opens the PDF in an iframe. */
import { Download, X } from 'lucide-react'
import { downloadCertificateUrl } from '../services/api'

export default function CertPreviewModal({ cert, onClose }) {
  if (!cert) return null
  const pdfUrl = downloadCertificateUrl(cert.id)

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal modal-lg"
        onClick={e => e.stopPropagation()}
        style={{ maxHeight: '90vh', display: 'flex', flexDirection: 'column' }}
      >
        <div className="modal-header">
          <div>
            <div className="modal-title">Certificate Preview</div>
            <div className="text-sm text-muted" style={{ marginTop: 4 }}>
              {cert.recipient_name} · {cert.certificate_id}
            </div>
          </div>
          <button className="btn btn-ghost btn-sm" onClick={onClose}>
            <X size={16} />
          </button>
        </div>

        {/* PDF embed */}
        <div style={{ flex: 1, minHeight: 400, background: 'var(--bg-base)', borderRadius: 'var(--radius-md)', overflow: 'hidden' }}>
          <iframe
            src={pdfUrl}
            title="Certificate Preview"
            width="100%"
            height="100%"
            style={{ minHeight: 480, border: 'none', display: 'block' }}
          />
        </div>

        <div className="modal-actions">
          <button className="btn btn-ghost" onClick={onClose}>Close</button>
          <a href={pdfUrl} download className="btn btn-primary">
            <Download size={14} /> Download PDF
          </a>
        </div>
      </div>
    </div>
  )
}
