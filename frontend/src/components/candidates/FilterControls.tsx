import React from 'react'
import type { GeneInfo } from '../../lib/types'

interface FilterControlsProps {
  includeExon: boolean
  includePromoter: boolean
  onRegionChange: (exon: boolean, promoter: boolean) => void
  minScore: number
  onMinScoreChange: (v: number) => void
  excludeCentromere: boolean
  onExcludeCentromereChange: (v: boolean) => void
  currentGene?: GeneInfo
  filteredCandidates?: number
  totalCandidates?: number
}

// 多维过滤控制栏：功能元件（外显子/启动子）+ 最低效率分 + 着丝粒过滤 + 基因信息摘要条
export const FilterControls: React.FC<FilterControlsProps> = ({
  includeExon,
  includePromoter,
  onRegionChange,
  minScore,
  onMinScoreChange,
  excludeCentromere,
  onExcludeCentromereChange,
  currentGene,
  filteredCandidates,
  totalCandidates,
}) => (
  <div className="mt-5 space-y-4">
    {/* 功能元件过滤组 (外显子与启动子) */}
    <div className="flex flex-col gap-3 py-1 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <span className="mb-1 block text-xs font-bold tracking-wider text-ink-muted">
          功能元件过滤 (Functional Region)
        </span>
        <span className="text-2xs text-ink-muted">
          按植物基因组功能区段筛选 gRNA 候选位点（支持多选、单选或全不选）
        </span>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <label className="flex cursor-pointer select-none items-center space-x-2 rounded-control border border-line bg-surface px-3 py-1.5 text-xs font-medium text-ink-muted shadow-sm transition-colors hover:bg-surface-sunken">
          <input
            type="checkbox"
            id="include-exon"
            checked={includeExon}
            onChange={(e) => onRegionChange(e.target.checked, includePromoter)}
            className="h-4 w-4 rounded border-slate-300 accent-brand-600 text-sky-600 focus:ring-sky-500"
          />
          <span className="inline-flex items-center rounded bg-sky-100 px-1.5 py-0.5 text-2xs font-bold text-sky-800">
            外显子 (Exon)
          </span>
          <span className="text-2xs text-ink-muted">基因敲除 (Knockout)</span>
        </label>

        <label className="flex cursor-pointer select-none items-center space-x-2 rounded-control border border-line bg-surface px-3 py-1.5 text-xs font-medium text-ink-muted shadow-sm transition-colors hover:bg-surface-sunken">
          <input
            type="checkbox"
            id="include-promoter"
            checked={includePromoter}
            onChange={(e) => onRegionChange(includeExon, e.target.checked)}
            className="h-4 w-4 rounded border-slate-300 accent-brand-600 text-purple-600 focus:ring-purple-500"
          />
          <span className="inline-flex items-center rounded bg-purple-100 px-1.5 py-0.5 text-2xs font-bold text-purple-800">
            启动子 (Promoter)
          </span>
          <span className="text-2xs text-ink-muted">调控干涉 (CRISPRi/a)</span>
        </label>

        <div className="ml-1 flex items-center space-x-1.5 border-l border-line pl-3">
          <button
            type="button"
            onClick={() => onRegionChange(true, true)}
            className="rounded px-1.5 py-0.5 text-2xs font-medium text-ink-muted transition-colors hover:bg-slate-100 hover:text-brand-600"
            title="同时勾选外显子与启动子"
          >
            全选
          </button>
          <span className="text-slate-300">/</span>
          <button
            type="button"
            onClick={() => onRegionChange(false, false)}
            className="rounded px-1.5 py-0.5 text-2xs font-medium text-ink-muted transition-colors hover:bg-slate-100 hover:text-rose-600"
            title="取消勾选全部功能元件"
          >
            清空
          </button>
        </div>
      </div>
    </div>

    {/* 阈值与物理特性过滤 */}
    <div className="grid grid-cols-1 items-center gap-4 pt-1 md:grid-cols-2">
      {/* 效率分滑块 */}
      <div>
        <div className="mb-1 flex justify-between text-xs font-medium text-ink-muted">
          <span>最低效率分过滤:</span>
          <span className="font-bold text-brand-600">{minScore} 分</span>
        </div>
        <input
          type="range"
          min="0"
          max="90"
          step="5"
          value={minScore}
          onChange={(e) => onMinScoreChange(Number(e.target.value))}
          className="h-2 w-full cursor-pointer appearance-none rounded-control bg-slate-200 accent-brand-600"
        />
      </div>

      {/* 着丝粒过滤开关 */}
      <div className="flex items-center space-x-2.5">
        <input
          type="checkbox"
          id="exclude-centro"
          checked={excludeCentromere}
          onChange={(e) => onExcludeCentromereChange(e.target.checked)}
          className="h-4 w-4 rounded border-slate-300 accent-brand-600 text-brand-600 focus:ring-brand-500"
        />
        <label htmlFor="exclude-centro" className="cursor-pointer text-xs font-medium text-ink-muted">
          排除着丝粒不稳定区靶点 (Centromere Filter)
        </label>
      </div>
    </div>

    {/* 基因信息摘要条 */}
    {currentGene && (
      <div className="glass-inner mt-5 flex flex-wrap items-center justify-between rounded-card px-4 py-2.5 text-xs text-ink-muted">
        <div className="flex items-center space-x-4">
          <span>
            <strong>染色体:</strong> {currentGene.chrom}
          </span>
          <span>
            <strong>区间:</strong> {currentGene.start.toLocaleString()} - {currentGene.end.toLocaleString()} (
            {currentGene.strand}链)
          </span>
          <span>
            <strong>类型:</strong> {currentGene.nlr_type || 'NLR-LRR'}
          </span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-ink-muted">候选靶点:</span>
          <span className="font-semibold text-ink">{filteredCandidates ?? currentGene.candidate_count}</span>
          <span className="text-ink-faint">/ {totalCandidates ?? currentGene.candidate_count} 总条数</span>
        </div>
      </div>
    )}
  </div>
)
