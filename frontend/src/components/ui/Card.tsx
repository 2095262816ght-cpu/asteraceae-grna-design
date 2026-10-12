import React from 'react'
import { cn } from '../../lib/cn'

interface CardProps {
  padding?: 'md' | 'sm' | 'none'
  interactive?: boolean
  className?: string
  children: React.ReactNode
}

export const Card: React.FC<CardProps> = ({ padding = 'md', interactive, className, children }) => (
  <div
    className={cn(
      'card',
      padding === 'md' && 'p-6',
      padding === 'sm' && 'p-4',
      interactive && 'transition-colors hover:bg-surface-sunken/60',
      className
    )}
  >
    {children}
  </div>
)

interface CardHeaderProps {
  title?: React.ReactNode
  icon?: React.ReactNode
  actions?: React.ReactNode
  description?: React.ReactNode
  className?: string
  children?: React.ReactNode
}

export const CardHeader: React.FC<CardHeaderProps> = ({
  title,
  icon,
  actions,
  description,
  className,
  children,
}) => (
  <div className={cn('flex items-start justify-between gap-4', className)}>
    <div className="flex items-center gap-3">
      {icon}
      <div>
        {title !== undefined && <h2 className="text-sm font-bold text-ink">{title}</h2>}
        {description !== undefined && <p className="mt-0.5 text-xs text-ink-muted">{description}</p>}
        {children}
      </div>
    </div>
    {actions !== undefined && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
  </div>
)

export const CardBody: React.FC<{ className?: string; children: React.ReactNode }> = ({
  className,
  children,
}) => <div className={cn('mt-4', className)}>{children}</div>
