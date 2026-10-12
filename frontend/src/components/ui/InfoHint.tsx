import React from 'react'
import { Info } from 'lucide-react'
import { cn } from '../../lib/cn'

interface InfoHintProps {
  /** 原生 title 属性：诚实标注的悬浮说明，测试用 getByTitle 断言，逐字保留 */
  title: string
  className?: string
  children?: React.ReactNode
}

export const InfoHint: React.FC<InfoHintProps> = ({ title, className, children }) => (
  <span
    title={title}
    className={cn('inline-flex cursor-help items-center text-ink-faint', className)}
  >
    {children ?? <Info className="h-3.5 w-3.5" />}
  </span>
)
