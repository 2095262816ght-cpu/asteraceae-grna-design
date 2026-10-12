import React from 'react'
import { ArrowUpDown, Info } from 'lucide-react'
import { TISSUE_NAMES, type TargetTissue } from '../../lib/tissues'

interface SortControlProps {
  targetTissue: TargetTissue
  sortBy: string
  sortOrder: string
  onSortByChange: (v: string) => void
  onSortOrderToggle: () => void
  onOpenSortHelp: () => void
}

export const SortControl: React.FC<SortControlProps> = ({
  targetTissue,
  sortBy,
  sortOrder,
  onSortByChange,
  onSortOrderToggle,
  onOpenSortHelp,
}) => (
  <div className="flex items-center space-x-3">
    <span className="text-xs font-medium text-ink-muted">排序依据:</span>
    <select
      value={sortBy}
      onChange={(e) => onSortByChange(e.target.value)}
      className="rounded-control border border-line bg-surface px-3 py-1.5 text-xs font-medium text-ink-muted shadow-sm focus:border-brand-500 focus:outline-none"
    >
      <option value="efficiency_score">on-target 效率分 (v2.1 推荐排序)</option>
      <option value="priority_score">组织优先指数（{TISSUE_NAMES[targetTissue]}）降序 · 方案3推荐</option>
      <option value="hazard_score">功能性脱靶危害（{TISSUE_NAMES[targetTissue]}）升序</option>
      <option value="start">基因物理起始坐标</option>
      <option value="offtarget_count_mis3">潜在脱靶位点数 (升序优先)</option>
      <option value="gc_pct">GC 含量 (%)</option>
    </select>

    <button
      onClick={onSortOrderToggle}
      title="切换升降序"
      className="inline-flex items-center rounded-control border border-line bg-surface p-1.5 text-xs text-ink-muted shadow-sm hover:bg-surface-sunken focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40"
    >
      <ArrowUpDown className="h-4 w-4" />
      <span className="ml-1 text-xs">{sortOrder === 'desc' ? '降序' : '升序'}</span>
    </button>

    <button
      type="button"
      onClick={onOpenSortHelp}
      title="查看各排序方式的详细排名方法"
      className="inline-flex items-center rounded-control border border-line bg-surface p-1.5 text-ink-muted shadow-sm hover:bg-surface-sunken hover:text-brand-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40"
    >
      <Info className="h-4 w-4" />
    </button>
  </div>
)
