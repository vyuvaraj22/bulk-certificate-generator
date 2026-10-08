/** Animated progress bar with label. */
export default function ProgressBar({ value = 0, label, showPct = true }) {
  const pct = Math.min(100, Math.max(0, value))
  return (
    <div>
      <div className="progress-bar-container">
        <div className="progress-bar-fill" style={{ width: `${pct}%` }} />
      </div>
      {(label || showPct) && (
        <div className="progress-info">
          <span>{label}</span>
          {showPct && <span>{pct}%</span>}
        </div>
      )}
    </div>
  )
}
