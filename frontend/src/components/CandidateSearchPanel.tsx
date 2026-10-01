import React, { useState, useMemo, useRef, useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Activity,
  AlertTriangle,
  ArrowUpDown,
  BookOpen,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Dna,
  Download,
  FileSpreadsheet,
  Info,
  Search,
  X,
} from 'lucide-react'
import { GenomicTargetMap } from './GenomicTargetMap'
import {
  computeOfftarget,
  fetchCandidates,
  fetchSortHelp,
  precomputeOfftargetForExport,
  type CandidateItem,
  type CandidatesResponse,
  type SortHelpItem,
  type TargetTissue,
} from '../lib/candidateQuery'

export const TISSUE_NAMES: Record<TargetTissue, string> = {
  Leaf: '叶',
  Root: '根',
  Stem: '茎',
  Flower: '花',
  Seed: '种子',
}

export const TISSUE_ORDER: TargetTissue[] = ['Leaf', 'Root', 'Stem', 'Flower', 'Seed']

// 各排序指标的推荐方向：切换排序指标时自动套用；GC 含量无推荐方向，保持手动切换
const SORT_RECOMMENDED_ORDER: Record<string, 'asc' | 'desc' | null> = {
  efficiency_score: 'desc',
  priority_score: 'desc',
  hazard_score: 'asc',
  start: 'asc',
  offtarget_count_mis3: 'asc',
  gc_pct: null,
}

// 排序说明弹窗文案取自后端 /api/v1/meta/sort-help（公式文案单点定义在
// cs_pipeline.core.ranking_semantics，前端不复述公式）

export interface GeneInfo {
  gene_id: string
  chrom: string
  start: number
  end: number
  strand: string
  nlr_type?: string
  candidate_count: number
}

export interface GeneExpressionData {
  gene_id: string
  lsa_id?: string
  tier?: number
  lsa_vote_frac?: number
  lsa_resolved_frac?: number
  is_mappable: boolean
  unmappable_reason?: string
  tpm_root?: number
  tpm_stem?: number
  tpm_leaf?: number
  tpm_flower?: number
  tpm_seed?: number
  top_tissue?: string
  top_tpm?: number
  tau?: number
  n_cluster: number
  lsa_cluster?: string
  scaffold_evidence?: string
  tpm_dict: Record<string, number>
}

// ============ 脱靶位点明细 API（教师反馈 #1） ============
export interface OfftargetSite {
  chrom: string
  start: number
  end: number
  strand: string
  protospacer20: string
  pam: string
  mismatch_count: number
  mismatch_positions: number[]
  cfd_score: number
  mit_hit_score: number
  region_type?: string | null
  region_label?: string | null
  gene_id?: string | null
  risk_level: string
  risk_note: string
  is_ontarget: boolean
}

export interface OfftargetSitesResponse {
  seq20: string
  bundle_id: string
  bundle_name: string
  genome_note: string
  profile: { exact: number; mis1: number; mis2: number; mis3: number }
  sites: OfftargetSite[]
  sites_truncated: boolean
  specificity: {
    n_offtarget_sites_scored: number
    mit_hit_sum: number
    mit_specificity: number
    cfd_hit_sum: number
    cfd_specificity: number
    on_target_excluded: boolean
  }
  method_note: string
}

// ============ 方法与版本说明 API（教师反馈 #4/#5） ============
export interface MethodsInfo {
  efficiency_model: {
    name: string
    kind: string
    components: string[]
    validation: string
    model_card: string
    lineage_note: string
  }
  offtarget: {
    search: string
    params: { pam: string; gRNA_length: string; max_mismatches: number; strands: string }
    site_scores: string[]
    guide_specificity: string
    risk_note: string
  }
  expression_fitness: { poly_t: string; five_prime_g: string; mfe: string; gc: string }
  gene_structure: { source: string; protein_domains: string }
  reference_genomes: Array<{
    id: string
    display_name: string
    fasta_available: boolean
    gff_available: boolean
  }>
  disclaimer: string
}

async function fetchGenes(): Promise<GeneInfo[]> {
  const res = await fetch('/api/v1/genes')
  if (!res.ok) throw new Error('获取基因列表失败')
  return res.json()
}

async function fetchGeneExpression(geneId: string): Promise<GeneExpressionData> {
  const res = await fetch(`/api/v1/genes/${geneId}/expression`)
  if (!res.ok) throw new Error('获取基因表达图谱失败')
  return res.json()
}

// 脱靶位点明细：点击"脱靶数"数字时按需请求（20nt 全基因组扫描，秒级~分钟级）
async function fetchOfftargetSites(params: {
  seq20: string
  bundle_id?: string
  max_sites?: number
  ontarget_start?: number
  ontarget_end?: number
}): Promise<OfftargetSitesResponse> {
  const sp = new URLSearchParams()
  sp.set('seq20', params.seq20)
  if (params.bundle_id) sp.set('bundle_id', params.bundle_id)
  if (params.max_sites) sp.set('max_sites', String(params.max_sites))
  if (params.ontarget_start !== undefined) sp.set('ontarget_start', String(params.ontarget_start))
  if (params.ontarget_end !== undefined) sp.set('ontarget_end', String(params.ontarget_end))
  const res = await fetch(`/api/v1/offtarget/sites?${sp.toString()}`)
  if (!res.ok) throw new Error('获取脱靶位点明细失败')
  return res.json()
}

// 方法与版本说明：点击"方法与版本"按钮时按需请求
async function fetchMethodsInfo(): Promise<MethodsInfo> {
  const res = await fetch('/api/v1/meta/methods')
  if (!res.ok) throw new Error('获取方法与版本信息失败')
  return res.json()
}

// 比对序列渲染：protospacer20 按 gRNA 方向 5'→3' 展示，错配碱基高亮（错配位置 1-based，PAM 远端为 1）
function renderAlignedSeq(seq: string, mismatchPositions: number[] | null | undefined) {
  const posSet = new Set(mismatchPositions || [])
  return seq.split('').map((ch, i) => (
    <span
      key={i}
      className={posSet.has(i + 1) ? 'rounded-sm bg-rose-500 px-[1px] font-bold text-white' : 'text-slate-700'}
    >
      {ch}
    </span>
  ))
}

