// 候选查询深度模块：filter state → CandidatesResponse。
// 隐藏三件事，调用方不得绕过本模块自行编码：
//   1. URL 参数编码（含「全部/无」哨兵值的取舍）；
//   2. 区域优先级规则：region_type 优先于 exon_only（与 backend/app/api/v1/endpoints/
//      candidates.py 的解释端同一契约，本文件是编码侧唯一定义处）；
//   3. 导出前的逐条脱靶预计算循环（后端工作流编排，UI 只观察进度）。
// 排序帮助条目取自 /api/v1/meta/sort-help（公式文案单点定义在 cs_pipeline.core.ranking_semantics）。

export type TargetTissue = 'Leaf' | 'Root' | 'Stem' | 'Flower' | 'Seed'

export interface CandidateItem {
  id: number
  guide_id: string
  gene_id: string
  chrom: string
  start: number
  end: number
  strand: string
  seq30: string
  seq20: string
  pam: string
  region_type: string
  is_centromere: boolean
  is_exon: boolean
  gc_pct: number
  tm_c: number
  offtarget_count_mis3?: number | null
  deepspcas9_score?: number
  crispron_score?: number
  efficiency_score?: number
  // 表达适配度（教师反馈 #2）：poly-T 硬过滤 + 5'G 起始 + spacer 自折叠 MFE
  poly_t?: boolean
  five_prime_g?: boolean
  mfe_kcal?: number | null
  mfe_risk?: boolean | null
  expression_fitness_note?: string | null
  priority_score?: number
  hazard_score?: number
  expression_status?: string
  expression_status_display?: string
  expression_evidence_note?: string
  n_intra_panel_sites?: number | null
  target_tissue?: string
}

export interface CandidatesResponse {
  items: CandidateItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
  gene_summary?: {
    gene_id: string
    chrom: string
    start: number
    end: number
    strand: string
    total_candidates: number
    filtered_candidates: number
    poly_t_filtered_count?: number
  }
}

export interface CandidateFilters {
  geneId: string
  targetTissue?: TargetTissue
  minScore?: number
  excludeCentromere?: boolean
  exonOnly?: boolean
  /** 'all' 不下发（不过滤）；'none' 显式查无区域注释；'exon'/'promoter' 精确过滤 */
  regionType?: string
  page?: number
  pageSize?: number
  sortBy?: string
  sortOrder?: string
}

export interface SortHelpItem {
  key: string
  title: string
  direction: string
  lines: string[]
}

export interface OfftargetComputeResult {
  computed: number
  items: Array<{ id: number; offtarget_count_mis3: number | null; n_intra_panel_sites: number | null }>
}

/** 请求编码单点定义：region_type 优先于 exon_only；'all' 哨兵不下发。 */
export function buildCandidatesParams(f: CandidateFilters): URLSearchParams {
  const sp = new URLSearchParams()
  sp.set('gene_id', f.geneId)
  if (f.targetTissue) sp.set('target_tissue', f.targetTissue)
  if (f.minScore !== undefined && f.minScore > 0) sp.set('min_score', String(f.minScore))
  if (f.excludeCentromere) sp.set('exclude_centromere', 'true')
  if (f.regionType && f.regionType !== 'all') {
    sp.set('region_type', f.regionType)
  } else if (f.exonOnly) {
    sp.set('exon_only', 'true')
  }
  if (f.page) sp.set('page', String(f.page))
  if (f.pageSize) sp.set('page_size', String(f.pageSize))
  if (f.sortBy) sp.set('sort_by', f.sortBy)
  if (f.sortOrder) sp.set('sort_order', f.sortOrder)
  return sp
}

export async function fetchCandidates(
  filters: CandidateFilters,
  signal?: AbortSignal,
): Promise<CandidatesResponse> {
  const sp = buildCandidatesParams(filters)
  const res = await fetch(`/api/v1/candidates?${sp.toString()}`, signal ? { signal } : undefined)
  if (!res.ok) throw new Error('获取候选靶点失败')
  return res.json()
}

/** 按需计算脱靶（服务端全基因组扫描并回填，约 1 分钟/条）。 */
export async function computeOfftarget(candidateIds: number[]): Promise<OfftargetComputeResult> {
  const res = await fetch('/api/v1/offtarget/compute', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ candidate_ids: candidateIds }),
  })
  if (!res.ok) {
    let detail = ''
    try {
      const data = await res.json()
      detail = data?.detail || ''
    } catch {
      // 非 JSON 错误体，保留通用文案
    }
    throw new Error(detail || '计算脱靶失败，请稍后重试')
  }
  return res.json()
}

/**
 * 导出前逐条预计算脱靶（已计算的秒回）：后端工作流编排隐藏于此，
 * onProgress(done, total) 供 UI 呈现进度，不参与编排决策。
 */
export async function precomputeOfftargetForExport(
  ids: number[],
  onProgress?: (done: number, total: number) => void,
): Promise<void> {
  for (let i = 0; i < ids.length; i++) {
    onProgress?.(i, ids.length)
    await computeOfftarget([ids[i]])
  }
}

/** 排序帮助条目（公式文案由后端自 ranking_semantics 单点渲染）。 */
export async function fetchSortHelp(tissueName: string): Promise<SortHelpItem[]> {
  const sp = new URLSearchParams()
  sp.set('tissue_name', tissueName)
  const res = await fetch(`/api/v1/meta/sort-help?${sp.toString()}`)
  if (!res.ok) throw new Error('获取排序帮助失败')
  const data = await res.json()
  return data.items
}
