import { Check, Clipboard, Download, FileText, Image as ImageIcon, Info, Save, ScanText } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import ConfidenceBadge from '../components/ConfidenceBadge'
import { exportDocument, getDocument, resolveImageUrl, saveDocumentCorrection } from '../services/documentService'
import { findRecentDocument, formatDate, friendlyStatus, normalizeDocument } from '../utils/documents'

export default function DocumentDetails() {
  const { id } = useParams()
  const location = useLocation()
  const [doc, setDoc] = useState(() => location.state?.document || findRecentDocument(id))
  const [loading, setLoading] = useState(!doc)
  const [copied, setCopied] = useState(false)
  const [exportMode, setExportMode] = useState('clean')
  const [exporting, setExporting] = useState('')
  const [exportError, setExportError] = useState('')
  const [editedText, setEditedText] = useState('')
  const [saving, setSaving] = useState(false)
  const [correctionError, setCorrectionError] = useState('')

  useEffect(() => {
    let active = true
    setLoading(true)
    getDocument(id).then((data) => active && setDoc(normalizeDocument(data))).catch(() => {}).finally(() => active && setLoading(false))
    return () => { active = false }
  }, [id])

  useEffect(() => {
    setEditedText(doc?.corrected_text || doc?.extracted_text || '')
  }, [doc?.id, doc?.corrected_text, doc?.extracted_text])

  if (loading && !doc) return <p className="text-sm text-slate-500">Loading document…</p>
  if (!doc) return <Unavailable />

  const originalText = doc.extracted_text || ''
  const displayText = doc.corrected_text || originalText
  const results = doc.ocr_results || []

  const copy = async () => {
    if (!displayText) return
    await navigator.clipboard.writeText(displayText)
    setCopied(true)
    setTimeout(() => setCopied(false), 1800)
  }

  const download = () => {
    if (!displayText) return
    const blob = new Blob([displayText], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `${doc.filename.replace(/\.[^.]+$/, '') || 'extracted-text'}.txt`
    anchor.click()
    URL.revokeObjectURL(url)
  }

  const saveCorrection = async () => {
    setSaving(true)
    setCorrectionError('')
    try {
      const updated = await saveDocumentCorrection(doc.id, editedText)
      setDoc(normalizeDocument(updated))
    } catch (error) {
      setCorrectionError(error.response?.data?.detail || 'Could not save your correction.')
    } finally {
      setSaving(false)
    }
  }

  const requestExport = async (format) => {
    setExporting(format)
    setExportError('')
    try {
      const output = await exportDocument(doc.id, format, exportMode)
      const anchor = document.createElement('a')
      anchor.href = resolveImageUrl(output.file)
      anchor.download = ''
      anchor.click()
    } catch (error) {
      setExportError(error.response?.data?.detail || 'Could not create this export.')
    } finally {
      setExporting('')
    }
  }

  return <div className="space-y-6">
    <header className="flex flex-wrap items-start justify-between gap-3">
      <div><Link to="/documents" className="text-sm font-semibold text-indigo-600">← Documents</Link><h2 className="mt-2 text-2xl font-bold tracking-tight">{doc.filename}</h2><p className="mt-1 text-sm text-slate-500">Uploaded {formatDate(doc.created_at)} · Document ID {doc.id}</p></div>
      <span className="rounded-full bg-emerald-50 px-3 py-1.5 text-sm font-semibold text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300">{friendlyStatus(doc.status)}</span>
    </header>

    <div className="grid gap-6 xl:grid-cols-2">
      <Panel icon={ImageIcon} title="Original upload">{doc.uploaded_file ? <img src={resolveImageUrl(doc.uploaded_file)} alt={`Uploaded ${doc.filename}`} className="max-h-[440px] w-full rounded-xl bg-slate-50 object-contain dark:bg-slate-900" /> : <NoData label="The API did not return an image URL." />}</Panel>
      <Panel icon={ScanText} title="Processed scan">{doc.processed_file ? <img src={resolveImageUrl(doc.processed_file)} alt={`Processed scan for ${doc.filename}`} className="max-h-[440px] w-full rounded-xl bg-slate-50 object-contain dark:bg-slate-900" /> : <NoData label="Processing did not produce a scan image." />}</Panel>
    </div>

    <section className="rounded-2xl border border-slate-200/80 bg-white p-5 dark:border-slate-800 dark:bg-[#111a2b]">
      <div className="flex flex-wrap items-center justify-between gap-3"><div><h3 className="font-bold">Human review editor</h3><p className="mt-1 text-sm text-slate-500">Correct OCR text, then save it as a verified human correction.</p></div><div className="flex gap-2"><button onClick={copy} disabled={!displayText} className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm font-semibold disabled:opacity-40 dark:border-slate-700">{copied ? <Check size={16} className="text-emerald-600" /> : <Clipboard size={16} />}{copied ? 'Copied' : 'Copy'}</button><button onClick={download} disabled={!displayText} className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-40"><Download size={16} />Download TXT</button></div></div>
      <textarea value={editedText} onChange={(event) => setEditedText(event.target.value)} className="mt-5 min-h-64 w-full rounded-xl bg-slate-50 p-4 font-mono text-sm leading-7 text-slate-700 outline-none ring-indigo-500 focus:ring-2 dark:bg-slate-900 dark:text-slate-300" aria-label="Correct extracted text" />
      <div className="mt-3 flex flex-wrap items-center gap-3"><button onClick={saveCorrection} disabled={saving || editedText === (doc.corrected_text || originalText)} className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"><Save size={16} />{saving ? 'Saving…' : 'Save verified correction'}</button>{doc.corrected_text && <span className="text-sm font-medium text-emerald-600">Human-corrected text is saved.</span>}</div>
      {correctionError && <p className="mt-3 text-sm text-rose-600">{correctionError}</p>}
    </section>

    <section className="rounded-2xl border border-slate-200/80 bg-white p-5 dark:border-slate-800 dark:bg-[#111a2b]"><h3 className="font-bold">Reconstructed exports</h3><p className="mt-1 text-sm text-slate-500">Original preserves OCR geometry; clean uses a readable digital layout.</p><div className="mt-4 flex flex-wrap items-center gap-3"><label className="text-sm font-medium">Layout <select value={exportMode} onChange={(event) => setExportMode(event.target.value)} className="ml-2 rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-900"><option value="clean">Clean layout</option><option value="original">Original layout</option></select></label><button onClick={() => requestExport('pdf')} disabled={!!exporting} className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm font-semibold disabled:opacity-50 dark:border-slate-700"><Download size={16} />{exporting === 'pdf' ? 'Creating PDF…' : 'Export PDF'}</button><button onClick={() => requestExport('docx')} disabled={!!exporting} className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"><Download size={16} />{exporting === 'docx' ? 'Creating DOCX…' : 'Export DOCX'}</button></div>{exportError && <p className="mt-3 text-sm text-rose-600">{exportError}</p>}</section>

    <section className="rounded-2xl border border-slate-200/80 bg-white p-5 dark:border-slate-800 dark:bg-[#111a2b]"><div className="flex gap-3"><Info className="mt-0.5 shrink-0 text-indigo-500" size={19} /><div className="min-w-0 flex-1"><h3 className="font-bold">Text detections and confidence</h3><p className="mt-1 text-sm leading-6 text-slate-500">Low-confidence detections are highlighted for review.</p>{doc.average_confidence != null && <div className="mt-3"><ConfidenceBadge value={doc.average_confidence} /></div>}{results.length > 0 && <div className="mt-4 space-y-2">{results.map((result, index) => <div key={`${result.text}-${index}`} className={`flex flex-wrap items-center gap-3 rounded-xl p-3 text-sm ${result.confidence < 0.7 ? 'bg-amber-50 ring-1 ring-amber-200 dark:bg-amber-500/10' : 'bg-slate-50 dark:bg-slate-900'}`}><span className="min-w-0 flex-1 truncate font-medium">{result.text}</span><ConfidenceBadge value={result.confidence} /><span className="text-xs text-slate-400">{result.bounding_box?.length || 0} points</span></div>)}</div>}</div></div></section>
  </div>
}

function Panel({ icon: Icon, title, children }) { return <section className="rounded-2xl border border-slate-200/80 bg-white p-5 dark:border-slate-800 dark:bg-[#111a2b]"><div className="mb-4 flex items-center gap-2"><Icon size={18} className="text-indigo-600" /><h3 className="font-bold">{title}</h3></div>{children}</section> }
function NoData({ label }) { return <div className="grid min-h-56 place-items-center rounded-xl bg-slate-50 p-6 text-center text-sm text-slate-400 dark:bg-slate-900">{label}</div> }
function Unavailable() { return <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center dark:border-slate-700 dark:bg-[#111a2b]"><FileText className="mx-auto text-slate-400" /><h2 className="mt-4 text-lg font-bold">Document unavailable</h2><p className="mt-1 text-sm text-slate-500">This document could not be loaded from the API.</p><Link className="mt-5 inline-block text-sm font-semibold text-indigo-600" to="/documents">Back to documents</Link></div> }
