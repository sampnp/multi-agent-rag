import { useCallback, useEffect, useRef, useState } from 'react'
import { FileText, Trash2, Upload, CheckCircle, AlertCircle, RefreshCw } from 'lucide-react'
import Sidebar from '../components/layout/Sidebar'
import Header from '../components/layout/Header'
import { documentsApi, type DocumentRecord } from '../services/ragApi'

export default function Documents() {
  const [documents, setDocuments] = useState<DocumentRecord[]>([])
  const [uploading, setUploading] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [error, setError] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const load = useCallback(async () => {
    try {
      setDocuments(await documentsApi.list())
    } catch {
      // silently ignore
    }
  }, [])

  useEffect(() => {
    load()
    const interval = setInterval(load, 4000)
    return () => clearInterval(interval)
  }, [load])

  const handleFiles = async (files: FileList | null) => {
    if (!files?.length) return
    const file = files[0]
    if (file.type !== 'application/pdf') {
      setError('Only PDF files are supported')
      return
    }
    setError('')
    setUploading(true)
    try {
      const doc = await documentsApi.upload(file)
      setDocuments((prev) => [doc, ...prev])
    } catch (e: unknown) {
      setError((e as Error).message)
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = async (id: string) => {
    await documentsApi.delete(id).catch(() => {})
    setDocuments((prev) => prev.filter((d) => d.id !== id))
  }

  const statusIcon = (status: DocumentRecord['status']) => {
    if (status === 'ready') return <CheckCircle className="w-4 h-4 text-green-400" />
    if (status === 'error') return <AlertCircle className="w-4 h-4 text-red-400" />
    return <RefreshCw className="w-4 h-4 text-yellow-400 animate-spin" />
  }

  const statusLabel = (status: DocumentRecord['status']) => {
    if (status === 'ready') return 'text-green-400'
    if (status === 'error') return 'text-red-400'
    return 'text-yellow-400'
  }

  return (
    <div className="flex h-screen bg-gray-900 overflow-hidden">
      <Sidebar />
      <div className="flex flex-col flex-1 ml-60 min-w-0">
        <Header title="Documents" isWsConnected={false} />
        <main className="flex-1 overflow-y-auto p-6">
          {/* Upload zone */}
          <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => { e.preventDefault(); setDragOver(false); handleFiles(e.dataTransfer.files) }}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-colors mb-6
              ${dragOver ? 'border-brand-500 bg-brand-950/20' : 'border-gray-700 hover:border-gray-500'}`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf"
              className="hidden"
              onChange={(e) => handleFiles(e.target.files)}
            />
            <Upload className="w-10 h-10 text-gray-500 mx-auto mb-3" />
            <p className="text-gray-300 font-medium">
              {uploading ? 'Uploading…' : 'Drop a PDF here or click to upload'}
            </p>
            <p className="text-gray-500 text-sm mt-1">Max 50 MB · PDF only</p>
          </div>

          {error && (
            <p className="text-red-400 text-sm bg-red-950/40 border border-red-800 rounded-lg px-4 py-3 mb-4">
              {error}
            </p>
          )}

          {/* Document list */}
          {documents.length === 0 ? (
            <div className="text-center text-gray-500 mt-16">
              <FileText className="w-12 h-12 mx-auto mb-3 opacity-40" />
              <p>No documents yet. Upload a PDF to get started.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {documents.map((doc) => (
                <div
                  key={doc.id}
                  className="flex items-center gap-4 bg-gray-800 border border-gray-700 rounded-xl px-5 py-4"
                >
                  <FileText className="w-8 h-8 text-brand-400 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-white font-medium truncate">{doc.original_name}</p>
                    <div className="flex items-center gap-3 mt-0.5">
                      <span className={`flex items-center gap-1.5 text-xs ${statusLabel(doc.status)}`}>
                        {statusIcon(doc.status)}
                        {doc.status}
                      </span>
                      {doc.status === 'ready' && (
                        <>
                          <span className="text-gray-500 text-xs">·</span>
                          <span className="text-gray-400 text-xs">{doc.page_count} pages</span>
                          <span className="text-gray-500 text-xs">·</span>
                          <span className="text-gray-400 text-xs">{doc.chunk_count} chunks</span>
                        </>
                      )}
                      {doc.status === 'error' && doc.error_message && (
                        <span className="text-red-400 text-xs truncate max-w-xs">{doc.error_message}</span>
                      )}
                    </div>
                  </div>
                  <span className="text-gray-500 text-xs shrink-0">
                    {new Date(doc.created_at).toLocaleDateString()}
                  </span>
                  <button
                    onClick={() => handleDelete(doc.id)}
                    className="text-gray-600 hover:text-red-400 transition-colors shrink-0"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
