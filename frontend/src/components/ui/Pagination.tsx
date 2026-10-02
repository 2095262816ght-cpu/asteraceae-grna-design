import React from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { cn } from '../../lib/cn'

interface PaginationProps {
  page: number
  pageSize: number
  total: number
  /** 提供时在按钮间显示 "{page} / {totalPages}" 页码指示 */
  totalPages?: number
  onPrev: () => void
  onNext: () => void
  className?: string
}

export const Pagination: React.FC<PaginationProps> = ({
  page,
  pageSize,
  total,
  totalPages,
  onPrev,
  onNext,
  className,
}) => {
  const start = (page - 1) * pageSize + 1
  const end = Math.min(page * pageSize, total)
  const nextDisabled = totalPages !== undefined ? page >= totalPages : end >= total
  const btnCls =
    'inline-flex items-center gap-1 rounded-control border border-line bg-surface px-2.5 py-1 text-xs font-medium text-ink-muted shadow-sm transition-colors hover:bg-surface-sunken disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40'

  return (
    <div className={cn('flex items-center justify-between gap-4', className)}>
      <span className="text-xs text-ink-muted">
        显示第 {start} - {end} 条，共 {total} 条
      </span>
      <div className="flex items-center gap-2">
        <button type="button" onClick={onPrev} disabled={page <= 1} className={btnCls}>
          <ChevronLeft className="mr-1 h-4 w-4" />
          上一页
        </button>
        {totalPages !== undefined && (
          <span className="px-2 text-xs font-medium text-ink-muted">
            {page} / {totalPages}
          </span>
        )}
        <button type="button" onClick={onNext} disabled={nextDisabled} className={btnCls}>
          下一页
          <ChevronRight className="ml-1 h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
