import React from 'react'
import { Loader2 } from 'lucide-react'
import { cn } from '../../lib/cn'

export const Spinner: React.FC<{ size?: 'sm' | 'md'; label?: string; className?: string }> = ({
  size = 'md',
  label,
  className,
}) => (
  <span className={cn('inline-flex items-center gap-2 text-ink-muted', className)}>
    <Loader2
      className={cn('animate-spin text-brand-600', size === 'sm' ? 'h-3.5 w-3.5' : 'h-5 w-5')}
    />
    {label !== undefined && <span className="text-sm font-medium">{label}</span>}
  </span>
)

export const Skeleton: React.FC<{ className?: string }> = ({ className }) => (
  <div className={cn('animate-pulse rounded-control bg-slate-200/70', className)} />
)
