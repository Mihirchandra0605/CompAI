import React, { useRef } from 'react'

/**
 * UploadCard — reusable file input card
 *
 * Props:
 *   title       — Card heading string
 *   description — Short purpose description
 *   icon        — Emoji or SVG icon string
 *   accept      — File types string e.g. ".pdf,.docx"
 *   multiple    — Boolean, allow multiple files
 *   files       — Current state value (File | File[] | null)
 *   onChange    — Setter function
 *   sectionKey  — Unique key string for IDs
 */
export default function UploadCard({
  title,
  description,
  icon,
  accept,
  multiple = false,
  files,
  onChange,
  sectionKey,
}) {
  const inputRef = useRef(null)

  const handleChange = (e) => {
    if (multiple) {
      onChange([...e.target.files])
    } else {
      onChange(e.target.files[0] || null)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    const dropped = [...e.dataTransfer.files]
    if (multiple) {
      onChange(dropped)
    } else {
      onChange(dropped[0] || null)
    }
  }

  const handleDragOver = (e) => e.preventDefault()

  const handleRemove = (indexToRemove) => {
    if (multiple) {
      onChange(files.filter((_, i) => i !== indexToRemove))
    } else {
      onChange(null)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  const hasFiles = multiple ? files && files.length > 0 : !!files

  // Accepted extensions as display pills
  const acceptList = accept.split(',').map(a => a.trim())

  return (
    <div className="bg-card border border-border rounded-xl p-5 flex flex-col gap-4 transition-all duration-200 hover:border-muted">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-faint border border-border flex items-center justify-center text-lg">
            {icon}
          </div>
          <div>
            <h3 className="font-display font-semibold text-sm text-white tracking-wide">
              {title}
            </h3>
            <p className="text-xs text-gray-500 mt-0.5 font-body">{description}</p>
          </div>
        </div>
        {hasFiles && (
          <span className="text-xs font-mono text-success border border-success/30 bg-success/10 px-2 py-0.5 rounded-full">
            ✓ {multiple ? `${files.length} file${files.length > 1 ? 's' : ''}` : '1 file'}
          </span>
        )}
      </div>

      {/* Accepted formats */}
      <div className="flex flex-wrap gap-1.5">
        {acceptList.map((ext) => (
          <span key={ext} className="tag-pill">{ext}</span>
        ))}
      </div>

      {/* Drop Zone */}
      <div
        className={`upload-zone ${hasFiles ? 'has-file' : ''}`}
        onClick={() => inputRef.current?.click()}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
      >
        <input
          ref={inputRef}
          id={`input-${sectionKey}`}
          type="file"
          accept={accept}
          multiple={multiple}
          onChange={handleChange}
          className="hidden"
        />

        {!hasFiles ? (
          <div className="flex flex-col items-center gap-2 py-4 text-center">
            <div className="text-2xl opacity-40">↑</div>
            <p className="text-xs text-gray-500">
              <span className="text-accent font-medium">Click to browse</span> or drag & drop
            </p>
            <p className="text-xs text-gray-600">
              {multiple ? 'Multiple files allowed' : 'Single file only'}
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-1.5 py-1" onClick={(e) => e.stopPropagation()}>
            {multiple
              ? files.map((f, i) => (
                  <FileRow key={i} file={f} onRemove={() => handleRemove(i)} />
                ))
              : <FileRow file={files} onRemove={() => handleRemove(null)} />
            }
            {/* Add more button for multiple */}
            {multiple && (
              <button
                onClick={(e) => { e.stopPropagation(); inputRef.current?.click() }}
                className="mt-1 text-xs text-accent hover:text-accent-dim transition-colors font-mono border border-dashed border-muted rounded px-3 py-1.5 w-full"
              >
                + Add more files
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function FileRow({ file, onRemove }) {
  const sizeKB = (file.size / 1024).toFixed(1)
  const sizeMB = (file.size / (1024 * 1024)).toFixed(2)
  const displaySize = file.size > 1024 * 1024 ? `${sizeMB} MB` : `${sizeKB} KB`

  return (
    <div className="flex items-center justify-between bg-faint rounded-md px-3 py-2 group">
      <div className="flex items-center gap-2 min-w-0">
        <span className="text-accent text-xs">◈</span>
        <span className="text-xs text-gray-300 font-mono truncate max-w-[180px]">{file.name}</span>
        <span className="text-xs text-gray-600 shrink-0">{displaySize}</span>
      </div>
      <button
        onClick={onRemove}
        className="text-gray-600 hover:text-error transition-colors text-xs ml-2 opacity-0 group-hover:opacity-100"
        title="Remove file"
      >
        ✕
      </button>
    </div>
  )
}
