import React, { useRef, useState } from 'react'
import { cn } from '../../lib/cn'

export interface TabItem {
  id: string
  label: React.ReactNode
  icon?: React.ReactNode
}

interface TabsProps {
  items: TabItem[]
  value: string
  onChange: (id: string) => void
  variant?: 'pill' | 'underline' | 'nav'
  orientation?: 'horizontal' | 'vertical'
  className?: string
  'aria-label'?: string
}

// Tabs 只渲染 tablist；面板由 TabPanel 控制：首次激活挂载、之后以 hidden 保持挂载，
// 避免切页丢失已打分结果等本地状态（未访问面板不挂载，不拖累首屏）。
// id 契约：tab 按钮 id=`tab-{id}`，面板 id=`panel-{id}`（TabPanel 同源生成）。
export const Tabs: React.FC<TabsProps> = ({
  items,
  value,
  onChange,
  variant = 'pill',
  orientation = 'horizontal',
  className,
  ...rest
}) => {
  const listRef = useRef<HTMLDivElement>(null)

  const onKeyDown = (e: React.KeyboardEvent) => {
    const idx = items.findIndex((it) => it.id === value)
    const forward = orientation === 'vertical' ? 'ArrowDown' : 'ArrowRight'
    const backward = orientation === 'vertical' ? 'ArrowUp' : 'ArrowLeft'
    let next = -1
    if (e.key === forward) next = (idx + 1) % items.length
    else if (e.key === backward) next = (idx - 1 + items.length) % items.length
    else if (e.key === 'Home') next = 0
    else if (e.key === 'End') next = items.length - 1
    if (next < 0) return
    e.preventDefault()
    onChange(items[next].id)
    listRef.current?.querySelector<HTMLButtonElement>(`#tab-${items[next].id}`)?.focus()
  }

  return (
    <div
      ref={listRef}
      role="tablist"
      aria-orientation={orientation}
      onKeyDown={onKeyDown}
      className={cn(
        variant === 'pill' && 'flex space-x-1 rounded-xl bg-slate-100 p-1',
        variant === 'underline' && 'flex border-b border-line',
        variant === 'nav' && 'flex flex-col gap-1',
        className
      )}
      {...rest}
    >
      {items.map((it) => {
        const selected = it.id === value
        return (
          <button
            key={it.id}
            id={`tab-${it.id}`}
            role="tab"
            type="button"
            aria-selected={selected}
            aria-controls={`panel-${it.id}`}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(it.id)}
            className={
              variant === 'pill'
                ? cn(
                    'flex items-center space-x-2 rounded-lg px-3 py-1.5 text-xs font-medium transition-all',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40',
                    selected ? 'bg-white text-brand-700 shadow-sm' : 'text-slate-600 hover:text-slate-900'
                  )
                : variant === 'underline'
                ? cn(
                    'inline-flex items-center gap-2 border-b-2 px-4 py-2.5 text-xs font-semibold transition-all',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40',
                    selected
                      ? 'border-brand-600 text-brand-700'
                      : 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-800'
                  )
                : cn(
                    'flex w-full items-center gap-3 rounded-control px-3 py-2 text-left text-sm font-medium transition-colors',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400/50',
                    selected
                      ? 'bg-white/75 text-brand-700 shadow-sm'
                      : 'text-ink-muted hover:bg-white/50 hover:text-ink'
                  )
            }
          >
            {it.icon}
            <span>{it.label}</span>
          </button>
        )
      })}
    </div>
  )
}

interface TabPanelProps {
  tabId: string
  activeTabId: string
  className?: string
  children: React.ReactNode
}

// 面板首次激活才挂载、之后仅切 hidden 保持挂载：未访问页签不付出首屏渲染/下载成本，
// 访问过的页签本地状态（如已打分结果）不因切页丢失。与 Tabs 的 id 契约配对（aria-labelledby/controls）
export const TabPanel: React.FC<TabPanelProps> = ({ tabId, activeTabId, className, children }) => {
  // 渲染期派生"是否已访问"：访问过的面板保持挂载，未访问的不挂载
  const [mounted, setMounted] = useState(tabId === activeTabId)
  if (!mounted && tabId === activeTabId) setMounted(true)
  return (
    <div
      id={`panel-${tabId}`}
      role="tabpanel"
      aria-labelledby={`tab-${tabId}`}
      hidden={tabId !== activeTabId}
      className={cn(tabId !== activeTabId && 'hidden', className)}
    >
      {mounted ? children : null}
    </div>
  )
}