// 风险等级着色：在靶=灰、致命=红、高危=橙、中=黄、低=绿
function riskBadgeClass(level: string): string {
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

export const CandidateSearchPanel: React.FC = () => {
  const [selectedGeneId, setSelectedGeneId] = useState<string>('')
  const [selectedGuideId, setSelectedGuideId] = useState<string | null>(null)
  const [targetTissue, setTargetTissue] = useState<TargetTissue>('Leaf')
  const [minScore, setMinScore] = useState<number>(0)

  const [excludeCentromere, setExcludeCentromere] = useState<boolean>(false)
  const [includeExon, setIncludeExon] = useState<boolean>(true)
  const [includePromoter, setIncludePromoter] = useState<boolean>(true)
  const [sortBy, setSortBy] = useState<string>('efficiency_score')
  const [sortOrder, setSortOrder] = useState<string>('desc')
  const [showSortHelp, setShowSortHelp] = useState<boolean>(false)
  // 排序帮助条目取自后端（公式文案单点定义在 cs_pipeline.core.ranking_semantics）
  const [sortHelpItems, setSortHelpItems] = useState<SortHelpItem[]>([])
  const [page, setPage] = useState<number>(1)
  const pageSize = 20

  // 计算当前区域类型过滤参数
  const currentRegionType = useMemo<'all' | 'exon' | 'promoter' | 'none'>(() => {
    if (includeExon && !includePromoter) return 'exon'
    if (!includeExon && includePromoter) return 'promoter'
    if (!includeExon && !includePromoter) return 'none'
    return 'all'
  }, [includeExon, includePromoter])

  const [selectedCandidateIds, setSelectedCandidateIds] = useState<Set<number>>(new Set())
  const [batchName, setBatchName] = useState<string>('')

  useEffect(() => {
    let alive = true
    fetchSortHelp(TISSUE_NAMES[targetTissue])
      .then((items) => {
        if (alive) setSortHelpItems(items)
      })
      .catch(() => {
        if (alive) setSortHelpItems([])
      })
    return () => {
      alive = false
    }
  }, [targetTissue])
  const [isExporting, setIsExporting] = useState<boolean>(false)
  const queryClient = useQueryClient()

  // "未计算"格：确认框（要计算脱靶吗）+ 计算中行 + 导出进度（脱靶扫描 n/N → 生成文件）
  const [computeConfirm, setComputeConfirm] = useState<CandidateItem | null>(null)
  const [computingIds, setComputingIds] = useState<Set<number>>(new Set())
  const [exportProgress, setExportProgress] = useState<{
    done: number
    total: number
    phase: 'scan' | 'generate'
  } | null>(null)

  // 脱靶位点明细抽屉状态（点击"脱靶数"数字时按需加载，不预先请求）
  const [offtargetCand, setOfftargetCand] = useState<CandidateItem | null>(null)
  const [offtargetData, setOfftargetData] = useState<OfftargetSitesResponse | null>(null)
  const [offtargetLoading, setOfftargetLoading] = useState<boolean>(false)
  const [offtargetError, setOfftargetError] = useState<string | null>(null)

  // 方法与版本弹窗状态（点击按钮时按需加载，不预先请求）
  const [showMethods, setShowMethods] = useState<boolean>(false)
  const [methodsData, setMethodsData] = useState<MethodsInfo | null>(null)
  const [methodsLoading, setMethodsLoading] = useState<boolean>(false)
  const [methodsError, setMethodsError] = useState<string | null>(null)

  // 基因即输即搜 Combobox 状态
  const [isGeneDropdownOpen, setIsGeneDropdownOpen] = useState<boolean>(false)
  const [geneSearchInput, setGeneSearchInput] = useState<string>('')
  const geneComboboxRef = useRef<HTMLDivElement>(null)

  // 1. 获取基因列表
  const { data: genes, isLoading: genesLoading } = useQuery<GeneInfo[]>({
    queryKey: ['genes'],
    queryFn: fetchGenes,
  })

  // 如果没有选定基因，默认选择第一个
  const activeGeneId = selectedGeneId || (genes && genes.length > 0 ? genes[0].gene_id : '')

  // 1.5 获取当前基因的多组织表达图谱与表型适宜性诊断
  const { data: expressionData, isLoading: exprLoading } = useQuery<GeneExpressionData>({
    queryKey: ['gene_expression', activeGeneId],
    queryFn: () => fetchGeneExpression(activeGeneId),
    enabled: !!activeGeneId,
  })

  // 点击外部区域自动收起浮层
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (geneComboboxRef.current && !geneComboboxRef.current.contains(event.target as Node)) {
        setIsGeneDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // 排序说明 / 方法与版本弹窗与脱靶明细抽屉 / 脱靶计算确认框：Esc 关闭（确认框与抽屉优先）
  useEffect(() => {
    if (!showSortHelp && !showMethods && !offtargetCand && !computeConfirm) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return
      if (computeConfirm) {
        setComputeConfirm(null)
      } else if (offtargetCand) {
        setOfftargetCand(null)
      } else if (showMethods) {
        setShowMethods(false)
      } else {
        setShowSortHelp(false)
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [showSortHelp, showMethods, offtargetCand, computeConfirm])

  // 模糊匹配过滤
  const filteredGenes = useMemo(() => {
    if (!genes) return []
    if (!geneSearchInput.trim()) return genes
    const q = geneSearchInput.toLowerCase().trim()
    return genes.filter(
      (g) =>
        g.gene_id.toLowerCase().includes(q) ||
        g.chrom.toLowerCase().includes(q) ||
        (g.nlr_type && g.nlr_type.toLowerCase().includes(q))
    )
  }, [genes, geneSearchInput])

  const handleSelectGene = (geneId: string) => {
    setSelectedGeneId(geneId)
    setGeneSearchInput('')
    setIsGeneDropdownOpen(false)
    setPage(1)
    setSelectedGuideId(null)
  }

  const handleExport = async (format: 'csv' | 'xlsx') => {
    if (selectedCandidateIds.size === 0 || isExporting) return
    setIsExporting(true)
    const ids = Array.from(selectedCandidateIds)
    try {
      const finalName = batchName.trim() || `${activeGeneId || 'gRNA'}_优选方案`
      // 阶段1：逐条按需计算脱靶（编排隐藏在候选查询模块），进度条随 n/N 前进
      await precomputeOfftargetForExport(ids, (done, total) =>
        setExportProgress({ done, total, phase: 'scan' }),
      )
      // 阶段2：创建批次并生成文件下载（此时脱靶已回填，下载不再触发长扫描）
      setExportProgress({ done: ids.length, total: ids.length, phase: 'generate' })
      const res = await fetch('/api/v1/exports', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: finalName,
          format,
          candidate_ids: ids,
          gene_id: activeGeneId || undefined,
        }),
      })
      if (!res.ok) throw new Error('创建导出批次失败')
      const data = await res.json()
      const dl = await fetch(`/api/v1/exports/${data.id}/download`)
      if (!dl.ok) throw new Error('导出文件生成失败')
      const blob = await dl.blob()
      const cd = dl.headers.get('Content-Disposition') || ''
      const m = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(cd)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = m ? decodeURIComponent(m[1]) : `${finalName}.${format === 'xlsx' ? 'xlsx' : 'csv'}`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
      // 刷新表格：新算出的脱靶数/优先指数就地显示，不再挂"未计算"
      await queryClient.invalidateQueries({ queryKey: ['candidates'] })
    } catch (err: any) {
      alert(err.message || '导出错误')
    } finally {
      setIsExporting(false)
      setExportProgress(null)
    }
  }

  // "未计算"格确认后按需计算脱靶：格内转圈 → 刷新数字 → 自动打开位点明细抽屉
  const confirmComputeOfftarget = async () => {
    const cand = computeConfirm
    if (!cand) return
    setComputeConfirm(null)
    setComputingIds((prev) => new Set(prev).add(cand.id))
    try {
      await computeOfftarget([cand.id])
      await queryClient.invalidateQueries({ queryKey: ['candidates'] })
      openOfftargetDrawer(cand)
    } catch (err: any) {
      alert(err?.message || '计算脱靶失败，请稍后重试')
    } finally {
      setComputingIds((prev) => {
        const next = new Set(prev)
        next.delete(cand.id)
        return next
      })
    }
  }

  // 打开脱靶明细抽屉并按需拉取位点明细（seq20 无效 / 请求失败时优雅降级）
  const openOfftargetDrawer = async (cand: CandidateItem) => {
    setOfftargetCand(cand)
    setOfftargetData(null)
    setOfftargetError(null)
    const seq = (cand.seq20 || '').trim()
    if (seq.length !== 20) {
      setOfftargetLoading(false)
      setOfftargetError('该候选缺少有效的 20nt guide 序列，无法查询脱靶位点明细')
      return
    }
    setOfftargetLoading(true)
    try {
      const data = await fetchOfftargetSites({
        seq20: seq,
        bundle_id: 'lettuce',
        max_sites: 200,
        ontarget_start: cand.start,
        ontarget_end: cand.end,
      })
      setOfftargetData(data)
    } catch (err: any) {
      setOfftargetError(err?.message || '获取脱靶位点明细失败，请稍后重试')
    } finally {
      setOfftargetLoading(false)
    }
  }

  // 打开方法与版本弹窗（已加载则复用缓存，不重复请求）
  const openMethods = async () => {
    setShowMethods(true)
    if (methodsData || methodsLoading) return
    setMethodsLoading(true)
    setMethodsError(null)
    try {
      setMethodsData(await fetchMethodsInfo())
    } catch (err: any) {
      setMethodsError(err?.message || '获取方法与版本信息失败，请稍后重试')
    } finally {
      setMethodsLoading(false)
    }
  }

  // 2. 获取候选靶点
  const {
    data: candidatesData,
    isLoading: candidatesLoading,
    isFetching,
  } = useQuery<CandidatesResponse>({
    queryKey: [
      'candidates',
      activeGeneId,
      targetTissue,
      minScore,
      excludeCentromere,
      currentRegionType,
      page,
      sortBy,
      sortOrder,
    ],
    queryFn: () =>
      fetchCandidates({
        geneId: activeGeneId,
        targetTissue,
        minScore,
        excludeCentromere,
        regionType: currentRegionType,
        page,
        pageSize,
        sortBy,
        sortOrder,
      }),
    enabled: !!activeGeneId,
  })

  const currentGene = genes?.find((g) => g.gene_id === activeGeneId)
  const summary = candidatesData?.gene_summary

  const currentItems = candidatesData?.items || []
  const pendingScanCount = currentItems.filter(
    (c) => selectedCandidateIds.has(c.id) && (c.offtarget_count_mis3 === null || c.offtarget_count_mis3 === undefined)
  ).length
  const isAllCurrentSelected =
    currentItems.length > 0 && currentItems.every((c) => selectedCandidateIds.has(c.id))

  const toggleSelectAllCurrent = () => {
    const next = new Set(selectedCandidateIds)
    if (isAllCurrentSelected) {
      currentItems.forEach((c) => next.delete(c.id))
    } else {
      currentItems.forEach((c) => next.add(c.id))
    }
    setSelectedCandidateIds(next)
  }

  const toggleSelectOne = (id: number) => {
    const next = new Set(selectedCandidateIds)
    if (next.has(id)) {
      next.delete(id)
    } else {
      next.add(id)
    }
    setSelectedCandidateIds(next)
  }

  return (
    <div className="space-y-6">
      {/* 顶部控制栏：基因选择与多维过滤面板 */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between border-b border-slate-100 pb-5">
          {/* 基因选择器 (即输即搜 Combobox) */}
          <div className="flex flex-1 items-start sm:items-center space-x-3.5 relative" ref={geneComboboxRef}>
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600 shadow-sm border border-emerald-100/60 mt-0.5 sm:mt-0">
              <Dna className="h-5 w-5" />
            </div>
            <div className="relative flex-1 max-w-md">
              <div className="flex items-center justify-between mb-1">
                <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  选择靶基因 (即输即搜 · 莴苣全基因组 + 49 NLR)
                </label>
                {activeGeneId && (
                  <span className="text-[11px] font-mono text-emerald-600 font-semibold bg-emerald-50 px-1.5 py-0.5 rounded">
                    当前: {activeGeneId}
                  </span>
                )}
              </div>

              {genesLoading ? (
                <div className="h-10 w-full animate-pulse rounded-xl bg-slate-100"></div>
              ) : (
                <div className="relative">
                  {/* 输入搜索框 */}
                  <div className="relative flex items-center">
                    <Search className="absolute left-3 h-4 w-4 text-slate-400 pointer-events-none" />
                    <input
                      type="text"
                      role="combobox"
                      aria-expanded={isGeneDropdownOpen}
                      aria-controls="gene-options-list"
                      aria-label="选择靶基因"
                      value={isGeneDropdownOpen ? geneSearchInput : (geneSearchInput || activeGeneId)}
                      placeholder="输入基因号或关键字 (如 019420, Chr06, CC)..."
                      onFocus={() => {
                        setIsGeneDropdownOpen(true)
                      }}
                      onChange={(e) => {
                        setGeneSearchInput(e.target.value)
                        setIsGeneDropdownOpen(true)
                      }}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault()
                          if (filteredGenes.length > 0) {
                            handleSelectGene(filteredGenes[0].gene_id)
                          }
                        } else if (e.key === 'Escape') {
                          setIsGeneDropdownOpen(false)
                        }
                      }}
                      className="block w-full rounded-xl border border-slate-200 bg-white pl-9 pr-16 py-2 text-sm font-medium text-slate-800 shadow-sm transition-all focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                    />
                    <div className="absolute right-2 flex items-center space-x-1">
                      {geneSearchInput && (
                        <button
                          type="button"
                          onClick={() => setGeneSearchInput('')}
                          className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                          title="清空输入"
                        >
                          <X className="h-3.5 w-3.5" />
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => setIsGeneDropdownOpen((prev) => !prev)}
                        className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                        title={isGeneDropdownOpen ? "收起下拉" : "展开下拉"}
                      >
                        <ChevronDown className={`h-4 w-4 transition-transform duration-200 ${isGeneDropdownOpen ? 'rotate-180' : ''}`} />
                      </button>
                    </div>
                  </div>

                  {/* 悬浮下拉选项列表 */}
                  {isGeneDropdownOpen && (
                    <div
                      id="gene-options-list"
                      className="absolute left-0 right-0 top-full z-40 mt-1.5 max-h-72 overflow-y-auto rounded-xl border border-slate-200 bg-white p-1.5 shadow-xl transition-all"
                    >
                      <div className="px-2.5 py-1.5 text-[11px] font-medium text-slate-400 border-b border-slate-100 flex justify-between items-center">
                        <span>{geneSearchInput ? `匹配结果 (${filteredGenes.length})` : `莴苣全基因组 + 49 NLR`}</span>
                        <span className="text-[10px] text-slate-400">按回车快速选中首项</span>
                      </div>

                      {filteredGenes.length === 0 ? (
                        <div className="py-6 text-center text-xs text-slate-400">
                          未找到匹配的基因 (关键字: "{geneSearchInput}")
                        </div>
                      ) : (
                        <div className="divide-y divide-slate-50">
                          {filteredGenes.slice(0, 200).map((g) => {
                            const isSelected = g.gene_id === activeGeneId
                            return (
                              <button
                                key={g.gene_id}
                                type="button"
                                onClick={() => handleSelectGene(g.gene_id)}
                                className={`w-full flex items-center justify-between rounded-lg px-3 py-2 text-left text-xs transition-colors ${
                                  isSelected
                                    ? 'bg-emerald-50 text-emerald-900 font-semibold'
                                    : 'text-slate-700 hover:bg-slate-50'
                                }`}
                              >
                                <div className="flex flex-col">
                                  <span className="font-mono text-sm tracking-tight flex items-center gap-1.5">
                                    {g.gene_id}
                                    {isSelected && <span className="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>}
                                  </span>
                                  <span className="text-[11px] text-slate-400 font-normal">
                                    {g.chrom} · {g.gene_id.startsWith('Lsa') ? 'NLR 专项注释' : '全基因组注释'}{g.nlr_type ? ` · ${g.nlr_type}` : ''} · {g.candidate_count} 候选位点
                                  </span>
                                </div>
                                {isSelected && (
                                  <Check className="h-4 w-4 text-emerald-600 shrink-0 ml-2" />
                                )}
                              </button>
                            )
                          })}
                          {filteredGenes.length > 200 && (
                            <div className="px-3 py-2 text-center text-[11px] text-slate-400">
                              仅显示前 200 条（共 {filteredGenes.length} 条），请输入关键字缩小范围
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* 目标组织切换器 (Target Tissue · 方案3联动) */}
          <div className="flex flex-col gap-1.5 lg:border-l lg:border-slate-200 lg:pl-6">
            <div className="flex items-center justify-between">
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
                <span>目标组织 (方案3联动)</span>
                <span className="text-[10px] text-slate-400 font-normal">重排与诊断跟随此选择</span>
              </label>
            </div>
            <div className="inline-flex rounded-xl bg-slate-100 p-1 border border-slate-200/80">
              {TISSUE_ORDER.map((t) => {
                const active = targetTissue === t
                return (
                  <button
                    key={t}
                    type="button"
                    onClick={() => {
                      setTargetTissue(t)
                      setPage(1)
                    }}
                    className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                      active
                        ? 'bg-white text-emerald-800 font-bold shadow-sm border border-emerald-100/80'
                        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                    }`}
                  >
                    <span>{TISSUE_NAMES[t]}</span>
                    <span className="text-[10px] text-slate-400 font-normal">({t})</span>
                  </button>
                )
              })}
            </div>
          </div>

          {/* 排序器 */}
          <div className="flex items-center space-x-3">
            <span className="text-xs font-medium text-slate-500">排序依据:</span>
            <select
              value={sortBy}
              onChange={(e) => {
                const v = e.target.value
                setSortBy(v)
                const rec = SORT_RECOMMENDED_ORDER[v]
                if (rec) setSortOrder(rec)
                setPage(1)
              }}
              className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-sm focus:border-emerald-500 focus:outline-none"
            >
              <option value="efficiency_score">on-target 效率分 (v2.1 推荐排序)</option>
              <option value="priority_score">组织优先指数（{TISSUE_NAMES[targetTissue]}）降序 · 方案3推荐</option>
              <option value="hazard_score">功能性脱靶危害（{TISSUE_NAMES[targetTissue]}）升序</option>
              <option value="start">基因物理起始坐标</option>
              <option value="offtarget_count_mis3">潜在脱靶位点数 (升序优先)</option>
              <option value="gc_pct">GC 含量 (%)</option>
            </select>

            <button
              onClick={() => {
                setSortOrder((prev) => (prev === 'desc' ? 'asc' : 'desc'))
                setPage(1)
              }}
              title="切换升降序"
              className="inline-flex items-center rounded-lg border border-slate-200 bg-white p-1.5 text-xs text-slate-700 shadow-sm hover:bg-slate-50"
            >
              <ArrowUpDown className="h-4 w-4" />
              <span className="ml-1 text-xs">{sortOrder === 'desc' ? '降序' : '升序'}</span>
            </button>

            <button
              type="button"
              onClick={() => setShowSortHelp(true)}
              title="查看各排序方式的详细排名方法"
              className="inline-flex items-center rounded-lg border border-slate-200 bg-white p-1.5 text-slate-500 shadow-sm hover:bg-slate-50 hover:text-emerald-700"
            >
              <Info className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* 多维过滤控制栏 */}
        <div className="mt-5 space-y-4">
          {/* 功能元件过滤组 (外显子与启动子) */}
          <div className="rounded-xl border border-slate-200/80 bg-slate-50/70 p-3.5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div>
              <span className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                功能元件过滤 (Functional Region)
              </span>
              <span className="text-[11px] text-slate-500">
                按植物基因组功能区段筛选 gRNA 候选位点（支持多选、单选或全不选）
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <label className="flex items-center space-x-2 rounded-lg bg-white border border-slate-200 px-3 py-1.5 shadow-sm text-xs font-medium text-slate-700 cursor-pointer select-none hover:bg-slate-50 transition-colors">
                <input
                  type="checkbox"
                  id="include-exon"
                  checked={includeExon}
                  onChange={(e) => {
                    setIncludeExon(e.target.checked)
                    setPage(1)
                  }}
                  className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-bold bg-blue-100 text-blue-800">
                  外显子 (Exon)
                </span>
                <span className="text-slate-500 text-[11px]">基因敲除 (Knockout)</span>
              </label>

              <label className="flex items-center space-x-2 rounded-lg bg-white border border-slate-200 px-3 py-1.5 shadow-sm text-xs font-medium text-slate-700 cursor-pointer select-none hover:bg-slate-50 transition-colors">
                <input
                  type="checkbox"
                  id="include-promoter"
                  checked={includePromoter}
                  onChange={(e) => {
                    setIncludePromoter(e.target.checked)
                    setPage(1)
                  }}
                  className="h-4 w-4 rounded border-slate-300 text-purple-600 focus:ring-purple-500"
                />
                <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-bold bg-purple-100 text-purple-800">
                  启动子 (Promoter)
                </span>
                <span className="text-slate-500 text-[11px]">调控干涉 (CRISPRi/a)</span>
              </label>

              <div className="flex items-center space-x-1.5 border-l border-slate-200 pl-3 ml-1">
                <button
                  type="button"
                  onClick={() => {
                    setIncludeExon(true)
                    setIncludePromoter(true)
                    setPage(1)
                  }}
                  className="text-[11px] font-medium text-slate-500 hover:text-emerald-600 px-1.5 py-0.5 rounded hover:bg-slate-100 transition-colors"
                  title="同时勾选外显子与启动子"
                >
                  全选
                </button>
                <span className="text-slate-300">/</span>
                <button
                  type="button"
                  onClick={() => {
                    setIncludeExon(false)
                    setIncludePromoter(false)
                    setPage(1)
                  }}
                  className="text-[11px] font-medium text-slate-500 hover:text-rose-600 px-1.5 py-0.5 rounded hover:bg-slate-100 transition-colors"
                  title="取消勾选全部功能元件"
                >
                  清空
                </button>
              </div>
            </div>
          </div>

          {/* 阈值与物理特性过滤 */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 items-center pt-1">
            {/* 效率分滑块 */}
            <div>
              <div className="flex justify-between text-xs font-medium text-slate-600 mb-1">
                <span>最低效率分过滤:</span>
                <span className="font-bold text-emerald-600">{minScore} 分</span>
              </div>
              <input
                type="range"
                min="0"
                max="90"
                step="5"
                value={minScore}
                onChange={(e) => {
                  setMinScore(Number(e.target.value))
                  setPage(1)
                }}
                className="h-2 w-full cursor-pointer appearance-none rounded-lg bg-slate-200 accent-emerald-600"
              />
            </div>

            {/* 着丝粒过滤开关 */}
            <div className="flex items-center space-x-2.5">
              <input
                type="checkbox"
                id="exclude-centro"
                checked={excludeCentromere}
                onChange={(e) => {
                  setExcludeCentromere(e.target.checked)
                  setPage(1)
                }}
                className="h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
              />
              <label htmlFor="exclude-centro" className="text-xs font-medium text-slate-700 cursor-pointer">
                排除着丝粒不稳定区靶点 (Centromere Filter)
              </label>
            </div>
          </div>
        </div>

        {/* 基因信息摘要条 */}
        {currentGene && (
          <div className="mt-5 flex flex-wrap items-center justify-between rounded-xl bg-slate-50 px-4 py-2.5 text-xs text-slate-600">
            <div className="flex items-center space-x-4">
              <span><strong>染色体:</strong> {currentGene.chrom}</span>
              <span><strong>区间:</strong> {currentGene.start.toLocaleString()} - {currentGene.end.toLocaleString()} ({currentGene.strand}链)</span>
              <span><strong>类型:</strong> {currentGene.nlr_type || 'NLR-LRR'}</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="text-slate-500">候选靶点:</span>
              <span className="font-semibold text-slate-800">{summary?.filtered_candidates ?? currentGene.candidate_count}</span>
              <span className="text-slate-400">/ {currentGene.candidate_count} 总条数</span>
            </div>
          </div>
        )}
      </div>

      {/* 多组织表达看板与靶向适宜性诊断 (方案1 & 方案3联动) */}
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
          <div className="flex items-center space-x-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal-50 text-teal-600 border border-teal-100/60">
              <Activity className="h-4 w-4" />
            </div>
            <div>
              <h4 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <span>多组织表达看板与靶向适宜性诊断</span>
                <span className="text-[11px] font-normal text-slate-400 font-mono">
                  (莴苣 v1.1c 表达矩阵 · 根/茎/叶/花/种子)
                </span>
              </h4>
            </div>
          </div>
          {exprLoading && (
            <span className="text-xs text-slate-400 animate-pulse flex items-center gap-1">
              <div className="h-3 w-3 animate-spin rounded-full border-2 border-emerald-600 border-t-transparent"></div>
              加载表达谱...
            </span>
          )}
        </div>

        {/* 顶部元数据指标块 */}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3 mb-4">
          <div className="rounded-xl border border-slate-200/80 bg-slate-50/70 p-3">
            <span className="text-[11px] font-medium text-slate-500 block mb-0.5">v1.1c 注释映射</span>
            <div className="flex items-baseline gap-1.5">
              <span className="font-mono text-sm font-bold text-slate-800">
                {expressionData?.is_mappable ? expressionData.lsa_id : '无对应注释'}
              </span>
              {expressionData?.is_mappable && expressionData.tier && (
                <span className="text-[10px] text-slate-400 font-mono">
                  (tier {expressionData.tier} · 票比 {((expressionData.lsa_vote_frac ?? 0) * 100).toFixed(0)}%)
                </span>
              )}
            </div>
          </div>

          <div className="rounded-xl border border-slate-200/80 bg-slate-50/70 p-3">
            <span className="text-[11px] font-medium text-slate-500 block mb-0.5">最高表达组织</span>
            <div className="flex items-baseline gap-1.5">
              <span className="text-sm font-bold text-slate-800">
                {expressionData?.is_mappable ? expressionData.top_tissue : '—'}
              </span>
              {expressionData?.is_mappable && expressionData.top_tpm !== undefined && (
                <span className="text-xs font-mono font-semibold text-emerald-600">
                  {expressionData.top_tpm.toFixed(1)} TPM
                </span>
              )}
            </div>
          </div>

          <div className="rounded-xl border border-slate-200/80 bg-slate-50/70 p-3">
            <span className="text-[11px] font-medium text-slate-500 block mb-0.5 flex items-center gap-1">
              <span>组织特异性 τ</span>
              <span className="text-[10px] text-slate-400 font-normal">(τ→1特异, τ→0泛表达)</span>
            </span>
            <div className="flex items-baseline gap-1.5">
              <span className="font-mono text-sm font-bold text-slate-800">
                {expressionData?.is_mappable && expressionData.tau !== undefined
                  ? expressionData.tau.toFixed(2)
                  : '—'}
              </span>
            </div>
          </div>
        </div>

        {/* 5 组织 TPM 表达柱状图 */}
        {expressionData?.is_mappable && (
          <div className="space-y-2 mb-4">
            <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
              <span className="font-semibold text-slate-700">5 组织转录丰度对比 (TPM)</span>
              <span className="text-[11px] text-slate-400">当前选中的目标组织高亮突出</span>
            </div>
            {(() => {
              const maxTpm = Math.max(
                ...(['Root', 'Stem', 'Leaf', 'Flower', 'Seed'] as TargetTissue[]).map(
                  (t) => expressionData.tpm_dict?.[t] ?? 0
                ),
                1.0
              )
              return (['Root', 'Stem', 'Leaf', 'Flower', 'Seed'] as TargetTissue[]).map((t) => {
                const val = expressionData.tpm_dict?.[t] ?? 0
                const isSelectedTissue = targetTissue === t
                const pct = Math.max((val / maxTpm) * 100, 2)

                return (
                  <div key={t} className="flex items-center text-xs space-x-3">
                    <span className="w-10 font-medium text-slate-700 shrink-0 flex items-center justify-between">
                      <span>{TISSUE_NAMES[t]}</span>
                    </span>
                    <div className="flex-1 bg-slate-100 rounded-full h-5 overflow-hidden flex items-center relative">
                      <div
                        className={`h-full rounded-full transition-all duration-300 ${
                          isSelectedTissue
                            ? 'bg-gradient-to-r from-emerald-500 to-teal-500'
                            : 'bg-gradient-to-r from-slate-300 to-slate-400'
                        }`}
                        style={{ width: `${pct}%` }}
                      ></div>
                      {isSelectedTissue && (
                        <span className="absolute right-2 text-[10px] font-bold text-emerald-800 bg-emerald-100/90 px-1.5 py-0.5 rounded-full">
                          目标组织
                        </span>
                      )}
                    </div>
                    <span
                      className={`w-20 text-right font-mono font-semibold shrink-0 ${
                        isSelectedTissue ? 'text-emerald-700 font-bold' : 'text-slate-600'
                      }`}
                    >
                      {val.toFixed(2)} TPM
                    </span>
                  </div>
                )
              })
            })()}
          </div>
        )}

        {/* 靶向适宜性诊断 Banner (依照 Streamlit 规范) */}
        {expressionData?.is_mappable ? (
          (() => {
            const val = expressionData.tpm_dict?.[targetTissue] ?? 0
            if (val < 0.5) {
              return (
                <div className="rounded-xl border border-amber-200 bg-amber-50/80 p-3.5 text-xs text-amber-900 flex items-start space-x-2.5">
                  <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-bold">⚠️ 弱表型警示：</span>
                    <span>
                      该基因在所选组织（{TISSUE_NAMES[targetTissue]}）中转录静默（TPM {val.toFixed(2)} &lt; 0.5），CRISPR 敲除可能无法诱导明显生物学表型。
                    </span>
                  </div>
                </div>
              )
            } else if (val >= 10.0) {
              return (
                <div className="rounded-xl border border-emerald-200 bg-emerald-50/80 p-3.5 text-xs text-emerald-900 flex items-start space-x-2.5">
                  <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-bold">✅ 适宜靶向：</span>
                    <span>
                      该基因在所选组织（{TISSUE_NAMES[targetTissue]}）中高度转录（TPM {val.toFixed(1)} ≥ 10.0），染色质处于开放状态，预期编辑响应好。
                    </span>
                  </div>
                </div>
              )
            } else {
              return (
                <div className="rounded-xl border border-sky-200 bg-sky-50/80 p-3.5 text-xs text-sky-900 flex items-start space-x-2.5">
                  <Info className="h-4 w-4 text-sky-600 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-bold">ℹ️ 中等表达：</span>
                    <span>
                      所选组织（{TISSUE_NAMES[targetTissue]}）TPM {val.toFixed(2)}，介于 0.5 与 10.0 之间；表型预期中等，建议结合蛋白水平验证。
                    </span>
                  </div>
                </div>
              )
            }
          })()
        ) : (
          <div className="rounded-xl border border-amber-200 bg-amber-50/80 p-3.5 text-xs text-amber-900 flex items-start space-x-2.5">
            <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold">⚠️ 表达证据缺失：</span>
              <span>
                {expressionData?.unmappable_reason || '该基因座在莴苣 v1.1c 表达矩阵中无对应注释，不展示假定表达值。'}
              </span>
            </div>
          </div>
        )}

        {/* 串联重复簇与未挂载 scaffold 说明 */}
        {expressionData && (expressionData.n_cluster > 1 || expressionData.scaffold_evidence) && (
          <div className="mt-2.5 text-[11px] text-slate-500 space-y-1">
            {expressionData.n_cluster > 1 && (
              <div>
                ℹ️ 该基因座为 NLR 串联重复簇：主映射 {expressionData.lsa_id}（投票占比{' '}
                {((expressionData.lsa_vote_frac ?? 0) * 100).toFixed(0)}%），簇成员 {expressionData.lsa_cluster}；看板展示主映射基因的表达。
              </div>
            )}
            {expressionData.scaffold_evidence && (
              <div>
                ℹ️ 映射证据来自未挂载 scaffold（{expressionData.scaffold_evidence}）：该基因座在 v1.1c 中未挂载到染色体上。
              </div>
            )}
          </div>
        )}
      </div>

      {/* 基因组物理坐标 ECharts 交互分布图谱 (Ticket 03) */}
      <GenomicTargetMap
        gene={currentGene}
        candidates={candidatesData?.items || []}
        selectedGuideId={selectedGuideId}
        onSelectCandidate={setSelectedGuideId}
      />

      {/* 候选靶点大表 */}

      <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
        <div className="border-b border-slate-100 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <h3 className="text-base font-bold text-slate-900">候选 gRNA 靶位点推荐清单</h3>
            <button
              type="button"
              onClick={openMethods}
              title="查看算法、版本、参数与参考基因组口径说明"
              className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-600 shadow-sm transition-colors hover:bg-slate-50 hover:text-emerald-700"
            >
              <BookOpen className="h-3.5 w-3.5" />
              方法与版本
            </button>
            {isFetching && <span className="text-xs text-slate-400 animate-pulse">(更新中...)</span>}
          </div>
          <div className="text-xs text-slate-500">
            共匹配到 <strong className="text-emerald-600">{candidatesData?.total || 0}</strong> 条符合条件的靶点
            {(summary?.poly_t_filtered_count ?? 0) > 0 && (
              <span
                className="ml-2 inline-block rounded border border-amber-200 bg-amber-50 px-1.5 py-0.5 text-[11px] text-amber-700"
                title="U6 启动子（RNA Pol III）转录遇 TTTT 提前终止，含 poly-T 信号的候选已在枚举阶段硬过滤，不参与列表与排序"
              >
                另有 {summary?.poly_t_filtered_count} 条含 TTTT poly-T 终止信号已过滤
              </span>
            )}
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/75 text-slate-500 font-semibold uppercase tracking-wider">
                <th className="py-3 px-3 w-10 text-center">
                  <input
                    type="checkbox"
                    aria-label="全选当前页"
                    checked={isAllCurrentSelected}
                    onChange={toggleSelectAllCurrent}
                    className="h-3.5 w-3.5 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500 cursor-pointer"
                  />
                </th>
                <th className="py-3 px-3">#</th>
                <th className="py-3 px-4">靶点 ID</th>
                <th className="py-3 px-2">方向</th>
                <th className="py-3 px-3">基因组物理坐标</th>
                <th className="py-3 px-3">区域</th>
                <th className="py-3 px-4 font-mono" title="序列为 gRNA 方向 5'→3'：4nt 侧翼 + 20nt Guide + 3nt PAM + 3nt 侧翼">30nt 靶位点序列 (Guide + PAM)</th>
                <th
                  className="py-3 px-2"
                  title="PAM 按 gRNA 方向 5'→3' 恒写作 NGG；负链靶点在基因组正链对应位置读作 CCN"
                >
                  PAM
                </th>
                <th className="py-3 px-2">GC %</th>
                <th
                  className="py-3 px-2"
                  title="表达适配度：含 TTTT poly-T 终止信号的候选已硬过滤；5' 端为 G 提高 U6 转录效率（G-start 徽章）；MFE 为 20nt spacer 自折叠最小自由能（ViennaRNA RNAfold，不含 scaffold 骨架），ΔG < -5 kcal/mol 标红警示"
                >
                  表达适配
                </th>
                <th
                  className="py-3 px-2"
                  title="DeepSpCas9 深度学习模型预测的 on-target 切割活性分（0–1），业界常用基准；越高预期在靶切割效率越高"
                >
                  DeepSpCas9 活性
                </th>
                <th
                  className="py-3 px-2"
                  title="CRISPRon 模型预测的 on-target 切割活性分；真实模型不可用时降级为经验近似式（详见导出表《指标方法说明》）"
                >
                  CRISPRon 活性
                </th>
                <th
                  className="py-3 px-2"
                  title="全基因组潜在脱靶位点计数（错配 1–3 累计，不含完全匹配行）；点击数字查看脱靶位点明细（坐标/错配位置/CFD/MIT 评分/区域）"
                >
                  脱靶数 (&le;3)
                </th>
                <th className="py-3 px-3 text-right">组织优先 ({TISSUE_NAMES[targetTissue]})</th>
                <th className="py-3 px-3 text-right">功能危害 ({TISSUE_NAMES[targetTissue]})</th>
                <th className="py-3 px-3 text-center">表达证据</th>
                <th className="py-3 px-2">着丝粒</th>
                <th
                  className="py-3 px-4 text-right"
                  title="on-target 效率分：自训练 Stacking 元模型（v2.1）预测的在靶切割活性综合分，0–100，由 DeepSpCas9 活性、CRISPRon 活性、GC、Tm、polyT 等 10 维序列特征构成；悬停每行分数可查看两个成分分"
                >
                  on-target 效率分 (v2.1)
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {candidatesLoading ? (
                <tr>
                  <td colSpan={18} className="py-12 text-center text-slate-400">
                    <div className="flex items-center justify-center space-x-2">
                      <div className="h-4 w-4 animate-spin rounded-full border-2 border-emerald-600 border-t-transparent"></div>
                      <span>正在检索候选 gRNA 靶位点...</span>
                    </div>
                  </td>
                </tr>
              ) : !candidatesData?.items || candidatesData.items.length === 0 ? (
                <tr>
                  <td colSpan={18} className="py-12 text-center text-slate-500">
                    {currentRegionType === 'none' ? (
                      <div className="flex flex-col items-center justify-center space-y-2">
                        <span className="text-sm font-semibold text-slate-700">当前未勾选任何功能元件</span>
                        <span className="text-xs text-slate-400">
                          外显子与启动子均处于未勾选状态。请在上方的【功能元件过滤】中勾选对应区段以查看候选位点。
                        </span>
                        <button
                          type="button"
                          onClick={() => {
                            setIncludeExon(true)
                            setIncludePromoter(true)
                            setPage(1)
                          }}
                          className="mt-1 inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-200 transition-colors"
                        >
                          一键恢复全选 (外显子 + 启动子)
                        </button>
                      </div>
                    ) : (
                      '未找到符合当前过滤条件的候选 gRNA 靶点，请尝试降低最低效率分限制或关闭着丝粒过滤项。'
                    )}
                  </td>
                </tr>
              ) : (
                candidatesData.items.map((cand, idx) => {
                  const globalIdx = (page - 1) * pageSize + idx + 1
                  const eff = cand.efficiency_score ?? 0
                  const effColor =
                    eff >= 70
                      ? 'bg-emerald-50 text-emerald-700 ring-emerald-600/20'
                      : eff >= 40
                      ? 'bg-amber-50 text-amber-700 ring-amber-600/20'
                      : 'bg-slate-100 text-slate-700 ring-slate-400/20'

                  // 高亮显示 30nt：前4nt(灰) + 20nt Guide(加黑) + 3nt PAM(绿色粗体) + 3nt(灰)
                  const flank5 = cand.seq30.slice(0, 4)
                  const guide = cand.seq20
                  const pam = cand.pam
                  const flank3 = cand.seq30.slice(27, 30)

                  const isSelected = selectedGuideId === cand.guide_id

                  return (
                    <tr
                      key={cand.id}
                      onClick={() => setSelectedGuideId(isSelected ? null : cand.guide_id)}
                      className={`cursor-pointer transition-colors ${
                        isSelected
                          ? 'bg-sky-50 ring-1 ring-inset ring-sky-300 font-medium'
                          : 'hover:bg-slate-50/70'
                      }`}
                    >
                      <td className="py-3 px-3 text-center" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          aria-label={`选择靶点 ${cand.guide_id}`}
                          checked={selectedCandidateIds.has(cand.id)}
                          onChange={() => toggleSelectOne(cand.id)}
                          className="h-3.5 w-3.5 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500 cursor-pointer"
                        />
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-400">{globalIdx}</td>
                      <td className="py-3 px-4 font-semibold text-slate-900">{cand.guide_id}</td>

                      <td className="py-3 px-4">
                        <span
                          className={`inline-block px-1.5 py-0.5 rounded text-[11px] font-mono font-bold ${
                            cand.strand === '+' ? 'bg-sky-50 text-sky-700' : 'bg-rose-50 text-rose-700'
                          }`}
                        >
                          {cand.strand}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-600">
                        {cand.start.toLocaleString()} - {cand.end.toLocaleString()}
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold ${
                            cand.region_type === 'exon'
                              ? 'bg-blue-50 text-blue-700 ring-1 ring-inset ring-blue-600/20'
                              : 'bg-purple-50 text-purple-700 ring-1 ring-inset ring-purple-600/20'
                          }`}
                        >
                          {cand.region_type === 'exon' ? '外显子 (exon)' : '启动子 (promoter)'}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono text-xs">
                        <span className="text-slate-400">{flank5}</span>
                        <span className="font-semibold text-slate-900 bg-amber-50 px-1 rounded">{guide}</span>
                        <span className="font-bold text-emerald-700 bg-emerald-100 px-1 rounded mx-0.5">{pam}</span>
                        <span className="text-slate-400">{flank3}</span>
                      </td>
                      <td className="py-3 px-4 font-mono font-bold text-emerald-700">{cand.pam}</td>
                      <td className="py-3 px-4 font-mono text-slate-700">{cand.gc_pct.toFixed(1)}%</td>

                      {/* 表达适配度（教师反馈 #2）：MFE + 5'G 徽章 */}
                      <td className="py-3 px-3" title={cand.expression_fitness_note || undefined}>
                        <div className="flex flex-col items-start gap-1">
                          {cand.mfe_kcal !== undefined && cand.mfe_kcal !== null ? (
                            <span
                              className={`inline-flex items-center gap-1 font-mono text-[11px] font-semibold ${
                                cand.mfe_risk ? 'text-rose-600' : 'text-slate-700'
                              }`}
                            >
                              {cand.mfe_kcal.toFixed(1)} kcal/mol
                              {cand.mfe_risk && (
                                <span
                                  title="ΔG < -5 kcal/mol：自折叠可能抑制靶向活性"
                                  className="inline-flex items-center rounded bg-rose-100 px-1 py-0.5 text-[10px] font-bold text-rose-700"
                                >
                                  <AlertTriangle className="h-3 w-3" />
                                </span>
                              )}
                            </span>
                          ) : (
                            <span
                              className="text-slate-400 text-[11px]"
                              title="ViennaRNA 不可用：无法计算 spacer 自折叠 MFE"
                            >
                              — <span className="text-[10px]">ViennaRNA 不可用</span>
                            </span>
                          )}
                          <span
                            className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-semibold ${
                              cand.five_prime_g
                                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200/70'
                                : 'bg-slate-50 text-slate-400 border border-slate-200/70'
                            }`}
                          >
                            G-start
                          </span>
                        </div>
                      </td>
                      <td
                        className="py-3 px-2 font-mono text-slate-700"
                        title="DeepSpCas9 模型预测的 on-target 切割活性分（0–1）"
                      >
                        {cand.deepspcas9_score !== undefined && cand.deepspcas9_score !== null ? (
                          cand.deepspcas9_score.toFixed(3)
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>
                      <td
                        className="py-3 px-2 font-mono text-slate-700"
                        title="CRISPRon 模型预测的 on-target 切割活性分"
                      >
                        {cand.crispron_score !== undefined && cand.crispron_score !== null ? (
                          cand.crispron_score.toFixed(2)
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-700">
                        {computingIds.has(cand.id) ? (
                          <span
                            className="inline-flex items-center gap-1.5 text-emerald-600"
                            title="正在计算脱靶：全基因组扫描（Cas-OFFinder 口径，≤3 错配、PAM=NGG），约 1 分钟/条，请稍候"
                          >
                            <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-emerald-600 border-t-transparent" />
                            <span className="text-[11px] font-semibold">计算中</span>
                          </span>
                        ) : cand.offtarget_count_mis3 === null || cand.offtarget_count_mis3 === undefined ? (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation()
                              setComputeConfirm(cand)
                            }}
                            title="未计算：未对该 guide 做全基因组脱靶扫描，不能读作'已验证无脱靶'；点击可计算脱靶并查看位点明细"
                            className="text-slate-400 underline decoration-dotted underline-offset-2 transition-colors hover:decoration-solid hover:text-emerald-700"
                          >
                            未计算
                          </button>
                        ) : (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation()
                              openOfftargetDrawer(cand)
                            }}
                            title="点击查看脱靶位点明细（坐标/错配位置/CFD/MIT 评分/区域）"
                            className={`font-semibold underline decoration-dotted underline-offset-2 transition-colors hover:decoration-solid hover:text-emerald-700 ${
                              cand.offtarget_count_mis3 > 0 ? 'text-amber-600' : 'text-emerald-600'
                            }`}
                          >
                            {cand.offtarget_count_mis3}
                          </button>
                        )}
                      </td>

                      {/* 组织优先指数 (方案3) */}
                      <td className="py-3 px-3 text-right">
                        {cand.priority_score !== undefined && cand.priority_score !== null ? (
                          <span className="inline-flex items-center rounded-md bg-emerald-50 px-2 py-0.5 text-[11px] font-mono font-bold text-emerald-800 ring-1 ring-inset ring-emerald-600/20">
                            {cand.priority_score.toFixed(3)}
                          </span>
                        ) : (
                          <span className="text-slate-400 font-mono text-[11px]">—</span>
                        )}
                      </td>

                      {/* 功能性脱靶危害 (方案5) */}
                      <td className="py-3 px-3 text-right">
                        {cand.hazard_score !== undefined && cand.hazard_score !== null ? (
                          <span
                            className={`inline-flex items-center rounded-md px-1.5 py-0.5 text-[11px] font-mono font-semibold ${
                              cand.hazard_score > 0
                                ? 'bg-rose-50 text-rose-700 ring-1 ring-inset ring-rose-600/20'
                                : 'text-slate-500'
                            }`}
                          >
                            {cand.hazard_score.toFixed(3)}
                          </span>
                        ) : (
                          <span className="text-slate-400 font-mono text-[11px]">—</span>
                        )}
                      </td>

                      {/* 表达证据状态 */}
                      <td className="py-3 px-3 text-center">
                        {cand.expression_status_display ? (
                          <span
                            title={cand.expression_evidence_note}
                            className={`inline-block px-2 py-0.5 rounded text-[10px] font-medium ${
                              cand.expression_status === 'mapped'
                                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200/60'
                                : cand.expression_status === 'mapped_cluster'
                                ? 'bg-indigo-50 text-indigo-700 border border-indigo-200/60'
                                : cand.expression_status === 'mapped_scaffold'
                                ? 'bg-cyan-50 text-cyan-700 border border-cyan-200/60'
                                : cand.expression_status === 'unassessed'
                                ? 'bg-slate-50 text-slate-500 border border-slate-200/60'
                                : 'bg-amber-50 text-amber-700 border border-amber-200/60'
                            }`}
                          >
                            {cand.expression_status_display}
                          </span>
                        ) : (
                          <span className="text-slate-400 text-[10px]">—</span>
                        )}
                      </td>

                      <td className="py-3 px-4">
                        {cand.is_centromere ? (
                          <span className="inline-flex items-center text-[10px] font-medium text-rose-600 bg-rose-50 px-1.5 py-0.5 rounded">
                            着丝粒
                          </span>
                        ) : (
                          <span className="text-slate-400 text-[10px]">否</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <span
                          className={`inline-flex items-center rounded-lg px-2.5 py-1 text-xs font-bold font-mono ring-1 ring-inset ${effColor}`}
                          title={`on-target 效率分（Stacking 元模型 v2.1，0–100）\n成分：DeepSpCas9 ${
                            cand.deepspcas9_score !== undefined && cand.deepspcas9_score !== null
                              ? cand.deepspcas9_score.toFixed(3)
                              : '—'
                          } · CRISPRon ${
                            cand.crispron_score !== undefined && cand.crispron_score !== null
                              ? cand.crispron_score.toFixed(2)
                              : '—'
                          }\n预测的是在靶切割活性，与脱靶数互相独立，需两者综合评价`}
                        >
                          {eff > 0 ? eff.toFixed(2) : '-'}
                        </span>
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>

        {/* 分页控制栏 */}
        {candidatesData && candidatesData.total_pages > 1 && (
          <div className="flex items-center justify-between border-t border-slate-100 px-6 py-3.5 bg-slate-50/50">
            <div className="text-xs text-slate-500">
              显示第 {(page - 1) * pageSize + 1} - {Math.min(page * pageSize, candidatesData.total)} 条，共{' '}
              {candidatesData.total} 条
            </div>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="inline-flex items-center rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 shadow-sm hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="h-4 w-4 mr-1" />
                上一页
              </button>
              <span className="text-xs font-medium text-slate-700 px-2">
                {page} / {candidatesData.total_pages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(candidatesData.total_pages, p + 1))}
                disabled={page >= candidatesData.total_pages}
                className="inline-flex items-center rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 shadow-sm hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                下一页
                <ChevronRight className="h-4 w-4 ml-1" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 悬浮多选导出操作栏 */}
      {selectedCandidateIds.size > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 flex flex-wrap items-center gap-3 rounded-2xl border border-emerald-200 bg-white/95 px-5 py-3 shadow-xl backdrop-blur-md">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-800">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-600 text-white text-[11px] font-bold">
              {selectedCandidateIds.size}
            </span>
            <span>个靶点已勾选</span>
          </div>

          <div className="h-4 w-px bg-slate-200 hidden sm:block" />

          <div className="flex items-center gap-2">
            <input
              type="text"
              placeholder="自定义方案名称..."
              value={batchName}
              onChange={(e) => setBatchName(e.target.value)}
              className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-800 placeholder-slate-400 focus:border-emerald-500 focus:outline-none w-48"
            />
            {isExporting && exportProgress ? (
              <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50/70 px-2.5 py-1.5">
                <span className="h-3.5 w-3.5 shrink-0 animate-spin rounded-full border-2 border-emerald-600 border-t-transparent" />
                <div
                  className="h-1.5 w-36 overflow-hidden rounded-full bg-emerald-100"
                  role="progressbar"
                  aria-label="导出进度"
                  aria-valuemin={0}
                  aria-valuemax={exportProgress.total}
                  aria-valuenow={exportProgress.done}
                >
                  <div
                    className="h-full rounded-full bg-emerald-600 transition-all duration-500"
                    style={{
                      width: `${Math.round(
                        ((exportProgress.done + (exportProgress.phase === 'scan' ? 0.5 : 0)) /
                          exportProgress.total) *
                          100
                      )}%`,
                    }}
                  />
                </div>
                <span className="text-[10px] font-semibold text-emerald-800">
                  {exportProgress.phase === 'scan'
                    ? `脱靶扫描中 ${Math.min(exportProgress.done + 1, exportProgress.total)}/${exportProgress.total}…约 1 分钟/条`
                    : '正在生成导出文件…'}
                </span>
              </div>
            ) : pendingScanCount > 0 ? (
              <span className="text-[10px] text-amber-600 bg-amber-50 border border-amber-200 rounded px-1.5 py-0.5 max-w-[220px]">
                {pendingScanCount} 个靶点脱靶数未计算，首次导出需全基因组扫描（约 1 分钟/条）
              </span>
            ) : null}
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => handleExport('csv')}
              disabled={isExporting}
              className="inline-flex items-center gap-1.5 rounded-xl bg-emerald-600 px-3.5 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-emerald-700 disabled:opacity-50 transition-colors"
            >
              <Download className="h-3.5 w-3.5" />
              <span>
                {isExporting
                  ? exportProgress?.phase === 'scan'
                    ? '脱靶扫描中…请稍候'
                    : '生成中...'
                  : '导出 CSV'}
              </span>
            </button>

            <button
              onClick={() => handleExport('xlsx')}
              disabled={isExporting}
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 disabled:opacity-50 transition-colors"
            >
              <FileSpreadsheet className="h-3.5 w-3.5 text-emerald-600" />
              <span>
                {isExporting
                  ? exportProgress?.phase === 'scan'
                    ? '脱靶扫描中…请稍候'
                    : '生成中...'
                  : '导出 Excel'}
              </span>
            </button>

            <button
              onClick={() => setSelectedCandidateIds(new Set())}
              className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors ml-1"
              title="清空已选"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* 计算脱靶确认框：点击"未计算"格弹出，确认后按需全基因组扫描并回填 */}
      {computeConfirm && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 backdrop-blur-sm"
          onClick={() => setComputeConfirm(null)}
        >
          <div className="w-full max-w-md rounded-2xl bg-white shadow-xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-start justify-between border-b border-slate-100 px-5 py-4">
              <div>
                <h3 className="text-sm font-bold text-slate-800">要计算脱靶吗？</h3>
                <p className="mt-1.5 text-[11px] leading-relaxed text-slate-500">
                  将对{' '}
                  <span className="font-mono font-semibold text-slate-700">{computeConfirm.guide_id}</span>{' '}
                  （<span className="font-mono text-slate-600">{computeConfirm.seq20}</span>）做 Cas-OFFinder
                  口径全基因组脱靶扫描（≤3 错配、PAM=NGG、正负链分行计数），单条约 1 分钟。完成后本行显示脱靶数，并自动打开脱靶位点明细抽屉。
                </p>
              </div>
              <button
                onClick={() => setComputeConfirm(null)}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                title="关闭"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="flex justify-end gap-2 px-5 py-4">
              <button
                onClick={() => setComputeConfirm(null)}
                className="rounded-lg border border-slate-200 bg-white px-3.5 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-50 transition-colors"
              >
                取消
              </button>
              <button
                onClick={confirmComputeOfftarget}
                className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700 transition-colors"
              >
                <Dna className="h-3.5 w-3.5" />
                计算脱靶
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 排序方式说明弹窗 */}
      {showSortHelp && (
        <div
          className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-900/40 p-4 backdrop-blur-sm sm:p-8"
          onClick={() => setShowSortHelp(false)}
        >
          <div
            className="w-full max-w-2xl rounded-2xl bg-white shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between border-b border-slate-100 px-5 py-4">
              <div>
                <h3 className="text-sm font-bold text-slate-800">排序方式说明 · 各指标详细排名方法</h3>
                <p className="mt-0.5 text-[11px] text-slate-500">
                  切换排序指标时自动套用该指标的推荐方向（升降序按钮仍可手动切换）；「未计算」的候选在任何排序下都排在最后
                </p>
              </div>
              <button
                onClick={() => setShowSortHelp(false)}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                title="关闭"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="space-y-3 px-5 py-4">
              {sortHelpItems.map((it) => (
                <div
                  key={it.key}
                  className={`rounded-xl border px-4 py-3 ${
                    it.key === sortBy
                      ? 'border-emerald-200 bg-emerald-50/60'
                      : 'border-slate-200/80 bg-white'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-bold text-slate-800">{it.title}</span>
                    {it.key === sortBy && (
                      <span className="shrink-0 rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-700">
                        当前选中
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-[11px] font-medium text-emerald-700">排名方式：{it.direction}</p>
                  {it.lines.map((ln) => (
                    <p key={ln} className="mt-1 text-[11px] leading-relaxed text-slate-600">
                      {ln}
                    </p>
                  ))}
                </div>
              ))}
            </div>
            <div className="border-t border-slate-100 px-5 py-3 text-[11px] text-slate-500">
              各指标完整口径（含特征系数、公式来源）见导出 Excel 的《指标方法说明》sheet。
            </div>
          </div>
        </div>
      )}

      {/* 脱靶位点明细抽屉（教师反馈 #1）：点击"脱靶数"数字打开，按需加载 */}
      {offtargetCand && (
        <div
          className="fixed inset-0 z-50 flex justify-end bg-slate-900/40 backdrop-blur-sm"
          onClick={() => setOfftargetCand(null)}
        >
          <div
            className="h-full w-full max-w-3xl overflow-y-auto bg-white shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            {/* 抽屉头部 */}
            <div className="sticky top-0 z-10 flex items-start justify-between border-b border-slate-100 bg-white px-5 py-4">
              <div>
                <h3 className="text-sm font-bold text-slate-800">脱靶位点明细（全基因组 ≤3 错配扫描）</h3>
                <p className="mt-0.5 flex flex-wrap items-center gap-x-2 text-[11px] text-slate-500">
                  <span className="font-mono font-semibold text-slate-700">{offtargetCand.guide_id}</span>
                  <span className="font-mono text-slate-600">{offtargetCand.seq20}</span>
                  <span>按 Esc 或点击左侧空白关闭</span>
                </p>
              </div>
              <button
                onClick={() => setOfftargetCand(null)}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                title="关闭"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-4 px-5 py-4">
              {offtargetLoading && (
                <div className="flex items-center justify-center space-x-2 rounded-xl border border-slate-200 bg-slate-50/70 py-10 text-xs text-slate-500">
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-emerald-600 border-t-transparent"></div>
                  <span>
                    正在扫描全基因组脱靶位点（Cas-OFFinder 口径，≤3 错配、PAM=NGG）…首次查询可能需要数秒到数分钟，请稍候
                  </span>
                </div>
              )}

              {offtargetError && (
                <div className="flex items-start space-x-2 rounded-xl border border-rose-200 bg-rose-50/80 p-3.5 text-xs text-rose-800">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" />
                  <div>
                    <span className="font-bold">脱靶明细获取失败：</span>
                    <span>{offtargetError}</span>
                  </div>
                </div>
              )}

              {offtargetData &&
                (() => {
                  const sp = offtargetData.specificity
                  return (
                    <>
                      {/* ① 顶部摘要：profile 四档计数 + 参考基因组 + 特异性汇总 */}
                      <div className="space-y-2.5 rounded-xl border border-slate-200/80 bg-slate-50/70 p-3.5">
                        <div className="grid grid-cols-4 gap-2">
                          {[
                            { label: '完全匹配', value: offtargetData.profile.exact, cls: 'text-slate-800' },
                            { label: '1 错配', value: offtargetData.profile.mis1, cls: 'text-orange-700' },
                            { label: '2 错配', value: offtargetData.profile.mis2, cls: 'text-amber-700' },
                            { label: '3 错配', value: offtargetData.profile.mis3, cls: 'text-emerald-700' },
                          ].map((it) => (
                            <div key={it.label} className="rounded-lg border border-slate-200/80 bg-white p-2 text-center">
                              <div className={`font-mono text-lg font-bold ${it.cls}`}>{it.value}</div>
                              <div className="text-[10px] text-slate-500">{it.label}</div>
                            </div>
                          ))}
                        </div>
                        <p className="text-[11px] text-slate-600">{offtargetData.genome_note}</p>
                        <div className="rounded-lg border border-emerald-100 bg-emerald-50/60 p-2.5 text-[11px] text-slate-700">
                          <div className="mb-1 font-semibold text-emerald-800">guide 级特异性汇总（CRISPOR 口径）</div>
                          <div className="flex flex-wrap gap-x-4 gap-y-1">
                            <span>
                              MIT Sguide：<strong className="font-mono">{Number(sp.mit_specificity).toFixed(2)}</strong>
                            </span>
                            <span>
                              CFD 特异性：<strong className="font-mono">{Number(sp.cfd_specificity).toFixed(2)}</strong>
                            </span>
                            <span>计分脱靶位点：{sp.n_offtarget_sites_scored} 个</span>
                            <span>Σ MIT hit：{Number(sp.mit_hit_sum).toFixed(1)}</span>
                            <span>Σ CFD site：{Number(sp.cfd_hit_sum).toFixed(2)}</span>
                          </div>
                          <p className="mt-1 text-slate-500">
                            口径：MIT Sguide = 100/(100+ΣhitScore)×100；CFD 特异性 = 100/Σcfd_site
                            {sp.on_target_excluded ? '；已排除候选自身在靶位点，不计入脱靶风险汇总' : ''}
                          </p>
                        </div>
                        {offtargetData.sites_truncated && (
                          <div className="rounded-lg border border-amber-200 bg-amber-50/80 px-2.5 py-1.5 text-[11px] text-amber-800">
                            明细已截断，计数仍为全量（位点表格仅展示前 {offtargetData.sites.length} 行）
                          </div>
                        )}
                      </div>

                      {/* ② 位点明细表格 */}
                      <div>
                        <div className="mb-1.5 flex items-center justify-between">
                          <h4 className="text-xs font-bold text-slate-800">
                            位点明细（{offtargetData.sites.length} 行，正负链分行计数）
                          </h4>
                          <span className="text-[10px] text-slate-400">
                            错配位置为 gRNA 方向 1-based（PAM 远端为 1）；错配碱基以红色高亮
                          </span>
                        </div>
                        {offtargetData.sites.length === 0 ? (
                          <div className="rounded-xl border border-slate-200 bg-white py-8 text-center text-xs text-slate-500">
                            未发现 ≤3 错配的脱靶位点（含完全匹配行）。
                          </div>
                        ) : (
                          <div className="overflow-x-auto rounded-xl border border-slate-200">
                            <table className="w-full text-left text-[11px]">
                              <thead>
                                <tr className="border-b border-slate-200 bg-slate-50/75 text-slate-500 font-semibold">
                                  <th className="px-2 py-2">风险</th>
                                  <th className="px-2 py-2">染色体:坐标</th>
                                  <th className="px-2 py-2">链</th>
                                  <th
                                    className="px-2 py-2"
                                    title="错配位置为 gRNA 方向 1-based（PAM 远端为 1）"
                                  >
                                    错配数
                                  </th>
                                  <th
                                    className="px-2 py-2"
                                    title="错配位置为 gRNA 方向 1-based（PAM 远端为 1）"
                                  >
                                    错配位置
                                  </th>
                                  <th className="px-2 py-2 font-mono" title="protospacer20，gRNA 方向 5'→3'，错配碱基高亮">
                                    比对序列
                                  </th>
                                  <th className="px-2 py-2">PAM</th>
                                  <th className="px-2 py-2" title="CFD（Doench 2016）单位点分，4 位小数">
                                    CFD
                                  </th>
                                  <th className="px-2 py-2" title="MIT/Hsu 2013 单位点 hit score，2 位小数">
                                    MIT
                                  </th>
                                  <th className="px-2 py-2">所在区域</th>
                                </tr>
                              </thead>
                              <tbody>
                                {offtargetData.sites.map((s, i) => (
                                  <tr
                                    key={`${s.chrom}-${s.start}-${s.end}-${s.strand}-${i}`}
                                    className={`border-b border-slate-100 last:border-b-0 ${
                                      s.is_ontarget ? 'bg-slate-50' : ''
                                    }`}
                                  >
                                    <td className="px-2 py-2">
                                      <span
                                        title={s.risk_note}
                                        className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-semibold ${riskBadgeClass(
                                          s.risk_level
                                        )}`}
                                      >
                                        {s.risk_level}
                                      </span>
                                    </td>
                                    <td className="whitespace-nowrap px-2 py-2 font-mono text-slate-700">
                                      {s.chrom}:{s.start.toLocaleString()}-{s.end.toLocaleString()}
                                    </td>
                                    <td className="px-2 py-2 font-mono text-slate-700">{s.strand}</td>
                                    <td className="px-2 py-2 font-mono text-slate-700">{s.mismatch_count}</td>
                                    <td className="px-2 py-2 font-mono text-slate-500">
                                      {s.mismatch_positions && s.mismatch_positions.length > 0
                                        ? s.mismatch_positions.join(', ')
                                        : '—'}
                                    </td>
                                    <td className="whitespace-nowrap px-2 py-2 font-mono">
                                      {renderAlignedSeq(s.protospacer20, s.mismatch_positions)}
                                    </td>
                                    <td className="px-2 py-2 font-mono font-semibold text-emerald-700">{s.pam}</td>
                                    <td className="px-2 py-2 font-mono text-slate-700">
                                      {Number(s.cfd_score).toFixed(4)}
                                    </td>
                                    <td className="px-2 py-2 font-mono text-slate-700">
                                      {Number(s.mit_hit_score).toFixed(2)}
                                    </td>
                                    <td className="px-2 py-2 text-slate-600">
                                      {s.region_label || '—'}
                                      {s.gene_id && (
                                        <span className="ml-1 font-mono text-[10px] text-slate-400">{s.gene_id}</span>
                                      )}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        )}
                      </div>

                      {/* ③ 搜索与评分口径 */}
                      <div className="rounded-xl border border-slate-200/80 bg-slate-50/70 p-3">
                        <div className="mb-1 text-[11px] font-bold text-slate-700">搜索与评分口径</div>
                        <p className="text-[11px] leading-relaxed text-slate-600">{offtargetData.method_note}</p>
                      </div>
                    </>
                  )
                })()}
            </div>
          </div>
        </div>
      )}

      {/* 方法与版本弹窗（教师反馈 #4/#5）：算法、版本、参数与参考基因组口径 */}
      {showMethods && (
        <div
          className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-900/40 p-4 backdrop-blur-sm sm:p-8"
          onClick={() => setShowMethods(false)}
        >
          <div className="w-full max-w-3xl rounded-2xl bg-white shadow-xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-start justify-between border-b border-slate-100 px-5 py-4">
              <div>
                <h3 className="text-sm font-bold text-slate-800">方法与版本 · 算法口径与参考基因组说明</h3>
                <p className="mt-0.5 text-[11px] text-slate-500">
                  效率模型、脱靶检测、表达适配度与基因结构注释的方法、参数与版本（透明性声明）
                </p>
              </div>
              <button
                onClick={() => setShowMethods(false)}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                title="关闭"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-3 px-5 py-4">
              {methodsLoading && (
                <div className="flex items-center justify-center space-x-2 rounded-xl border border-slate-200 bg-slate-50/70 py-10 text-xs text-slate-500">
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-emerald-600 border-t-transparent"></div>
                  <span>正在加载方法与版本说明…</span>
                </div>
              )}

              {methodsError && (
                <div className="flex items-start space-x-2 rounded-xl border border-rose-200 bg-rose-50/80 p-3.5 text-xs text-rose-800">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" />
                  <div>
                    <span className="font-bold">方法与版本信息获取失败：</span>
                    <span>{methodsError}</span>
                  </div>
                </div>
              )}

              {methodsData && (
                <div className="space-y-3">
                  {/* 效率分模型 */}
                  <section className="rounded-xl border border-slate-200/80 bg-white p-4">
                    <h4 className="mb-2 border-b border-slate-100 pb-1.5 text-xs font-bold text-slate-800">
                      效率分模型（on-target 效率分）
                    </h4>
                    <div className="space-y-1.5 text-[11px] leading-relaxed text-slate-600">
                      <p>
                        <span className="font-semibold text-slate-700">名称：</span>
                        {methodsData.efficiency_model.name}
                      </p>
                      <p>
                        <span className="font-semibold text-slate-700">类型：</span>
                        {methodsData.efficiency_model.kind}
                      </p>
                      <div>
                        <span className="font-semibold text-slate-700">组成成分：</span>
                        <ul className="mt-1 list-inside list-disc space-y-0.5 pl-1">
                          {(methodsData.efficiency_model.components || []).map((c, i) => (
                            <li key={i}>{c}</li>
                          ))}
                        </ul>
                      </div>
                      <p>
                        <span className="font-semibold text-slate-700">验证：</span>
                        {methodsData.efficiency_model.validation}
                      </p>
                      <p>
                        <span className="font-semibold text-slate-700">模型卡：</span>
                        <span className="font-mono text-slate-500">{methodsData.efficiency_model.model_card}</span>
                      </p>
                      <p>
                        <span className="font-semibold text-slate-700">模型谱系：</span>
                        {methodsData.efficiency_model.lineage_note}
                      </p>
                    </div>
                  </section>

                  {/* 脱靶检测 */}
                  <section className="rounded-xl border border-slate-200/80 bg-white p-4">
                    <h4 className="mb-2 border-b border-slate-100 pb-1.5 text-xs font-bold text-slate-800">
                      脱靶检测（全基因组扫描与位点评分）
                    </h4>
                    <div className="space-y-1.5 text-[11px] leading-relaxed text-slate-600">
                      <p>
                        <span className="font-semibold text-slate-700">搜索方法：</span>
                        {methodsData.offtarget.search}
                      </p>
                      <div>
                        <span className="font-semibold text-slate-700">参数：</span>
                        <ul className="mt-1 list-inside list-disc space-y-0.5 pl-1">
                          <li>PAM：{methodsData.offtarget.params?.pam}</li>
                          <li>gRNA 长度：{methodsData.offtarget.params?.gRNA_length}</li>
                          <li>最大错配数：{methodsData.offtarget.params?.max_mismatches}</li>
                          <li>链处理：{methodsData.offtarget.params?.strands}</li>
                        </ul>
                      </div>
                      <div>
                        <span className="font-semibold text-slate-700">位点评分：</span>
                        <ul className="mt-1 list-inside list-disc space-y-0.5 pl-1">
                          {(methodsData.offtarget.site_scores || []).map((s, i) => (
                            <li key={i}>{s}</li>
                          ))}
                        </ul>
                      </div>
                      <p>
                        <span className="font-semibold text-slate-700">guide 级特异性：</span>
                        {methodsData.offtarget.guide_specificity}
                      </p>
                      <p>
                        <span className="font-semibold text-slate-700">风险分档：</span>
                        {methodsData.offtarget.risk_note}
                      </p>
                    </div>
                  </section>

                  {/* 表达适配度 */}
                  <section className="rounded-xl border border-slate-200/80 bg-white p-4">
                    <h4 className="mb-2 border-b border-slate-100 pb-1.5 text-xs font-bold text-slate-800">
                      表达适配度（poly-T / 5'G / MFE / GC）
                    </h4>
                    <div className="space-y-1.5 text-[11px] leading-relaxed text-slate-600">
                      <p>
                        <span className="font-semibold text-slate-700">poly-T：</span>
                        {methodsData.expression_fitness.poly_t}
                      </p>
                      <p>
                        <span className="font-semibold text-slate-700">5' 端 G：</span>
                        {methodsData.expression_fitness.five_prime_g}
                      </p>
                      <p>
                        <span className="font-semibold text-slate-700">MFE 自折叠：</span>
                        {methodsData.expression_fitness.mfe}
                      </p>
                      <p>
                        <span className="font-semibold text-slate-700">GC 含量：</span>
                        {methodsData.expression_fitness.gc}
                      </p>
                    </div>
                  </section>

                  {/* 基因结构注释 */}
                  <section className="rounded-xl border border-slate-200/80 bg-white p-4">
                    <h4 className="mb-2 border-b border-slate-100 pb-1.5 text-xs font-bold text-slate-800">
                      基因结构注释
                    </h4>
                    <div className="space-y-1.5 text-[11px] leading-relaxed text-slate-600">
                      <p>
                        <span className="font-semibold text-slate-700">结构来源：</span>
                        {methodsData.gene_structure.source}
                      </p>
                      <p>
                        <span className="font-semibold text-slate-700">蛋白功能域：</span>
                        {methodsData.gene_structure.protein_domains}
                      </p>
                    </div>
                  </section>

                  {/* 参考基因组 */}
                  <section className="rounded-xl border border-slate-200/80 bg-white p-4">
                    <h4 className="mb-2 border-b border-slate-100 pb-1.5 text-xs font-bold text-slate-800">
                      参考基因组（{(methodsData.reference_genomes || []).length} 个参考包）
                    </h4>
                    <ul className="space-y-1.5">
                      {(methodsData.reference_genomes || []).map((g) => (
                        <li
                          key={g.id}
                          className="flex flex-wrap items-center gap-2 rounded-lg border border-slate-100 bg-slate-50/70 px-2.5 py-1.5 text-[11px]"
                        >
                          <span className="font-mono font-semibold text-slate-700">{g.id}</span>
                          <span className="text-slate-600">{g.display_name}</span>
                          <span
                            className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${
                              g.fasta_available
                                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200/70'
                                : 'bg-slate-100 text-slate-400 border border-slate-200'
                            }`}
                          >
                            FASTA {g.fasta_available ? '可用' : '缺失'}
                          </span>
                          <span
                            className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${
                              g.gff_available
                                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200/70'
                                : 'bg-slate-100 text-slate-400 border border-slate-200'
                            }`}
                          >
                            GFF {g.gff_available ? '可用' : '缺失'}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </section>

                  {/* 免责声明 */}
                  <div className="rounded-xl border border-amber-200 bg-amber-50/80 p-3 text-[11px] leading-relaxed text-amber-900">
                    <span className="font-bold">免责声明：</span>
                    {methodsData.disclaimer}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
