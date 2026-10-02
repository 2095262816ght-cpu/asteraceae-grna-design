// 比对序列渲染：protospacer20 按 gRNA 方向 5'→3' 展示，错配碱基高亮（错配位置 1-based，PAM 远端为 1）
export function renderAlignedSeq(seq: string, mismatchPositions: number[] | null | undefined) {
  const posSet = new Set(mismatchPositions || [])
  return seq.split('').map((ch, i) => (
    <span
      key={i}
      className={posSet.has(i + 1) ? 'rounded-sm bg-rose-500 px-[1px] font-bold text-white' : 'text-ink-muted'}
    >
      {ch}
    </span>
  ))
}

// 风险等级着色：在靶=灰、致命=红、高危=橙、中=黄、低=绿
export function riskBadgeClass(level: string): string {
  switch (level) {
    case '在靶':
      return 'bg-slate-100 text-slate-600 ring-1 ring-inset ring-slate-400/30'
    case '致命':
      return 'bg-rose-100 text-rose-700 ring-1 ring-inset ring-rose-600/30'
    case '高危':
      return 'bg-orange-100 text-orange-700 ring-1 ring-inset ring-orange-600/30'
    case '中':
      return 'bg-yellow-100 text-yellow-800 ring-1 ring-inset ring-yellow-600/30'
    case '低':
      return 'bg-emerald-100 text-emerald-700 ring-1 ring-inset ring-emerald-600/30'
    default:
      return 'bg-slate-100 text-slate-600 ring-1 ring-inset ring-slate-400/30'
  }
}
