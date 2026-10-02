import React from 'react'
import { cn } from '../../lib/cn'

interface EmptyStateProps {
  icon?: React.ReactNode
  title?: React.ReactNode
  description?: React.ReactNode
  action?: React.ReactNode
  className?: string
  children?: React.ReactNode
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  action,
  className,
  children,
}) => (
  <div className={cn('flex flex-col items-center justify-center gap-2 py-10 text-center', className)}>
    {icon !== undefined && <div className="text-ink-faint">{icon}</div>}
    {title !== undefined && <div className="text-sm font-medium text-ink">{title}</div>}
    {description !== undefined && <div className="max-w-md text-xs text-ink-muted">{description}</div>}
    {children}
    {action !== undefined && <div className="mt-2">{action}</div>}
  </div>
)
