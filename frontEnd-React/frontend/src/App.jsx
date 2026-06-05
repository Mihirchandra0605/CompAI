import React, { useState } from 'react'
import axios from 'axios'
import UploadCard from './components/UploadCard'
import StatusMessage from './components/StatusMessage'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// ── tiny helper: parse first markdown table found in a string ──────────────
function parseMarkdownTable(md) {
  if (!md) return null
  const lines = md.split('\n').filter(l => l.trim().startsWith('|'))
  if (lines.length < 3) return null
  const splitRow = l =>
    l.split('|').map(c => c.trim()).filter((_, i, a) => i !== 0 && i !== a.length - 1)
  const headers = splitRow(lines[0])
  const rows    = lines.slice(2).map(splitRow)
  return { headers, rows }
}

export default function App() {
  // ── upload state ───────────────────────────────────────────────────────────
  const [regulationFile, setRegulationFile] = useState(null)
  const [repositoryFile, setRepositoryFile] = useState(null)
  const [configFiles,    setConfigFiles]    = useState([])
  const [logFiles,       setLogFiles]       = useState([])
  const [securityFiles,  setSecurityFiles]  = useState([])

  const [status,    setStatus]    = useState({ type: 'idle', message: '', data: null })
  const [activeTab, setActiveTab] = useState('pipeline')

  // ── upload handler ─────────────────────────────────────────────────────────
  const handleUpload = async () => {
    const totalFiles =
      (regulationFile ? 1 : 0) +
      (repositoryFile ? 1 : 0) +
      configFiles.length +
      logFiles.length +
      securityFiles.length

    if (totalFiles === 0) {
      setStatus({ type: 'error', message: 'Please select at least one file before uploading.', data: null })
      return
    }

    const form = new FormData()
    if (regulationFile) form.append('regulation', regulationFile)
    if (repositoryFile) form.append('repository', repositoryFile)
    configFiles.forEach(f   => form.append('configs',   f))
    logFiles.forEach(f      => form.append('logs',      f))
    securityFiles.forEach(f => form.append('security',  f))

    setStatus({ type: 'loading', message: 'Uploading files and running compliance pipeline…', data: null })

    try {
      const response = await axios.post(`${API_URL}/upload`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 10_800_000, // pipeline can take a while (now 3 hours)
      })
      setStatus({ type: 'success', message: '', data: response.data })
      setActiveTab('pipeline')
    } catch (err) {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        'Upload failed. Is the backend running on port 8000?'
      setStatus({ type: 'error', message: msg, data: null })
    }
  }

  // ── reset ──────────────────────────────────────────────────────────────────
  const handleReset = () => {
    setRegulationFile(null)
    setRepositoryFile(null)
    setConfigFiles([])
    setLogFiles([])
    setSecurityFiles([])
    setStatus({ type: 'idle', message: '', data: null })
  }

  const totalSelected =
    (regulationFile ? 1 : 0) +
    (repositoryFile ? 1 : 0) +
    configFiles.length +
    logFiles.length +
    securityFiles.length

  const pipelineResult = status.data ?? null
  const constraintTable = parseMarkdownTable(pipelineResult?.report)

  const verdictIsPass =
    pipelineResult &&
    !pipelineResult.verdict.toLowerCase().includes('non_compliant') &&
    !pipelineResult.verdict.toLowerCase().includes('failed')

  // ── render ─────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-ink">

      {/* ── NAV ── */}
      <nav className="border-b border-border bg-panel/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 rounded bg-accent/20 border border-accent/40 flex items-center justify-center pulse-glow">
              <span className="text-accent text-xs font-mono font-bold">C</span>
            </div>
            <span className="font-display font-bold text-white tracking-wider text-sm">
              COMPLI<span className="text-accent">AI</span>
            </span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-xs font-mono text-gray-600 border border-border px-2 py-1 rounded">v0.1.0 MVP</span>
            <span className="hidden sm:flex items-center gap-1.5 text-xs text-gray-500">
              <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse inline-block" />
              localhost:5173
            </span>
          </div>
        </div>
      </nav>

      {/* ── HERO HEADER ── */}
      <header className="max-w-6xl mx-auto px-6 pt-12 pb-8">
        <div className="flex flex-col gap-2">
          <p className="text-xs font-mono text-accent tracking-[0.2em] uppercase">Compliance Engineering Digital Twin</p>
          <h1 className="font-display font-extrabold text-3xl sm:text-4xl text-white leading-tight">CompliAI Dashboard</h1>
          <p className="text-gray-500 text-sm font-body max-w-xl mt-1">
            Upload your telecom artifacts — regulations, source code, configs, logs, and security evidence — for automated compliance analysis.
          </p>
        </div>
        <div className="flex flex-wrap gap-4 mt-6">
          {[
            { label: 'Files Selected', value: totalSelected },
            { label: 'Sections',       value: '5' },
            { label: 'Backend',        value: 'localhost:8000' },
          ].map(s => (
            <div key={s.label} className="bg-panel border border-border rounded-lg px-4 py-2.5 flex flex-col gap-0.5">
              <span className="text-xs text-gray-600 font-body">{s.label}</span>
              <span className="text-sm font-mono font-semibold text-white">{s.value}</span>
            </div>
          ))}
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 pb-16">

        {/* ══════════════════════════════════════════════════════════════════════
            UPLOAD PANEL  (always visible)
        ══════════════════════════════════════════════════════════════════════ */}
        <div className="flex items-center gap-3 mb-6">
          <span className="text-xs font-mono text-gray-600 uppercase tracking-widest">Input Sections</span>
          <div className="flex-1 border-t border-border" />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          <UploadCard sectionKey="regulation" title="Regulation Input"    description="Telecom regulation documents"     icon="📋" accept=".pdf,.docx,.txt"                      multiple={false} files={regulationFile} onChange={setRegulationFile} />
          <UploadCard sectionKey="repository" title="Repository Input"    description="Source code repository archive"   icon="🗄️" accept=".zip"                                 multiple={false} files={repositoryFile} onChange={setRepositoryFile} />
          <UploadCard sectionKey="configs"    title="Configuration Files" description="Telecom configuration files"      icon="⚙️" accept=".yaml,.yml,.json"                     multiple={true}  files={configFiles}    onChange={setConfigFiles} />
          <UploadCard sectionKey="logs"       title="Logs"                description="Telemetry and latency logs"       icon="📊" accept=".log,.txt,.csv,.json"                 multiple={true}  files={logFiles}       onChange={setLogFiles} />
          <UploadCard sectionKey="security"   title="Security Evidence"   description="Certificates and security artifacts" icon="🔐" accept=".pem,.crt,.txt,.json,.yaml,.yml,.zip" multiple={true}  files={securityFiles}  onChange={setSecurityFiles} />
        </div>

        <div className="mt-8 flex flex-col gap-4">
          <StatusMessage status={status} />
          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={handleUpload}
              disabled={status.type === 'loading'}
              className={`relative flex items-center gap-2.5 px-6 py-3 rounded-lg font-display font-semibold text-sm transition-all duration-200 tracking-wide
                ${status.type === 'loading'
                  ? 'bg-faint text-gray-500 cursor-not-allowed border border-border'
                  : 'bg-accent text-ink hover:bg-accent-dim shadow-glow hover:shadow-none cursor-pointer'}`}
            >
              {status.type === 'loading' ? (
                <><div className="spinner !border-gray-600 ![border-top-color:#888]" />Running Pipeline…</>
              ) : (
                <>
                  <span>↑</span>
                  Upload Inputs
                  {totalSelected > 0 && (
                    <span className="bg-ink/20 text-ink text-xs font-mono px-1.5 py-0.5 rounded">{totalSelected}</span>
                  )}
                </>
              )}
            </button>
            {(totalSelected > 0 || status.type !== 'idle') && (
              <button onClick={handleReset} className="px-4 py-3 rounded-lg font-body text-sm text-gray-500 hover:text-gray-300 border border-border hover:border-muted transition-all duration-200">
                Reset
              </button>
            )}
          </div>
          <p className="text-xs text-gray-700 font-mono">POST → <span className="text-gray-500">{API_URL}/upload</span></p>
        </div>

        {/* ══════════════════════════════════════════════════════════════════════
            RESULTS DASHBOARD  (shown only after successful pipeline run)
        ══════════════════════════════════════════════════════════════════════ */}
        {pipelineResult && (
          <div className="mt-12 space-y-6 fade-up">

            {/* ── Divider ── */}
            <div className="flex items-center gap-3">
              <span className="text-xs font-mono text-gray-600 uppercase tracking-widest">Pipeline Results</span>
              <div className="flex-1 border-t border-border" />
            </div>

            {/* ── Verdict Banner ── */}
            <div className={`border p-6 rounded-xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 backdrop-blur-md
              ${verdictIsPass
                ? 'border-success/30 bg-success/5 shadow-glow-success'
                : 'border-error/30 bg-error/5 shadow-glow-error'}`}>
              <div className="flex items-center gap-4">
                <div className={`w-14 h-14 rounded-full flex items-center justify-center text-3xl font-bold border
                  ${verdictIsPass
                    ? 'border-success/40 text-success bg-success/10'
                    : 'border-error/40 text-error bg-error/10 animate-pulse'}`}>
                  {verdictIsPass ? '✓' : '✕'}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono text-gray-500 uppercase tracking-widest">Compliance Status</span>
                    <span className="text-xs font-mono bg-panel border border-border text-gray-400 px-2 py-0.5 rounded">
                      Run: {pipelineResult.run_id?.slice(0, 8)}
                    </span>
                  </div>
                  <h2 className="text-2xl font-display font-extrabold text-white mt-1 uppercase tracking-wide">
                    Verdict:{' '}
                    <span className={verdictIsPass ? 'text-success' : 'text-error'}>
                      {pipelineResult.verdict.replace(/_/g, ' ')}
                    </span>
                  </h2>
                </div>
              </div>
            </div>

            {/* ── Metrics row ── */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {[
                {
                  label: 'Partial Score',
                  value: pipelineResult.partial_compliance_score != null
                    ? `${(pipelineResult.partial_compliance_score * 100).toFixed(0)}%`
                    : 'N/A',
                  sub: 'Rule execution pass rate',
                  color: 'text-white',
                },
                {
                  label: 'Confidence',
                  value: pipelineResult.confidence != null
                    ? `${(pipelineResult.confidence * 100).toFixed(0)}%`
                    : 'N/A',
                  sub: 'Geometric weighted mean',
                  color: 'text-accent',
                },
                {
                  label: 'Files Saved',
                  value: Object.values(status.data?.files_saved ?? {}).reduce((a, b) => a + b, 0),
                  sub: Object.entries(status.data?.files_saved ?? {}).filter(([, v]) => v > 0).map(([k, v]) => `${k}:${v}`).join('  '),
                  color: 'text-white',
                },
              ].map(m => (
                <div key={m.label} className="bg-panel border border-border rounded-xl p-5 flex flex-col gap-1">
                  <span className="text-xs text-gray-500 font-body uppercase tracking-wider">{m.label}</span>
                  <span className={`text-3xl font-mono font-extrabold ${m.color}`}>{m.value}</span>
                  <span className="text-xs text-gray-600 font-mono mt-1">{m.sub}</span>
                </div>
              ))}
            </div>

            {/* ── Tab nav ── */}
            <div className="border-b border-border flex items-center gap-1">
              {[
                { id: 'pipeline',   label: 'Pipeline Agents' },
                { id: 'validation', label: 'Validation Checks' },
                { id: 'report',     label: 'Audit Report' },
                { id: 'logs',       label: 'Execution Logs' },
              ].map(t => (
                <button
                  key={t.id}
                  onClick={() => setActiveTab(t.id)}
                  className={`px-4 py-2.5 font-display font-semibold text-xs tracking-wider uppercase transition-all border-b-2 cursor-pointer
                    ${activeTab === t.id ? 'border-accent text-accent' : 'border-transparent text-gray-500 hover:text-gray-300'}`}
                >
                  {t.label}
                </button>
              ))}
            </div>

            {/* ── Tab: Pipeline Agents ── */}
            {activeTab === 'pipeline' && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Timeline */}
                <div className="md:col-span-2 space-y-3 relative before:absolute before:left-[19px] before:top-2 before:bottom-2 before:w-0.5 before:bg-border">
                  {pipelineResult.stages.map((stage, idx) => (
                    <div key={stage.name} className="flex gap-4 items-start relative fade-up" style={{ animationDelay: `${idx * 0.04}s` }}>
                      <div className={`w-10 h-10 rounded-full border flex items-center justify-center shrink-0 font-mono text-sm z-10
                        ${stage.status === 'completed' ? 'border-success/40 bg-ink text-success shadow-glow-success'
                          : stage.status === 'failed'  ? 'border-error/40 bg-ink text-error shadow-glow-error'
                          : 'border-muted bg-panel text-gray-500'}`}>
                        {stage.status === 'completed' ? '✓' : stage.status === 'failed' ? '✕' : idx + 1}
                      </div>
                      <div className="bg-panel border border-border rounded-xl p-4 flex-1">
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-display font-bold text-sm text-white capitalize">{stage.name.replace(/_/g, ' ')}</span>
                          <span className="text-xs font-mono text-gray-600 bg-faint px-1.5 py-0.5 rounded">{stage.duration_ms} ms</span>
                        </div>
                        <p className="text-xs text-gray-400 font-body mt-1.5">{stage.description}</p>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Side: reasoning + recommendations */}
                <div className="space-y-4">
                  <div className="bg-panel border border-border rounded-xl p-5">
                    <h4 className="text-xs font-mono text-accent uppercase tracking-wider border-b border-border pb-2 mb-3">Reasoning Chain</h4>
                    <ul className="space-y-2">
                      {pipelineResult.reasoning_chain.map((r, i) => (
                        <li key={i} className="flex gap-2 text-xs font-body text-gray-300">
                          <span className="text-accent shrink-0">→</span><span>{r}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div className="bg-panel border border-border rounded-xl p-5">
                    <h4 className="text-xs font-mono text-error uppercase tracking-wider border-b border-border pb-2 mb-3">Recommendations</h4>
                    <ul className="space-y-2">
                      {pipelineResult.recommendations.map((r, i) => (
                        <li key={i} className="flex gap-2 text-xs font-body text-gray-400">
                          <span className="text-error shrink-0">⚠</span><span>{r}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {/* ── Tab: Validation Checks ── */}
            {activeTab === 'validation' && (
              <div className="bg-panel border border-border rounded-xl p-6 fade-up">
                <h3 className="font-display font-bold text-white mb-4">Numeric Constraint Validation</h3>
                <div className="overflow-x-auto border border-border rounded-lg">
                  <table className="w-full text-left border-collapse text-xs font-mono">
                    <thead>
                      <tr className="bg-card border-b border-border text-gray-400">
                        {['Constraint', 'Operator', 'Threshold', 'Measured', 'Samples', 'Verdict', 'Reasoning'].map(h => (
                          <th key={h} className="px-4 py-3 font-semibold">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {pipelineResult.validation_results.map((vr, i) => {
                        const pass = vr.verdict === 'pass'
                        return (
                          <tr key={i} className="border-b border-border hover:bg-faint transition-all">
                            <td className="px-4 py-3 text-gray-300">{vr.constraint_id || vr.condition_id}</td>
                            <td className="px-4 py-3 text-accent">{vr.operator}</td>
                            <td className="px-4 py-3 text-white">{vr.threshold ?? '—'}</td>
                            <td className="px-4 py-3 text-white">{vr.measured != null ? Number(vr.measured).toFixed(1) : '—'}</td>
                            <td className="px-4 py-3 text-gray-400">{vr.sample_count}</td>
                            <td className="px-4 py-3">
                              <span className={`px-2 py-0.5 rounded text-[10px] font-bold border
                                ${pass
                                  ? 'text-success bg-success/10 border-success/20'
                                  : 'text-error   bg-error/10   border-error/20'}`}>
                                {pass ? '✅ PASS' : '❌ FAIL'}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-gray-500 max-w-[240px] truncate">{vr.reasoning}</td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* ── Tab: Audit Report ── */}
            {activeTab === 'report' && (
              <div className="bg-panel border border-border rounded-xl p-6 space-y-6 fade-up">
                <div className="flex justify-between items-center border-b border-border pb-4">
                  <h3 className="font-display font-bold text-lg text-white">Compliance Audit Report</h3>
                  <span className="text-xs font-mono text-gray-600 bg-faint border border-border px-2.5 py-1 rounded">MARKDOWN</span>
                </div>
                {/* Parsed constraint table */}
                {constraintTable && (
                  <div>
                    <h4 className="text-xs font-mono text-gray-400 uppercase tracking-widest mb-3">Constraint Summary Table</h4>
                    <div className="overflow-x-auto border border-border rounded-lg">
                      <table className="w-full text-left border-collapse text-xs font-mono">
                        <thead>
                          <tr className="bg-card border-b border-border text-gray-400">
                            {constraintTable.headers.map((h, i) => <th key={i} className="px-4 py-3 font-semibold">{h}</th>)}
                          </tr>
                        </thead>
                        <tbody>
                          {constraintTable.rows.map((row, ri) => (
                            <tr key={ri} className="border-b border-border hover:bg-faint">
                              {row.map((cell, ci) => {
                                const isPass = cell.includes('PASS') || cell.includes('✅')
                                const isFail = cell.includes('FAIL') || cell.includes('❌')
                                return (
                                  <td key={ci} className="px-4 py-3 text-gray-300">
                                    {isPass
                                      ? <span className="text-success bg-success/10 border border-success/20 px-2 py-0.5 rounded text-[10px] font-bold">✅ PASS</span>
                                      : isFail
                                      ? <span className="text-error bg-error/10 border border-error/20 px-2 py-0.5 rounded text-[10px] font-bold">❌ FAIL</span>
                                      : cell}
                                  </td>
                                )
                              })}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
                {/* Raw markdown */}
                <div>
                  <h4 className="text-xs font-mono text-gray-400 uppercase tracking-widest mb-3">Raw Report</h4>
                  <pre className="bg-card border border-border rounded-lg p-4 font-mono text-xs text-gray-400 overflow-x-auto whitespace-pre-wrap leading-relaxed">
                    {pipelineResult.report}
                  </pre>
                </div>
              </div>
            )}

            {/* ── Tab: Execution Logs ── */}
            {activeTab === 'logs' && (
              <div className="bg-black border border-border rounded-xl p-5 font-mono text-xs leading-relaxed fade-up">
                <div className="flex items-center justify-between border-b border-border/40 pb-3 mb-4 text-gray-600">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-error" />
                    <span className="w-2.5 h-2.5 rounded-full bg-warn" />
                    <span className="w-2.5 h-2.5 rounded-full bg-success" />
                  </div>
                  <span>pipeline.log — {pipelineResult.generated_at}</span>
                </div>
                <div className="space-y-1.5 max-h-[420px] overflow-y-auto pr-2">
                  {pipelineResult.logs.length > 0
                    ? pipelineResult.logs.map((log, i) => (
                        <div key={i} className="flex gap-3">
                          <span className="text-gray-600 shrink-0">
                            [{new Date(log.timestamp).toLocaleTimeString()}]
                          </span>
                          <span className={
                            log.event.includes('fail') || log.message.toLowerCase().includes('error')
                              ? 'text-error'
                              : log.event.includes('verdict') || log.event.includes('complete')
                              ? 'text-success font-bold'
                              : 'text-gray-300'
                          }>
                            {log.message}
                          </span>
                        </div>
                      ))
                    : <span className="text-gray-600 italic">No events captured.</span>
                  }
                  {/* blinking cursor */}
                  <div className="flex items-center gap-1.5 text-accent mt-2">
                    <span>$</span>
                    <span className="inline-block w-2 h-4 bg-accent animate-pulse" />
                  </div>
                </div>
              </div>
            )}

          </div>
        )}
      </main>
    </div>
  )
}
