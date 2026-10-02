import { useEffect, useRef } from 'react'

// 多个浮层同时打开时的 Esc 归属：priority 大者先关（确认框 > 抽屉 > 弹窗），
// 同优先级后开者先关。文档级监听，行为与历史实现一致（有测试断言）。

interface OverlayEntry {
  priority: number
  close: () => void
}

const entries: OverlayEntry[] = []
let listening = false

function handleKeydown(e: KeyboardEvent) {
  if (e.key !== 'Escape' || entries.length === 0) return
  const top = entries.reduce((a, b) => (b.priority >= a.priority ? b : a))
  top.close()
}

export function useOverlayEsc(open: boolean, priority: number, close: () => void) {
  const closeRef = useRef(close)
  useEffect(() => {
    closeRef.current = close
  }, [close])

  useEffect(() => {
    if (!open) return
    const entry: OverlayEntry = { priority, close: () => closeRef.current() }
    entries.push(entry)
    if (!listening) {
      document.addEventListener('keydown', handleKeydown)
      listening = true
    }
    return () => {
      const idx = entries.indexOf(entry)
      if (idx >= 0) entries.splice(idx, 1)
      if (entries.length === 0 && listening) {
        document.removeEventListener('keydown', handleKeydown)
        listening = false
      }
    }
  }, [open, priority])
}
