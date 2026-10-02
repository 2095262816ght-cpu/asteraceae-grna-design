import { useCallback, useEffect, useRef, useState } from 'react'

// URL 状态持久化：筛选/Tab 状态进 URL（F5/分享不丢），不引路由库。
// 默认值不写入 URL（保持分享链接干净）；tab/gene 用 pushState，其余 replaceState。
// 非法/缺失参数静默回落默认值。

export type ParamMode = 'push' | 'replace'

export function readParam(key: string): string | null {
  return new URLSearchParams(window.location.search).get(key)
}

export function writeParams(updates: Record<string, string | null>, mode: ParamMode) {
  const sp = new URLSearchParams(window.location.search)
  for (const [k, v] of Object.entries(updates)) {
    if (v === null) sp.delete(k)
    else sp.set(k, v)
  }
  const qs = sp.toString()
  const url = window.location.pathname + (qs ? `?${qs}` : '') + window.location.hash
  if (mode === 'push') window.history.pushState(null, '', url)
  else window.history.replaceState(null, '', url)
}

export function resetUrl() {
  window.history.replaceState(null, '', window.location.pathname)
}

interface UrlSyncedOptions<T> {
  key: string
  defaultValue: T
  /** URL 原始串 → 值；非法返回 null（回落默认） */
  parse: (raw: string) => T | null
  /** 值 → URL 串；返回 null 表示默认值，从 URL 移除 */
  serialize: (v: T) => string | null
  mode?: ParamMode
}

export function useUrlSynced<T>({
  key,
  defaultValue,
  parse,
  serialize,
  mode = 'replace',
}: UrlSyncedOptions<T>): [T, (v: T) => void] {
  const [value, setValue] = useState<T>(() => {
    const raw = readParam(key)
    const parsed = raw !== null ? parse(raw) : null
    return parsed !== null && parsed !== undefined ? parsed : defaultValue
  })

  const parseRef = useRef(parse)
  const serializeRef = useRef(serialize)
  const defaultRef = useRef(defaultValue)
  useEffect(() => {
    parseRef.current = parse
    serializeRef.current = serialize
    defaultRef.current = defaultValue
  })

  const set = useCallback(
    (v: T) => {
      setValue(v)
      writeParams({ [key]: serializeRef.current(v) }, mode)
    },
    [key, mode]
  )

  // 后退/前进按钮：从 URL 回填（非法参数回落默认）
  useEffect(() => {
    const onPop = () => {
      const raw = readParam(key)
      const parsed = raw !== null ? parseRef.current(raw) : null
      setValue(parsed !== null && parsed !== undefined ? parsed : defaultRef.current)
    }
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [key])

  return [value, set]
}
