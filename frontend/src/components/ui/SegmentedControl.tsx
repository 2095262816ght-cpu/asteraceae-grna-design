import React from 'react'
import { cn } from '../../lib/cn'

export interface SegmentOption {
  value: string
  label: React.ReactNode
  icon?: React.ReactNode
}

interface SegmentedControlProps {
  options: SegmentOption[]
  value: string
  onChange: (value: string) => void
  size?: 'sm' | 'md'
  'aria-label'?: string
  className?: string
}

export const SegmentedControl: React.FC<SegmentedControlProps> = ({
  options,
  value,
  onChange,
  size = 'sm',
  className,
  ...rest
}) => (
  <div role="radiogroup" className={cn('flex flex-wrap gap-1.5', className)} {...rest}>
    {options.map((opt) => {
      const selected = opt.value === value
      return (
        <button
          key={opt.value}
          type="button"
          role="radio"
          aria-checked={selected}
          onClick={() => onChange(opt.value)}
          className={cn(
            'inline-flex items-center gap-1.5 rounded-control border font-medium transition-colors',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40',
            size === 'sm' ? 'px-2.5 py-1.5 text-xs' : 'px-3 py-2 text-sm',
            selected
              ? 'border-brand-600 bg-brand-50 text-brand-700'
              : 'border-line bg-surface text-ink-muted hover:border-line-strong hover:text-ink'
          )}
        >
          {opt.icon}
          <span>{opt.label}</span>
        </button>
      )
    })}
  </div>
)
