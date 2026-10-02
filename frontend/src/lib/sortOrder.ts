// 各排序指标的推荐方向：切换排序指标时自动套用；GC 含量无推荐方向，保持手动切换
export const SORT_RECOMMENDED_ORDER: Record<string, 'asc' | 'desc' | null> = {
  efficiency_score: 'desc',
  priority_score: 'desc',
  hazard_score: 'asc',
  start: 'asc',
  offtarget_count_mis3: 'asc',
  gc_pct: null,
}
