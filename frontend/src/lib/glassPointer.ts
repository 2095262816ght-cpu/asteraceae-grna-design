/**
 * 指针追光：把指针位置写入 .card 的 --mx / --my，
 * 供卡片背景层的径向高光实时跟随（rAF 节流）。
 * 注意：.glass-panel（侧栏/图谱卡）刻意不参与——悬停时刻意零变化。
 */
let frame = 0
let pending: PointerEvent | null = null

function flush() {
  frame = 0
  const e = pending
  pending = null
  if (!e || !(e.target instanceof Element)) return
  const surface = e.target.closest('.card')
  if (!(surface instanceof HTMLElement)) return
  const rect = surface.getBoundingClientRect()
  surface.style.setProperty('--mx', `${(e.clientX - rect.left).toFixed(1)}px`)
  surface.style.setProperty('--my', `${(e.clientY - rect.top).toFixed(1)}px`)
}

export function initGlassPointer(): void {
  window.addEventListener(
    'pointermove',
    (e) => {
      pending = e
      if (!frame) frame = requestAnimationFrame(flush)
    },
    { passive: true },
  )
}
