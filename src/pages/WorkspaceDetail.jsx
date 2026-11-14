import { useState, useEffect, useRef, useMemo } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  ArrowLeft,
  Copy,
  Check,
  Save,
  Download,
  RotateCcw,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Sparkles,
  Search,
  Undo2,
  X,
  Replace,
  ZoomIn,
  ZoomOut,
  RotateCw,
  ExternalLink,
  Columns,
  FileText,
  Image as ImageIcon,
  Eye,
} from 'lucide-react'
import {
  getDocument,
  saveDocumentCorrection,
  exportDocument,
  reprocessDocument,
  autocorrectDocument,
  resolveImageUrl,
} from '../services/documentService'

export default function WorkspaceDetail() {
  const { id } = useParams()
  const [doc, setDoc] = useState(null)
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [copied, setCopied] = useState(false)
  const [exporting, setExporting] = useState('')
  const [error, setError] = useState('')
  const [reprocessing, setReprocessing] = useState(false)

  // Layout mode: 'split' (side-by-side) | 'text' (editor only) | 'image' (image only)
  const [layoutMode, setLayoutMode] = useState('split')

  // Document image viewer state
  const [imageVersion, setImageVersion] = useState('original') // 'original' | 'processed'
  const [zoom, setZoom] = useState(1)
  const [rotation, setRotation] = useState(0)

  // Smart spelling & OCR correction state
  const [autocorrecting, setAutocorrecting] = useState(false)
  const [autocorrectNotice, setAutocorrectNotice] = useState(null)
  const [undoText, setUndoText] = useState(null)

  // Find & Replace state
  const [showFindReplace, setShowFindReplace] = useState(false)
  const [findQuery, setFindQuery] = useState('')
  const [replaceQuery, setReplaceQuery] = useState('')

  const textareaRef = useRef(null)

  const fetchDoc = async () => {
    try {
      const data = await getDocument(id)
      setDoc(data)
      setText(data.corrected_text || data.extracted_text || '')
      if (data.processed_file) {
        setImageVersion('processed')
      } else {
        setImageVersion('original')
      }
      setError('')
      return data
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load document.')
      return null
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDoc()
  }, [id])

  // Count matches for Find & Replace
  const matchCount = useMemo(() => {
    if (!findQuery.trim() || !text) return 0
    try {
      const regex = new RegExp(findQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi')
      const matches = text.match(regex)
      return matches ? matches.length : 0
    } catch {
      return 0
    }
  }, [findQuery, text])

  const handleCopy = async () => {
    if (!text) return
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleSelectAll = () => {
    if (textareaRef.current) {
      textareaRef.current.select()
    }
  }

  const handleAutoCorrect = async () => {
    setAutocorrecting(true)
    setError('')
    try {
      const res = await autocorrectDocument(id, text)
      if (res.corrected_text !== text) {
        setUndoText(text)
        setText(res.corrected_text)

        const count = res.changes_count || 0
        const samples = (res.changes || [])
          .slice(0, 2)
          .map((c) => `"${c.original}" → "${c.replacement}"`)
          .join(', ')

        setAutocorrectNotice({
          count,
          message:
            count > 0
              ? `Cleaned ${count} spelling/OCR issue${count > 1 ? 's' : ''}${
                  samples ? ` (e.g. ${samples})` : ''
                }`
              : 'Text analyzed. No common spelling or OCR noise errors found.',
        })
      } else {
        setAutocorrectNotice({
          count: 0,
          message: 'Text is already clean! No spelling or OCR errors detected.',
        })
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not auto-correct text.')
    } finally {
      setAutocorrecting(false)
    }
  }

  const handleUndo = () => {
    if (undoText !== null) {
      setText(undoText)
      setUndoText(null)
      setAutocorrectNotice(null)
    }
  }

  const handleReplaceOne = () => {
    if (!findQuery || !text) return
    setUndoText(text)
    const regex = new RegExp(findQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i')
    setText((prev) => prev.replace(regex, replaceQuery))
  }

  const handleReplaceAll = () => {
    if (!findQuery || !text) return
    setUndoText(text)
    const regex = new RegExp(findQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi')
    setText((prev) => prev.replaceAll(regex, replaceQuery))
  }

  const handleSave = async () => {
    setSaving(true)
    setError('')
    try {
      const updated = await saveDocumentCorrection(id, text)
      setDoc(updated)
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not save text corrections.')
    } finally {
      setSaving(false)
    }
  }

  const handleExport = async (format) => {
    setExporting(format)
    setError('')
    try {
      if (text !== (doc.corrected_text || doc.extracted_text)) {
        await saveDocumentCorrection(id, text)
      }
      const res = await exportDocument(id, format, 'clean')
      const fileUrl = resolveImageUrl(res.file)
      const baseName = doc?.title || doc?.filename || `document_${id}`
      const cleanName = baseName.replace(/\.[^/.]+$/, '')
      const fileName = `${cleanName}_export.${format}`

      // Attempt in-browser blob download first (same-origin blob respects filename and stays on page)
      try {
        const response = await fetch(fileUrl)
        if (!response.ok) throw new Error('Fetch failed')
        const blob = await response.blob()
        const blobUrl = window.URL.createObjectURL(blob)
        const anchor = window.document.createElement('a')
        anchor.href = blobUrl
        anchor.download = fileName
        window.document.body.appendChild(anchor)
        anchor.click()
        window.document.body.removeChild(anchor)
        setTimeout(() => window.URL.revokeObjectURL(blobUrl), 2000)
      } catch {
        // Fallback for cross-origin downloads: open in new tab with target="_blank"
        // so the active document workspace tab is NEVER replaced or navigated away from
        const anchor = window.document.createElement('a')
        anchor.href = fileUrl
        anchor.target = '_blank'
        anchor.rel = 'noopener noreferrer'
        anchor.download = fileName
        window.document.body.appendChild(anchor)
        anchor.click()
        window.document.body.removeChild(anchor)
      }
    } catch (err) {
      setError(err.response?.data?.detail || `Failed to generate ${format.toUpperCase()} export.`)
    } finally {
      setExporting('')
    }
  }

  const handleReprocess = async () => {
    setReprocessing(true)
    setError('')
    try {
      await reprocessDocument(id)
      const interval = setInterval(async () => {
        const updated = await getDocument(id)
        if (updated.status === 'completed' || updated.status === 'failed') {
          clearInterval(interval)
          setDoc(updated)
          setText(updated.extracted_text || '')
          setReprocessing(false)
        }
      }, 1500)
    } catch (err) {
      setError(err.response?.data?.detail || 'Reprocessing failed.')
      setReprocessing(false)
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="text-center">
          <Loader2 className="mx-auto h-8 w-8 animate-spin text-teal-600" />
          <p className="mt-3 text-xs font-semibold text-slate-400">Loading document workspace…</p>
        </div>
      </div>
    )
  }

  if (error && !doc) {
    return (
      <div className="mx-auto max-w-lg py-16 text-center">
        <AlertCircle className="mx-auto h-12 w-12 text-rose-500" />
        <h2 className="mt-4 text-lg font-bold">Document Unavailable</h2>
        <p className="mt-2 text-xs text-slate-400">{error}</p>
        <Link
          to="/documents"
          className="mt-6 inline-flex items-center gap-2 rounded-xl bg-teal-600 px-4 py-2.5 text-xs font-bold text-white shadow-sm"
        >
          <ArrowLeft size={15} /> Return to Documents
        </Link>
      </div>
    )
  }

  const originalText = doc?.extracted_text || ''
  const hasChanges = text !== (doc?.corrected_text || originalText)
  const wordCount = text.trim() ? text.trim().split(/\s+/).length : 0
  const charCount = text.length

  // Image source resolution
  const activeImageField =
    imageVersion === 'processed' && doc?.processed_file
      ? doc.processed_file
      : doc?.uploaded_file

  const imageUrl = resolveImageUrl(activeImageField)
  const isPdf =
    (doc?.uploaded_file || '').toLowerCase().endsWith('.pdf') ||
    (doc?.filename || '').toLowerCase().endsWith('.pdf')

  return (
    <div className="mx-auto max-w-[1600px] space-y-5 py-2">
      {/* Top Navigation & View Options */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200/80 pb-4 dark:border-slate-800">
        <div className="flex items-center gap-3">
          <Link
            to="/documents"
            className="grid h-9 w-9 place-items-center rounded-xl border border-slate-200 text-slate-500 transition hover:bg-slate-100 hover:text-slate-800 dark:border-slate-800 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-white"
          >
            <ArrowLeft size={16} />
          </Link>
          <div>
            <h1 className="text-lg font-bold tracking-tight text-slate-900 sm:text-xl dark:text-white">
              {doc?.filename || doc?.title || 'Document Workspace'}
            </h1>
            <p className="text-xs text-slate-400">
              {wordCount} words · {charCount} characters
              {doc?.corrected_text && ' · Verified'}
            </p>
          </div>
        </div>

        {/* View mode toggle (Side-by-side vs Text only vs Image only) */}
        <div className="flex items-center gap-2">
          <div className="hidden sm:flex items-center rounded-xl border border-slate-200 bg-slate-50 p-1 dark:border-slate-800 dark:bg-slate-900">
            <button
              type="button"
              onClick={() => setLayoutMode('split')}
              className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-semibold transition ${
                layoutMode === 'split'
                  ? 'bg-white text-teal-700 shadow-xs dark:bg-slate-800 dark:text-teal-300'
                  : 'text-slate-500 hover:text-slate-800 dark:text-slate-400'
              }`}
            >
              <Columns size={13} />
              <span>Side-by-Side</span>
            </button>
            <button
              type="button"
              onClick={() => setLayoutMode('text')}
              className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-semibold transition ${
                layoutMode === 'text'
                  ? 'bg-white text-teal-700 shadow-xs dark:bg-slate-800 dark:text-teal-300'
                  : 'text-slate-500 hover:text-slate-800 dark:text-slate-400'
              }`}
            >
              <FileText size={13} />
              <span>Text Only</span>
            </button>
            <button
              type="button"
              onClick={() => setLayoutMode('image')}
              className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-semibold transition ${
                layoutMode === 'image'
                  ? 'bg-white text-teal-700 shadow-xs dark:bg-slate-800 dark:text-teal-300'
                  : 'text-slate-500 hover:text-slate-800 dark:text-slate-400'
              }`}
            >
              <ImageIcon size={13} />
              <span>Original Image</span>
            </button>
          </div>

          <button
            type="button"
            onClick={handleReprocess}
            disabled={reprocessing}
            title="Re-run OCR extraction"
            className="flex items-center gap-1.5 rounded-xl border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-600 transition hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            <RotateCcw size={14} className={reprocessing ? 'animate-spin' : ''} />
            <span className="hidden sm:inline">{reprocessing ? 'Reprocessing…' : 'Reprocess'}</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-xl bg-rose-50 p-3 text-xs font-semibold text-rose-700 dark:bg-rose-950/30 dark:text-rose-300">
          <AlertCircle size={15} />
          <span>{error}</span>
        </div>
      )}

      {/* Main Workspace Body */}
      <div
        className={`grid gap-6 ${
          layoutMode === 'split'
            ? 'grid-cols-1 lg:grid-cols-2'
            : 'grid-cols-1'
        }`}
      >
        {/* ============================================================== */}
        {/* LEFT PANEL: ORIGINAL DOCUMENT IMAGE VIEWER (Side-by-side view) */}
        {/* ============================================================== */}
        {(layoutMode === 'split' || layoutMode === 'image') && (
          <div className="flex flex-col rounded-3xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-[#0c1824] lg:sticky lg:top-20 lg:max-h-[calc(100vh-6rem)]">
            {/* Image Viewer Header Toolbar */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3 dark:border-slate-800">
              <div className="flex items-center gap-2">
                <span className="grid h-7 w-7 place-items-center rounded-lg bg-teal-50 text-teal-600 dark:bg-teal-950/50 dark:text-teal-400">
                  <ImageIcon size={15} />
                </span>
                <span className="text-xs font-bold text-slate-900 dark:text-white">
                  Original Document
                </span>

                {/* Toggle Original vs Enhanced if processed file exists */}
                {doc?.processed_file && (
                  <div className="ml-2 flex items-center rounded-lg border border-slate-200 bg-slate-50 p-0.5 text-[11px] font-semibold dark:border-slate-700 dark:bg-slate-900">
                    <button
                      type="button"
                      onClick={() => setImageVersion('original')}
                      className={`rounded px-2 py-0.5 transition ${
                        imageVersion === 'original'
                          ? 'bg-white text-teal-700 shadow-2xs dark:bg-slate-800 dark:text-teal-300'
                          : 'text-slate-500 hover:text-slate-800 dark:text-slate-400'
                      }`}
                    >
                      Original
                    </button>
                    <button
                      type="button"
                      onClick={() => setImageVersion('processed')}
                      className={`rounded px-2 py-0.5 transition ${
                        imageVersion === 'processed'
                          ? 'bg-white text-teal-700 shadow-2xs dark:bg-slate-800 dark:text-teal-300'
                          : 'text-slate-500 hover:text-slate-800 dark:text-slate-400'
                      }`}
                    >
                      Enhanced
                    </button>
                  </div>
                )}
              </div>

              {/* Zoom & View Controls */}
              {!isPdf && (
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => setZoom((z) => Math.max(0.75, z - 0.25))}
                    title="Zoom Out"
                    className="grid h-7 w-7 place-items-center rounded-lg text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
                  >
                    <ZoomOut size={14} />
                  </button>
                  <span className="min-w-[42px] text-center text-[10px] font-bold text-slate-500">
                    {Math.round(zoom * 100)}%
                  </span>
                  <button
                    type="button"
                    onClick={() => setZoom((z) => Math.min(3, z + 0.25))}
                    title="Zoom In"
                    className="grid h-7 w-7 place-items-center rounded-lg text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
                  >
                    <ZoomIn size={14} />
                  </button>
                  <button
                    type="button"
                    onClick={() => setRotation((r) => (r + 90) % 360)}
                    title="Rotate 90°"
                    className="grid h-7 w-7 place-items-center rounded-lg text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
                  >
                    <RotateCw size={14} />
                  </button>
                  <a
                    href={imageUrl}
                    target="_blank"
                    rel="noreferrer"
                    title="Open Full Image in New Tab"
                    className="grid h-7 w-7 place-items-center rounded-lg text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
                  >
                    <ExternalLink size={14} />
                  </a>
                </div>
              )}
            </div>

            {/* Document Image Container */}
            <div className="mt-3 relative flex-1 overflow-auto rounded-2xl bg-slate-900/5 p-2 dark:bg-black/40 min-h-[420px] max-h-[72vh] flex items-center justify-center">
              {isPdf ? (
                <iframe
                  src={imageUrl}
                  title="PDF Viewer"
                  className="h-full min-h-[500px] w-full rounded-xl border-0"
                />
              ) : imageUrl ? (
                <div className="overflow-auto max-h-full max-w-full flex items-center justify-center p-2">
                  <img
                    src={imageUrl}
                    alt="Original Document"
                    style={{
                      transform: `scale(${zoom}) rotate(${rotation}deg)`,
                      transformOrigin: 'center center',
                      transition: 'transform 0.15s ease-out',
                    }}
                    className="max-h-[68vh] w-auto max-w-full rounded-xl object-contain shadow-xs select-none"
                  />
                </div>
              ) : (
                <div className="p-8 text-center text-xs text-slate-400">
                  <ImageIcon size={32} className="mx-auto mb-2 text-slate-300 dark:text-slate-700" />
                  No image file available
                </div>
              )}
            </div>
          </div>
        )}

        {/* ============================================================== */}
        {/* RIGHT PANEL: EXTRACTED TEXT EDITOR & CONVERSION                */}
        {/* ============================================================== */}
        {(layoutMode === 'split' || layoutMode === 'text') && (
          <div className="space-y-5">
            {/* Text Editor Card */}
            <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-[#0c1824] sm:p-6">
              {/* Header Toolbar */}
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4 dark:border-slate-800">
                <div className="flex items-center gap-2">
                  <span className="grid h-7 w-7 place-items-center rounded-lg bg-teal-50 text-teal-600 dark:bg-teal-950/50 dark:text-teal-400">
                    <FileText size={15} />
                  </span>
                  <span className="text-xs font-bold text-slate-900 dark:text-white">
                    Extracted Text Editor
                  </span>
                </div>

                <div className="flex flex-wrap items-center gap-1.5">
                  {/* Auto-Fix Spelling */}
                  <button
                    type="button"
                    onClick={handleAutoCorrect}
                    disabled={autocorrecting || !text.trim()}
                    title="Auto-fix spelling mistakes, OCR noise suffixes (e.g. 'brain st' → 'brain'), and artifacts"
                    className="flex items-center gap-1 rounded-lg border border-teal-500/30 bg-teal-500/10 px-2.5 py-1 text-xs font-bold text-teal-700 transition hover:bg-teal-500/20 disabled:opacity-50 dark:border-teal-500/30 dark:bg-teal-500/15 dark:text-teal-300"
                  >
                    <Sparkles
                      size={13}
                      className={autocorrecting ? 'animate-spin' : 'text-teal-600 dark:text-teal-400'}
                    />
                    <span>{autocorrecting ? 'Fixing…' : '✨ Auto-Fix'}</span>
                  </button>

                  {/* Find & Replace */}
                  <button
                    type="button"
                    onClick={() => setShowFindReplace((prev) => !prev)}
                    className={`flex items-center gap-1 rounded-lg border px-2.5 py-1 text-xs font-semibold transition ${
                      showFindReplace
                        ? 'border-teal-500 bg-teal-50 text-teal-700 dark:border-teal-500 dark:bg-teal-950/40 dark:text-teal-300'
                        : 'border-slate-200 text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800'
                    }`}
                  >
                    <Search size={13} />
                    <span>Find</span>
                  </button>

                  <button
                    type="button"
                    onClick={handleSelectAll}
                    className="rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-semibold text-slate-600 transition hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                  >
                    Select All
                  </button>

                  <button
                    type="button"
                    onClick={handleCopy}
                    className="flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-semibold text-slate-600 transition hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                  >
                    {copied ? <Check size={13} className="text-emerald-500" /> : <Copy size={13} />}
                    <span>{copied ? 'Copied' : 'Copy'}</span>
                  </button>
                </div>
              </div>

              {/* Collapsible Find & Replace Bar */}
              {showFindReplace && (
                <div className="mt-3 flex flex-wrap items-center gap-2 rounded-xl border border-teal-500/30 bg-teal-50/50 p-2.5 text-xs shadow-2xs dark:border-teal-500/20 dark:bg-slate-900/80">
                  <div className="flex min-w-[170px] flex-1 items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2 py-1 dark:border-slate-700 dark:bg-slate-950">
                    <Search size={13} className="text-slate-400" />
                    <input
                      type="text"
                      value={findQuery}
                      onChange={(e) => setFindQuery(e.target.value)}
                      placeholder="Find (e.g. brain st)..."
                      className="w-full bg-transparent text-xs text-slate-800 outline-none placeholder:text-slate-400 dark:text-slate-200"
                    />
                    {findQuery && (
                      <span className="shrink-0 rounded bg-slate-100 px-1 text-[10px] font-bold text-slate-500 dark:bg-slate-800 dark:text-slate-400">
                        {matchCount}
                      </span>
                    )}
                  </div>

                  <div className="flex min-w-[170px] flex-1 items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2 py-1 dark:border-slate-700 dark:bg-slate-950">
                    <Replace size={13} className="text-slate-400" />
                    <input
                      type="text"
                      value={replaceQuery}
                      onChange={(e) => setReplaceQuery(e.target.value)}
                      placeholder="Replace with..."
                      className="w-full bg-transparent text-xs text-slate-800 outline-none placeholder:text-slate-400 dark:text-slate-200"
                    />
                  </div>

                  <button
                    type="button"
                    onClick={handleReplaceOne}
                    disabled={!matchCount}
                    className="rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 transition hover:bg-slate-100 disabled:opacity-40 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
                  >
                    Replace
                  </button>

                  <button
                    type="button"
                    onClick={handleReplaceAll}
                    disabled={!matchCount}
                    className="rounded-lg bg-teal-600 px-2.5 py-1 text-xs font-bold text-white shadow-2xs transition hover:bg-teal-700 disabled:opacity-40"
                  >
                    Replace All
                  </button>

                  <button
                    type="button"
                    onClick={() => setShowFindReplace(false)}
                    className="rounded-lg p-1 text-slate-400 hover:bg-slate-200/60 dark:hover:bg-slate-800"
                  >
                    <X size={14} />
                  </button>
                </div>
              )}

              {/* Auto-correction Notice Banner */}
              {autocorrectNotice && (
                <div className="mt-3 flex items-center justify-between gap-2 rounded-xl border border-teal-500/20 bg-teal-50/70 px-3.5 py-2 text-xs text-teal-800 dark:border-teal-500/20 dark:bg-teal-950/30 dark:text-teal-200">
                  <div className="flex items-center gap-2">
                    <Sparkles size={14} className="shrink-0 text-teal-600 dark:text-teal-400" />
                    <span>{autocorrectNotice.message}</span>
                  </div>
                  {undoText !== null && (
                    <button
                      type="button"
                      onClick={handleUndo}
                      className="inline-flex items-center gap-1 rounded-md border border-teal-500/30 bg-white px-2 py-0.5 text-xs font-bold text-teal-700 shadow-2xs transition hover:bg-teal-50 dark:border-teal-500/30 dark:bg-slate-900 dark:text-teal-300"
                    >
                      <Undo2 size={12} />
                      <span>Undo</span>
                    </button>
                  )}
                </div>
              )}

              {/* Editable Text Area */}
              <div className="mt-4">
                <textarea
                  ref={textareaRef}
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  placeholder="Extracted text will appear here..."
                  rows={layoutMode === 'split' ? 18 : 22}
                  className="w-full resize-y rounded-2xl border border-slate-200 bg-slate-50/70 p-4 font-mono text-xs sm:text-sm leading-relaxed text-slate-900 outline-none transition focus:border-teal-500 focus:bg-white focus:text-slate-950 dark:border-slate-800 dark:bg-[#07111a] dark:text-slate-100 dark:focus:border-teal-400 dark:focus:bg-[#07111a] dark:focus:text-white"
                />
              </div>

              {/* Editor Footer / Save Action */}
              <div className="mt-3 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-3 dark:border-slate-800">
                <div className="flex items-center gap-3">
                  {saved && (
                    <span className="flex items-center gap-1.5 text-xs font-semibold text-emerald-600 dark:text-emerald-400">
                      <CheckCircle2 size={14} /> Saved successfully
                    </span>
                  )}
                  {hasChanges && !saved && (
                    <span className="text-xs font-medium text-amber-600 dark:text-amber-400">
                      Unsaved edits
                    </span>
                  )}
                  {undoText !== null && (
                    <button
                      type="button"
                      onClick={handleUndo}
                      className="inline-flex items-center gap-1 text-xs font-bold text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200"
                    >
                      <Undo2 size={12} />
                      <span>Undo</span>
                    </button>
                  )}
                </div>

                <button
                  type="button"
                  onClick={handleSave}
                  disabled={saving || !hasChanges}
                  className="flex items-center gap-1.5 rounded-xl bg-teal-600 px-4 py-2 text-xs font-bold text-white shadow-sm transition hover:bg-teal-700 disabled:opacity-40"
                >
                  <Save size={14} />
                  <span>{saving ? 'Saving…' : 'Save Corrections'}</span>
                </button>
              </div>
            </div>

            {/* Convert & Download Section */}
            <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-[#0c1824]">
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-teal-600 dark:text-teal-400">
                  Step 4: Convert &amp; Download
                </h3>
                <p className="mt-0.5 text-xs text-slate-400">
                  All exports use your latest saved corrections. PDF preserves the original image with selectable text overlay. DOCX reconstructs tables and columns as native Word elements.
                </p>
              </div>

              <div className="mt-3 grid grid-cols-1 gap-2.5 sm:grid-cols-3">
                {/* TXT */}
                <button
                  type="button"
                  onClick={() => handleExport('txt')}
                  disabled={!!exporting}
                  className="group flex flex-col items-center gap-1 rounded-xl border border-slate-200 p-3 text-xs font-bold text-slate-700 transition hover:border-teal-500 hover:bg-teal-50/20 disabled:opacity-50 dark:border-slate-800 dark:text-slate-300 dark:hover:border-teal-500 dark:hover:bg-teal-500/10"
                >
                  <span className="flex items-center gap-2">
                    <Download size={14} className="text-teal-600" />
                    <span>Plain Text (.TXT)</span>
                  </span>
                  <span className="text-[10px] font-normal text-slate-400 dark:text-slate-500">Raw corrected text</span>
                </button>

                {/* DOCX */}
                <button
                  type="button"
                  onClick={() => handleExport('docx')}
                  disabled={!!exporting}
                  className="group flex flex-col items-center gap-1 rounded-xl border border-slate-200 p-3 text-xs font-bold text-slate-700 transition hover:border-teal-500 hover:bg-teal-50/20 disabled:opacity-50 dark:border-slate-800 dark:text-slate-300 dark:hover:border-teal-500 dark:hover:bg-teal-500/10"
                >
                  <span className="flex items-center gap-2">
                    <Download size={14} className="text-teal-600" />
                    <span>Structured Word (.DOCX)</span>
                  </span>
                  <span className="text-[10px] font-normal text-slate-400 dark:text-slate-500">Tables · headings · columns</span>
                </button>

                {/* PDF */}
                <button
                  type="button"
                  onClick={() => handleExport('pdf')}
                  disabled={!!exporting}
                  className="group flex flex-col items-center gap-1 rounded-xl border border-slate-200 p-3 text-xs font-bold text-slate-700 transition hover:border-teal-500 hover:bg-teal-50/20 disabled:opacity-50 dark:border-slate-800 dark:text-slate-300 dark:hover:border-teal-500 dark:hover:bg-teal-500/10"
                >
                  <span className="flex items-center gap-2">
                    <Download size={14} className="text-teal-600" />
                    <span>Sandwich PDF (.PDF)</span>
                  </span>
                  <span className="text-[10px] font-normal text-slate-400 dark:text-slate-500">Image + searchable text layer</span>
                </button>
              </div>

              {exporting && (
                <p className="mt-3 flex items-center gap-2 text-xs text-teal-600 dark:text-teal-400">
                  <Loader2 size={12} className="animate-spin" />
                  Generating {exporting.toUpperCase()} export…
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
