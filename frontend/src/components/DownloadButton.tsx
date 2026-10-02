import React, { useState } from 'react'
import { Download, Loader2, AlertTriangle } from 'lucide-react'

interface DownloadButtonProps {
  url: string
  title?: string
  className?: string
  children: React.ReactNode
}

// fetch + Blob 下载：请求期间给"生成中"反馈，失败时明确报错（<a> 链接下载失败毫无提示）
export const DownloadButton: React.FC<DownloadButtonProps> = ({ url, title, className, children }) => {
  const [busy, setBusy] = useState(false)
  const [errMsg, setErrMsg] = useState<string | null>(null)

  const handleDownload = async () => {
    if (busy) return
    setBusy(true)
    setErrMsg(null)
    try {
      const res = await fetch(url)
      if (!res.ok) {
        const detail = await res.json().catch(() => null)
        throw new Error(detail?.detail || `服务返回 ${res.status}`)
      }
      const blob = await res.blob()
      const cd = res.headers.get('Content-Disposition') || ''
      const m = /filename\*=UTF-8''([^;]+)/.exec(cd) || /filename="?([^";]+)"?/.exec(cd)
      const objectUrl = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = objectUrl
      a.download = m ? decodeURIComponent(m[1]) : ''
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(objectUrl)
    } catch (e) {
      setErrMsg(
        e instanceof TypeError
          ? '服务未连接：请确认后端已启动（Application startup complete）'
          : e instanceof Error
          ? e.message
          : '下载失败'
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <span className="inline-flex flex-col">
      <button
        type="button"
        onClick={handleDownload}
        disabled={busy}
        title={title}
        className={className ?? 'inline-flex items-center gap-1 rounded-control border border-line px-2.5 py-1.5 text-xs text-ink-muted transition-colors hover:bg-surface-sunken disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40'}
      >
        {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
        <span>{busy ? '生成中…' : children}</span>
      </button>
      {errMsg && (
        <span className="mt-1 inline-flex items-center gap-1 text-2xs text-rose-600">
          <AlertTriangle className="h-3 w-3" />
          {errMsg}
        </span>
      )}
    </span>
  )
}
