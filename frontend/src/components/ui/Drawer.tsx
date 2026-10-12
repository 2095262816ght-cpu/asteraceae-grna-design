import React, { useRef } from 'react'
import { createPortal } from 'react-dom'
import { X } from 'lucide-react'
import { cn } from '../../lib/cn'
import { useOverlayEsc } from './useOverlayEsc'
import { useDialogA11y } from './useDialogA11y'

export interface DrawerProps {
  open: boolean
  onClose: () => void
  title?: React.ReactNode
  subtitle?: React.ReactNode
  actions?: React.ReactNode
  width?: string
  /** Esc 关闭优先级：大者先关（确认框 3 > 抽屉 2 > 弹窗 1） */
  closePriority?: number
  className?: string
  children: React.ReactNode
}

export const Drawer: React.FC<DrawerProps> = ({
  open,
  onClose,
  title,
  subtitle,
  actions,
  width = 'max-w-3xl',
  closePriority = 2,
  className,
  children,
}) => {
  const panelRef = useRef<HTMLDivElement>(null)
  useOverlayEsc(open, closePriority, onClose)
  useDialogA11y(open, panelRef)

  if (!open) return null

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex justify-end bg-slate-900/40 backdrop-blur-sm"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={typeof title === 'string' ? title : undefined}
        tabIndex={-1}
        className={cn(
          'glass-pop flex h-full w-full flex-col',
          'focus:outline-none',
          width,
          className
        )}
      >
        {(title !== undefined || subtitle !== undefined) && (
          <div className="flex items-start justify-between gap-4 border-b border-line px-5 py-3.5">
            <div>
              {title !== undefined && <h3 className="text-sm font-bold text-ink">{title}</h3>}
              {subtitle !== undefined && <p className="mt-0.5 text-xs text-ink-muted">{subtitle}</p>}
            </div>
            <div className="flex shrink-0 items-center gap-2">
              {actions}
              <button
                type="button"
                onClick={onClose}
                title="关闭"
                aria-label="关闭"
                className="rounded-control p-1 text-ink-muted transition-colors hover:bg-surface-sunken hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}
        <div className="flex-1 overflow-y-auto">{children}</div>
      </div>
    </div>,
    document.body
  )
}
