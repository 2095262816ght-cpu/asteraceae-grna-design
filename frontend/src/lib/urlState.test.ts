import { describe, it, expect, beforeEach } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import { useUrlSynced } from './urlState'

const tissueOptions = {
  key: 'tissue',
  defaultValue: 'Leaf' as const,
  parse: (raw: string) => (['Leaf', 'Root', 'Stem'].includes(raw) ? raw : null),
  serialize: (v: string) => (v === 'Leaf' ? null : v),
}

describe('useUrlSynced', () => {
  beforeEach(() => {
    window.history.replaceState(null, '', window.location.pathname)
  })

  it('keeps default values out of the URL and writes changes back', () => {
    const { result } = renderHook(() => useUrlSynced<string>(tissueOptions))
    expect(result.current[0]).toBe('Leaf')
    expect(window.location.search).toBe('')

    act(() => result.current[1]('Root'))
    expect(result.current[0]).toBe('Root')
    expect(window.location.search).toBe('?tissue=Root')

    // 回到默认值：参数从 URL 移除
    act(() => result.current[1]('Leaf'))
    expect(window.location.search).toBe('')
  })

  it('restores state from the URL on mount and survives refresh semantics', () => {
    window.history.replaceState(null, '', `${window.location.pathname}?tissue=Stem`)
    const { result } = renderHook(() => useUrlSynced<string>(tissueOptions))
    expect(result.current[0]).toBe('Stem')
  })

  it('falls back to the default for invalid URL values', () => {
    window.history.replaceState(null, '', `${window.location.pathname}?tissue=Bogus`)
    const { result } = renderHook(() => useUrlSynced<string>(tissueOptions))
    expect(result.current[0]).toBe('Leaf')
  })

  it('syncs back from the URL on popstate (back/forward)', () => {
    const { result } = renderHook(() => useUrlSynced<string>(tissueOptions))
    act(() => result.current[1]('Root'))
    window.history.replaceState(null, '', `${window.location.pathname}?tissue=Stem`)
    act(() => {
      window.dispatchEvent(new PopStateEvent('popstate'))
    })
    expect(result.current[0]).toBe('Stem')
  })
})
