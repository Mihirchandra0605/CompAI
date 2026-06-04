import React from 'react'

/**
 * StatusMessage — displays upload feedback
 * status: { type: 'idle'|'loading'|'success'|'error', message: '', data: null }
 */
export default function StatusMessage({ status }) {
  if (status.type === 'idle') return null

  if (status.type === 'loading') {
    return (
      <div className="flex items-center gap-3 bg-faint border border-border rounded-lg px-4 py-3 fade-up">
        <div className="spinner shrink-0" />
        <p className="text-sm text-gray-400 font-body">Uploading files to backend...</p>
      </div>
    )
  }

  if (status.type === 'success') {
    const d = status.data
    return (
      <div className="bg-success/5 border border-success/30 rounded-lg px-4 py-4 fade-up shadow-glow-success">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-success text-base">✓</span>
          <p className="text-sm font-display font-semibold text-success">Upload Successful</p>
        </div>
        {d && (
          <div className="space-y-2">
            <p className="text-xs font-mono text-gray-400">
              Session: <span className="text-accent">{d.session_id}</span>
            </p>
            <div className="flex flex-wrap gap-2 mt-2">
              {Object.entries(d.files_saved).map(([key, count]) => (
                <span
                  key={key}
                  className="text-xs font-mono px-2 py-0.5 rounded bg-success/10 border border-success/20 text-success"
                >
                  {key}: {count}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    )
  }

  if (status.type === 'error') {
    return (
      <div className="bg-error/5 border border-error/30 rounded-lg px-4 py-3 fade-up shadow-glow-error">
        <div className="flex items-center gap-2">
          <span className="text-error text-base">✕</span>
          <p className="text-sm font-body text-error">{status.message}</p>
        </div>
      </div>
    )
  }

  return null
}
