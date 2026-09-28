import React, { useState, useMemo, useRef, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Activity,
  AlertTriangle,
  ArrowUpDown,
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

export type TargetTissue = 'Leaf' | 'Root' | 'Stem' | 'Flower' | 'Seed'

export const TISSUE_NAMES: Record<TargetTissue, string> = {
  Leaf: '叶',
  Root: '根',
  Stem: '茎',
  Flower: '花',
  Seed: '种子',
}

export const TISSUE_ORDER: TargetTissue[] = ['Leaf', 'Root', 'Stem', 'Flower', 'Seed']

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
  }
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

async function fetchCandidates(params: {
  gene_id: string
  target_tissue?: TargetTissue
  min_score?: number
  exclude_centromere?: boolean
  exon_only?: boolean
  region_type?: string
  page?: number
  page_size?: number
  sort_by?: string
  sort_order?: string
}): Promise<CandidatesResponse> {
  const sp = new URLSearchParams()
  sp.set('gene_id', params.gene_id)
  if (params.target_tissue) {
    sp.set('target_tissue', params.target_tissue)
  }
  if (params.min_score !== undefined && params.min_score > 0) {
    sp.set('min_score', String(params.min_score))
  }
  if (params.exclude_centromere) {
    sp.set('exclude_centromere', 'true')
  }
  if (params.region_type && params.region_type !== 'all') {
    sp.set('region_type', params.region_type)
  } else if (params.exon_only) {
    sp.set('exon_only', 'true')
  }
  if (params.page) sp.set('page', String(params.page))
  if (params.page_size) sp.set('page_size', String(params.page_size))
  if (params.sort_by) sp.set('sort_by', params.sort_by)
  if (params.sort_order) sp.set('sort_order', params.sort_order)

  const res = await fetch(`/api/v1/candidates?${sp.toString()}`)
  if (!res.ok) throw new Error('获取候选靶点失败')
  return res.json()
}

export const CandidateSearchPanel: React.FC = () => {
  const [selectedGeneId, setSelectedGeneId] = useState<string>('')
  const [selectedGuideId, setSelectedGuideId] = useState<string | null>(null)
  const [targetTissue, setTargetTissue] = useState<TargetTissue>('Leaf')
  const [minScore, setMinScore] = useState<number>(0)

  const [excludeCentromere, setExcludeCentromere] = useState<boolean>(false)
  const [includeExon, setIncludeExon] = useState<boolean>(true)
  const [includePromoter, setIncludePromoter] = useState<boolean>(true)
  const [sortBy, setSortBy] = useState<string>('priority_score')
  const [sortOrder, setSortOrder] = useState<string>('desc')
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
  const [isExporting, setIsExporting] = useState<boolean>(false)

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
    if (selectedCandidateIds.size === 0) return
    setIsExporting(true)
    try {
      const finalName = batchName.trim() || `${activeGeneId || 'gRNA'}_优选方案`
      const res = await fetch('/api/v1/exports', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: finalName,
          format,
          candidate_ids: Array.from(selectedCandidateIds),
          gene_id: activeGeneId || undefined,
        }),
      })
      if (!res.ok) throw new Error('创建导出批次失败')
      const data = await res.json()
      window.location.href = `/api/v1/exports/${data.id}/download`
    } catch (err: any) {
      alert(err.message || '导出错误')
    } finally {
      setIsExporting(false)
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
        gene_id: activeGeneId,
        target_tissue: targetTissue,
        min_score: minScore,
        exclude_centromere: excludeCentromere,
        region_type: currentRegionType,
        page,
        page_size: pageSize,
        sort_by: sortBy,
        sort_order: sortOrder,
      }),
    enabled: !!activeGeneId,
  })

  const currentGene = genes?.find((g) => g.gene_id === activeGeneId)
  const summary = candidatesData?.gene_summary

  const currentItems = candidatesData?.items || []
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
                          {filteredGenes.map((g) => {
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
                                    {g.chrom} · {g.nlr_type || 'NLR'} · {g.candidate_count} 候选位点
                                  </span>
                                </div>
                                {isSelected && (
                                  <Check className="h-4 w-4 text-emerald-600 shrink-0 ml-2" />
                                )}
                              </button>
                            )
                          })}
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
                setSortBy(e.target.value)
                setPage(1)
              }}
              className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-sm focus:border-emerald-500 focus:outline-none"
            >
              <option value="priority_score">组织优先指数（{TISSUE_NAMES[targetTissue]}）降序 · 方案3推荐</option>
              <option value="efficiency_score">效率分 (v2.1 推荐排序)</option>
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
            {isFetching && <span className="text-xs text-slate-400 animate-pulse">(更新中...)</span>}
          </div>
          <div className="text-xs text-slate-500">
            共匹配到 <strong className="text-emerald-600">{candidatesData?.total || 0}</strong> 条符合条件的靶点
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
                <th className="py-3 px-2">脱靶数 (&le;3)</th>
                <th className="py-3 px-3 text-right">组织优先 ({TISSUE_NAMES[targetTissue]})</th>
                <th className="py-3 px-3 text-right">功能危害 ({TISSUE_NAMES[targetTissue]})</th>
                <th className="py-3 px-3 text-center">表达证据</th>
                <th className="py-3 px-2">着丝粒</th>
                <th className="py-3 px-4 text-right">效率分 (v2.1)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {candidatesLoading ? (
                <tr>
                  <td colSpan={15} className="py-12 text-center text-slate-400">
                    <div className="flex items-center justify-center space-x-2">
                      <div className="h-4 w-4 animate-spin rounded-full border-2 border-emerald-600 border-t-transparent"></div>
                      <span>正在检索候选 gRNA 靶位点...</span>
                    </div>
                  </td>
                </tr>
              ) : !candidatesData?.items || candidatesData.items.length === 0 ? (
                <tr>
                  <td colSpan={15} className="py-12 text-center text-slate-500">
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
                      <td className="py-3 px-4 font-mono text-slate-700">
                        {cand.offtarget_count_mis3 === null || cand.offtarget_count_mis3 === undefined ? (
                          <span
                            className="text-slate-400"
                            title="未计算：未对该 guide 做全基因组脱靶扫描，不能读作'已验证无脱靶'"
                          >
                            未计算
                          </span>
                        ) : cand.offtarget_count_mis3 > 0 ? (
                          <span className="text-amber-600 font-semibold">{cand.offtarget_count_mis3}</span>
                        ) : (
                          <span className="text-emerald-600">0</span>
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
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => handleExport('csv')}
              disabled={isExporting}
              className="inline-flex items-center gap-1.5 rounded-xl bg-emerald-600 px-3.5 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-emerald-700 disabled:opacity-50 transition-colors"
            >
              <Download className="h-3.5 w-3.5" />
              <span>{isExporting ? '生成中...' : '导出 CSV'}</span>
            </button>

            <button
              onClick={() => handleExport('xlsx')}
              disabled={isExporting}
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 disabled:opacity-50 transition-colors"
            >
              <FileSpreadsheet className="h-3.5 w-3.5 text-emerald-600" />
              <span>{isExporting ? '生成中...' : '导出 Excel'}</span>
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
    </div>
  )
}
