import React from 'react'
import { cn } from '../../lib/cn'
import { TISSUE_NAMES, TISSUE_ORDER, type TargetTissue } from '../../lib/tissues'

interface TissueSelectorProps {
  value: TargetTissue
  onChange: (t: TargetTissue) => void
}

// 目标组织切换器 (Target Tissue · 方案3联动)：重排与诊断跟随此选择
export const TissueSelector: React.FC<TissueSelectorProps> = ({ value, onChange }) => (
  <div className="flex flex-col gap-1.5 lg:border-l lg:border-line lg:pl-6">
    <div className="flex items-center justify-between">
      <label className="flex items-center gap-1.5 text-xs font-semibold tracking-wider text-ink-muted">
        <span>目标组织 (方案3联动)</span>
        <span className="text-[10px] font-normal text-ink-faint">重排与诊断跟随此选择</span>
      </label>
    </div>
    <div className="inline-flex rounded-card border border-line/80 bg-slate-100 p-1">
      {TISSUE_ORDER.map((t) => {
        const active = value === t
        return (
          <button
            key={t}
            type="button"
            onClick={() => onChange(t)}
            className={cn(
              'flex items-center gap-1 rounded-control px-3 py-1.5 text-xs font-medium transition-all',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40',
              active
                ? 'border border-brand-100/80 bg-surface font-bold text-brand-800 shadow-sm'
                : 'text-ink-muted hover:bg-surface-sunken hover:text-ink'
            )}
          >
            <span>{TISSUE_NAMES[t]}</span>
            <span className="text-[10px] font-normal text-ink-faint">({t})</span>
          </button>
        )
      })}
    </div>
  </div>
)
