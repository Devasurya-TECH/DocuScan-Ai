import { useState, useRef, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  FileText,
  Upload,
  ArrowRight,
  AlertCircle,
  Loader2,
  X,
  FileCheck2,
  Image as ImageIcon,
  Eye,
  RefreshCw,
} from 'lucide-react'
import { uploadDocument, pollDocumentStatus } from '../services/documentService'

export default function NewScan() {
  const [file, setFile] = useState(null)
  const [previewUrl, setPreviewUrl] = useState('')
  const [state, setState] = useState('idle') // 'idle' | 'uploading' | 'processing' | 'failed' | 'completed'
  const [processingStage, setProcessingStage] = useState('')
  const [error, setError] = useState('')
  const [createdDocId, setCreatedDocId] = useState(null)
  const fileInputRef = useRef(null)
  const navigate = useNavigate()

  // Clean up object URL when component unmounts or file changes
  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl)
      }
    }
  }, [previewUrl])

  const formatFileSize = (bytes) => {
    if (!bytes) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
  }

  const handleFileChange = (e) => {
    const selected = e.target.files?.[0]
    if (!selected) return

    setError('')
    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'application/pdf']
    const isPdfExt = selected.name.toLowerCase().endsWith('.pdf')

    if (!allowedTypes.includes(selected.type) && !isPdfExt) {
      setError('Unsupported file type. Please upload a JPG, PNG, or PDF document.')
      setFile(null)
      setPreviewUrl('')
      return
    }

    if (selected.size > 15 * 1024 * 1024) {
      setError('File is too large. Maximum supported size is 15 MB.')
      setFile(null)
      setPreviewUrl('')
      return
    }

    if (previewUrl) {
      URL.revokeObjectURL(previewUrl)
    }

    setFile(selected)
    if (selected.type.startsWith('image/')) {
      const url = URL.createObjectURL(selected)
      setPreviewUrl(url)
    } else {
      setPreviewUrl('')
    }
  }

  const handleRemove = () => {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl)
    }
    setFile(null)
    setPreviewUrl('')
    setError('')
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const handleProcess = async () => {
    if (!file) return
    setError('')
    setState('uploading')

    try {
      const result = await uploadDocument(file)
      setCreatedDocId(result.id)

      if (result.status === 'completed') {
        setState('completed')
        navigate(`/documents/${result.id}`)
        return
      }

      setState('processing')
      setProcessingStage(result.progress_stage || 'starting')
      pollStatus(result.id)
    } catch (err) {
      const data = err.response?.data
      const detail =
        data?.uploaded_file?.[0] ||
        data?.detail ||
        data?.failure_reason ||
        'Upload failed. Please ensure the server is running.'
      setError(detail)
      setState('failed')
    }
  }

  const pollStatus = (docId) => {
    let consecutiveErrors = 0
    const interval = setInterval(async () => {
      try {
        const res = await pollDocumentStatus(docId)
        consecutiveErrors = 0
        setProcessingStage(res.progress_stage || 'processing')

        if (res.status === 'completed') {
          clearInterval(interval)
          setState('completed')
          navigate(`/documents/${docId}`)
        } else if (res.status === 'failed') {
          clearInterval(interval)
          setError(res.failure_reason || 'Processing failed. Please try again.')
          setState('failed')
        }
      } catch (err) {
        consecutiveErrors++
        if (consecutiveErrors >= 10) {
          clearInterval(interval)
          setError('Server took too long to respond. Please try uploading again.')
          setState('failed')
        }
      }
    }, 1500)
  }

  const stageDescriptions = {
    queued: 'Document queued for processing…',
    starting: 'Starting OCR neural engine…',
    pdf_extraction: 'Extracting PDF pages…',
    boundary_detection: 'Detecting document boundary & perspective…',
    ocr_inference: 'Running docTR deep learning OCR…',
    document_understanding: 'Structuring and organizing text…',
    completed: 'Extraction complete! Opening editor…',
    reprocessing: 'Reprocessing document…',
  }

  const isPdf = file?.name?.toLowerCase().endsWith('.pdf') || file?.type === 'application/pdf'
  const isProcessing = state === 'processing' || state === 'uploading'

  return (
    <div className="mx-auto max-w-2xl py-8">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
          Extract Text from Documents
        </h1>
        <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
          Upload any scanned document, photo, receipt, or PDF to extract clean, editable text.
        </p>
      </div>

      {/* Main Upload Card */}
      <div className="mt-8 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8 dark:border-slate-800 dark:bg-[#0c1824]">
        {error && (
          <div className="mb-6 flex items-start gap-3 rounded-2xl bg-rose-50 p-4 text-xs font-semibold text-rose-700 dark:bg-rose-950/30 dark:text-rose-300">
            <AlertCircle size={16} className="mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          id="file-upload"
          accept=".jpg,.jpeg,.png,.pdf,image/jpeg,image/png,application/pdf"
          onChange={handleFileChange}
          className="hidden"
        />

        {!file ? (
          /* Step 1: File selection drop area */
          <div className="text-center">
            <label
              htmlFor="file-upload"
              className="group mx-auto flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-200 px-6 py-12 transition hover:border-teal-500 hover:bg-teal-50/20 dark:border-slate-800 dark:hover:border-teal-500 dark:hover:bg-teal-950/10"
            >
              <div className="grid h-14 w-14 place-items-center rounded-2xl bg-teal-50 text-teal-600 transition group-hover:scale-105 dark:bg-teal-950/40">
                <Upload size={24} />
              </div>
              <span className="mt-4 inline-flex items-center gap-1.5 rounded-xl bg-teal-600 px-5 py-2.5 text-xs font-bold text-white shadow-sm transition hover:bg-teal-700">
                Browse Files
              </span>
              <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
                Supported formats: <strong>JPG, PNG, PDF</strong> (up to 15 MB)
              </p>
            </label>
          </div>
        ) : (
          /* Selected File View WITH LIVE IMAGE PREVIEW */
          <div className="space-y-5">
            {/* Image Preview Box */}
            <div className="relative overflow-hidden rounded-2xl border border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-[#07111a]">
              {previewUrl ? (
                <div className="relative flex max-h-80 w-full items-center justify-center bg-slate-900/5 p-3 dark:bg-black/30">
                  <img
                    src={previewUrl}
                    alt="Document preview"
                    className="max-h-72 w-auto max-w-full rounded-xl object-contain shadow-xs"
                  />
                  <div className="absolute bottom-4 left-4 rounded-lg bg-black/60 px-2.5 py-1 text-[11px] font-semibold text-white backdrop-blur-xs">
                    Image Preview
                  </div>
                </div>
              ) : isPdf ? (
                <div className="flex h-48 w-full flex-col items-center justify-center gap-3 bg-teal-50/30 p-6 text-center dark:bg-teal-950/10">
                  <span className="grid h-16 w-16 place-items-center rounded-2xl bg-teal-100 text-teal-700 dark:bg-teal-950 dark:text-teal-300">
                    <FileText size={32} />
                  </span>
                  <div>
                    <span className="rounded-md bg-teal-600/10 px-2.5 py-0.5 text-xs font-bold text-teal-600 dark:text-teal-400">
                      PDF Document
                    </span>
                    <p className="mt-1 text-xs text-slate-500">Multi-page digital or scanned PDF ready for extraction</p>
                  </div>
                </div>
              ) : null}

              {/* Processing Overlay (visible when uploading/processing) */}
              {isProcessing && (
                <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-slate-950/75 p-6 text-center text-white backdrop-blur-xs">
                  <div className="grid h-14 w-14 place-items-center rounded-2xl bg-teal-500/20 text-teal-300">
                    <Loader2 size={30} className="animate-spin" />
                  </div>
                  <h3 className="mt-4 text-base font-bold text-white">
                    {state === 'uploading' ? 'Uploading Document…' : 'Processing Document'}
                  </h3>
                  <p className="mt-1 max-w-xs text-xs text-teal-200">
                    {stageDescriptions[processingStage] || 'Extracting complete document text…'}
                  </p>
                </div>
              )}
            </div>

            {/* File Info Card */}
            <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50/70 p-3.5 dark:border-slate-800 dark:bg-slate-900/60">
              <div className="flex items-center gap-3 min-w-0">
                <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-teal-100 text-teal-700 dark:bg-teal-950 dark:text-teal-300">
                  {previewUrl ? <ImageIcon size={19} /> : <FileText size={19} />}
                </span>
                <div className="min-w-0">
                  <p className="truncate text-xs font-bold text-slate-900 dark:text-white">
                    {file.name}
                  </p>
                  <p className="text-[11px] text-slate-400">
                    {formatFileSize(file.size)} · {file.type || 'Document'}
                  </p>
                </div>
              </div>

              {!isProcessing && (
                <button
                  type="button"
                  onClick={handleRemove}
                  title="Remove file"
                  className="grid h-8 w-8 place-items-center rounded-lg text-slate-400 transition hover:bg-slate-200 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
                >
                  <X size={15} />
                </button>
              )}
            </div>

            {/* Action Buttons */}
            {!isProcessing && (
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="w-1/3 rounded-xl border border-slate-200 py-3 text-xs font-bold text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                >
                  Choose Another
                </button>
                <button
                  type="button"
                  onClick={handleProcess}
                  className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-teal-600 py-3 text-xs font-extrabold text-white shadow-md shadow-teal-600/25 transition hover:bg-teal-700"
                >
                  <FileCheck2 size={16} />
                  <span>Process Document</span>
                  <ArrowRight size={15} />
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="mt-6 text-center">
        <Link
          to="/documents"
          className="text-xs font-semibold text-slate-400 transition hover:text-teal-600 dark:hover:text-teal-400"
        >
          ← View All Documents
        </Link>
      </div>
    </div>
  )
}
