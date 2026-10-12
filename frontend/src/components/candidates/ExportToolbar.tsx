import React from 'react'
import { Download, FileSpreadsheet, X } from 'lucide-react'

export interface ExportProgress {
  done: number
  total: number
  phase: 'scan' | 'generate'
}

interface ExportToolbarProps {
  selectedCount: number
  batchName: string
  onBatchNameChange: (v: string) => void
  isExporting: boolean
  exportProgress: ExportProgress | null
  pendingScanCount: number
  onExport: (format: 'csv' | 'xlsx') => void
  onClear: () => void
}

// 悬浮多选导出操作栏：勾选即现；导出前逐条脱靶预计算（进度可见）
export const ExportToolbar: React.FC<ExportToolbarProps> = ({
  selectedCount,
  batchName,
  onBatchNameChange,
  isExporting,
  exportProgress,
  pendingScanCount,
  onExport,
  onClear,
}) => (
  <div className="glass-pop fixed bottom-6 left-1/2 z-40 flex -translate-x-1/2 flex-wrap items-center gap-3 rounded-card px-5 py-3">
    <div className="flex items-center gap-2 text-xs font-semibold text-ink">
      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-brand-600 text-[11px] font-bold text-white">
        {selectedCount}
      </span>
      <span>个靶点已勾选</span>
    </div>

    <div className="hidden h-4 w-px bg-line sm:block" />

    <div className="flex items-center gap-2">
      <input
        type="text"
        placeholder="自定义方案名称..."
        value={batchName}
        onChange={(e) => onBatchNameChange(e.target.value)}
        className="w-48 rounded-control border border-line bg-surface px-3 py-1.5 text-xs text-ink placeholder-ink-faint focus:border-brand-500 focus:outline-none"
      />
      {isExporting && exportProgress ? (
        <div className="flex items-center gap-2 rounded-control border border-brand-200 bg-brand-50/70 px-2.5 py-1.5">
          <span className="h-3.5 w-3.5 shrink-0 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" />
          <div
            className="h-1.5 w-36 overflow-hidden rounded-full bg-brand-100"
            role="progressbar"
            aria-label="导出进度"
            aria-valuemin={0}
            aria-valuemax={exportProgress.total}
            aria-valuenow={exportProgress.done}
          >
            <div
              className="h-full rounded-full bg-brand-600 transition-all duration-500"
              style={{
                width: `${Math.round(
                  ((exportProgress.done + (exportProgress.phase === 'scan' ? 0.5 : 0)) /
                    exportProgress.total) *
                    100
                )}%`,
              }}
            />
          </div>
          <span className="text-[10px] font-semibold text-brand-800">
            {exportProgress.phase === 'scan'
              ? `脱靶扫描中 ${Math.min(exportProgress.done + 1, exportProgress.total)}/${exportProgress.total}…约 1 分钟/条`
              : '正在生成导出文件…'}
          </span>
        </div>
      ) : pendingScanCount > 0 ? (
        <span className="max-w-[220px] rounded border border-amber-200 bg-amber-50 px-1.5 py-0.5 text-[10px] text-amber-600">
          {pendingScanCount} 个靶点脱靶数未计算，首次导出需全基因组扫描（约 1 分钟/条）
        </span>
      ) : null}
    </div>

    <div className="flex items-center gap-2">
      <button
        onClick={() => onExport('csv')}
        disabled={isExporting}
        className="inline-flex items-center gap-1.5 rounded-card bg-brand-600 px-3.5 py-1.5 text-xs font-semibold text-white shadow-sm transition-colors hover:bg-brand-700 disabled:opacity-50"
      >
        <Download className="h-3.5 w-3.5" />
        <span>
          {isExporting
            ? exportProgress?.phase === 'scan'
              ? '脱靶扫描中…请稍候'
              : '生成中...'
            : '导出 CSV'}
        </span>
      </button>

      <button
        onClick={() => onExport('xlsx')}
        disabled={isExporting}
        className="inline-flex items-center gap-1.5 rounded-card border border-line bg-surface-sunken px-3.5 py-1.5 text-xs font-semibold text-ink-muted transition-colors hover:bg-slate-100 disabled:opacity-50"
      >
        <FileSpreadsheet className="h-3.5 w-3.5 text-brand-600" />
        <span>
          {isExporting
            ? exportProgress?.phase === 'scan'
              ? '脱靶扫描中…请稍候'
              : '生成中...'
            : '导出 Excel'}
        </span>
      </button>

      <button
        onClick={onClear}
        className="ml-1 rounded-control p-1.5 text-ink-faint transition-colors hover:bg-slate-100 hover:text-ink-muted"
        title="清空已选"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  </div>
)
