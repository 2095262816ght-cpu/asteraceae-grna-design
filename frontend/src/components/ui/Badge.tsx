import React from 'react'
import { cn } from '../../lib/cn'

type BadgeTone = 'neutral' | 'success' | 'warning' | 'danger' | 'info' | 'brand'

const SOFT: Record<BadgeTone, string> = {
  neutral: 'bg-slate-100 text-slate-600 ring-slate-500/20',
  success: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20',
  warning: 'bg-amber-50 text-amber-700 ring-amber-600/20',
  danger: 'bg-rose-50 text-rose-700 ring-rose-600/20',
  info: 'bg-sky-50 text-sky-700 ring-sky-600/20',
  brand: 'bg-brand-50 text-brand-700 ring-brand-600/20',
}

const SOLID: Record<BadgeTone, string> = {
  neutral: 'bg-slate-600 text-white ring-slate-600',
  success: 'bg-emerald-600 text-white ring-emerald-600',
  warning: 'bg-amber-500 text-white ring-amber-500',
  danger: 'bg-rose-600 text-white ring-rose-600',
  info: 'bg-sky-600 text-white ring-sky-600',
  brand: 'bg-brand-600 text-white ring-brand-600',
}

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone
  solid?: boolean
}

// title 透传是硬要求：「诚实标注」的悬浮说明全靠原生 title 属性（测试用 getByTitle 断言）
export const Badge: React.FC<BadgeProps> = ({
  tone = 'neutral',
  solid,
  className,
  children,
  ...rest
}) => (
  <span
    className={cn(
      'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset',
      solid ? SOLID[tone] : SOFT[tone],
      className
    )}
    {...rest}
  >
    {children}
  </span>
)
