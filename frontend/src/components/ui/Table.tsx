import React from 'react'
import { cn } from '../../lib/cn'

type Align = 'left' | 'center' | 'right'

const ALIGN: Record<Align, string> = {
  left: 'text-left',
  center: 'text-center',
  right: 'text-right',
}

interface StickySpec {
  left?: number
  right?: number
}

function cellStyle(sticky?: StickySpec, width?: number | string): React.CSSProperties | undefined {
  if (!sticky && width === undefined) return undefined
  return { left: sticky?.left, right: sticky?.right, width }
}

interface TableProps {
  density?: 'default' | 'compact'
  className?: string
  children: React.ReactNode
}

export const Table: React.FC<TableProps> = ({ density = 'default', className, children }) => (
  <table className={cn('w-full border-collapse text-sm', density === 'compact' && 'text-xs', className)}>
    {children}
  </table>
)

export const Thead: React.FC<{ className?: string; children: React.ReactNode }> = ({
  className,
  children,
}) => <thead className={cn('bg-white/30', className)}>{children}</thead>

export const Tbody: React.FC<{ children: React.ReactNode }> = ({ children }) => <tbody>{children}</tbody>

export const Tr: React.FC<{
  className?: string
  hover?: boolean
  onClick?: (e: React.MouseEvent<HTMLTableRowElement>) => void
  onKeyDown?: (e: React.KeyboardEvent<HTMLTableRowElement>) => void
  tabIndex?: number
  children: React.ReactNode
}> = ({ className, hover = true, onClick, onKeyDown, tabIndex, children }) => (
  <tr
    onClick={onClick}
    onKeyDown={onKeyDown}
    tabIndex={tabIndex}
    className={cn('border-b border-line', hover && 'hover:bg-white/30', className)}
  >
    {children}
  </tr>
)

interface CellProps extends Omit<React.TdHTMLAttributes<HTMLTableCellElement>, 'align'> {
  align?: Align
  numeric?: boolean
  sticky?: StickySpec
  width?: number | string
  colSpan?: number
  className?: string
  children: React.ReactNode
}

export const Th: React.FC<CellProps & { scope?: 'col' | 'row' }> = ({
  align = 'left',
  numeric,
  sticky,
  width,
  colSpan,
  scope = 'col',
  className,
  children,
  ...rest
}) => (
  <th
    scope={scope}
    colSpan={colSpan}
    style={cellStyle(sticky, width)}
    className={cn(
      'px-3 py-2.5 text-2xs font-semibold tracking-wide text-ink-muted',
      ALIGN[align],
      numeric && 'whitespace-nowrap tabular-nums',
      sticky && 'sticky z-10 bg-inherit backdrop-blur-md',
      className
    )}
    {...rest}
  >
    {children}
  </th>
)

export const Td: React.FC<CellProps> = ({
  align = 'left',
  numeric,
  sticky,
  width,
  colSpan,
  className,
  children,
  ...rest
}) => (
  <td
    colSpan={colSpan}
    style={cellStyle(sticky, width)}
    className={cn(
      'px-3 py-2.5 align-middle text-ink',
      ALIGN[align],
      numeric && 'whitespace-nowrap tabular-nums',
      sticky && 'sticky z-10 bg-inherit backdrop-blur-md',
      className
    )}
    {...rest}
  >
    {children}
  </td>
)
