import React, { useRef } from 'react'
import { createPortal } from 'react-dom'
import { X } from 'lucide-react'
import { cn } from '../../lib/cn'
import { useOverlayEsc } from './useOverlayEsc'
import { useDialogA11y } from './useDialogA11y'

export interface DialogProps {
  open: boolean
  onClose: () => void
  title?: React.ReactNode
  subtitle?: React.ReactNode
  size?: 'sm' | 'md' | 'lg'
  /** Esc 关闭优先级：大者先关（确认框 3 > 抽屉 2 > 弹窗 1） */
  closePriority?: number
  /** 弹窗主体对齐：center 用于确认框，start 用于长内容（自带滚动） */
  align?: 'center' | 'start'
  initialFocusRef?: React.RefObject<HTMLElement | null>
  className?: string
  children: React.ReactNode
}

const SIZES = { sm: 'max-w-md', md: 'max-w-2xl', lg: 'max-w-4xl' }

export const Dialog: React.FC<DialogProps> = ({
  open,
  onClose,
  title,
  subtitle,
  size = 'md',
  closePriority = 1,
  align = 'start',
  initialFocusRef,
  className,
  children,
}) => {
  const panelRef = useRef<HTMLDivElement>(null)
  useOverlayEsc(open, closePriority, onClose)
  useDialogA11y(open, panelRef, initialFocusRef)

  if (!open) return null

  return createPortal(
    <div
      className={cn(
        'fixed inset-0 z-50 overflow-y-auto bg-slate-900/40 p-4 backdrop-blur-sm sm:p-8',
        align === 'center' ? 'flex items-center justify-center' : 'flex items-start justify-center'
      )}
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
          'glass-pop w-full rounded-card',
          'focus:outline-none',
          SIZES[size],
          className
        )}
      >
        {(title !== undefined || subtitle !== undefined) && (
          <div className="flex items-start justify-between gap-4 border-b border-line px-5 py-3.5">
            <div>
              {title !== undefined && <h3 className="text-sm font-bold text-ink">{title}</h3>}
              {subtitle !== undefined && <p className="mt-1 text-2xs text-ink-muted">{subtitle}</p>}
            </div>
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
        )}
        {children}
      </div>
    </div>,
    document.body
  )
}
