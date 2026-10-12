import React from 'react'
import { Dialog } from '../ui'
import type { SortHelpItem } from '../../lib/candidateQuery'

interface SortHelpDialogProps {
  open: boolean
  onClose: () => void
  items: SortHelpItem[]
  sortBy: string
}

// 排序方式说明弹窗：条目文案取自后端 /api/v1/meta/sort-help（前端不复述公式）
export const SortHelpDialog: React.FC<SortHelpDialogProps> = ({ open, onClose, items, sortBy }) => (
  <Dialog
    open={open}
    onClose={onClose}
    size="md"
    closePriority={0}
    title="排序方式说明 · 各指标详细排名方法"
    subtitle="切换排序指标时自动套用该指标的推荐方向（升降序按钮仍可手动切换）；「未计算」的候选在任何排序下都排在最后"
  >
    <div className="space-y-3 px-5 py-4">
      {items.map((it) => (
        <div
          key={it.key}
          className={`glass-inner rounded-card px-4 py-3 ${
            it.key === sortBy ? 'border-brand-200 bg-brand-50/60' : ''
          }`}
        >
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs font-bold text-ink">{it.title}</span>
            {it.key === sortBy && (
              <span className="shrink-0 rounded-full bg-brand-100 px-2 py-0.5 text-[10px] font-semibold text-brand-700">
                当前选中
              </span>
            )}
          </div>
          <p className="mt-1 text-2xs font-medium text-brand-700">排名方式：{it.direction}</p>
          {it.lines.map((ln) => (
            <p key={ln} className="mt-1 text-2xs leading-relaxed text-ink-muted">
              {ln}
            </p>
          ))}
        </div>
      ))}
    </div>
    <div className="border-t border-line px-5 py-3 text-2xs text-ink-muted">
      各指标完整口径（含特征系数、公式来源）见导出 Excel 的《指标方法说明》sheet。
    </div>
  </Dialog>
)
