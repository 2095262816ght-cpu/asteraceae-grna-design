import React, { useState, useMemo, useRef, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ArrowUpDown, Check, ChevronDown, ChevronLeft, ChevronRight, Dna, Download, FileSpreadsheet, Search, X } from 'lucide-react'
import { GenomicTargetMap } from './GenomicTargetMap'



export interface GeneInfo {
  gene_id: string
  chrom: string
  start: number
  end: number
  strand: string
  nlr_type?: string
  candidate_count: number
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
  offtarget_count_mis3: number
  deepspcas9_score?: number
  crispron_score?: number
  efficiency_score?: number
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

async function fetchCandidates(params: {
  gene_id: string
  min_score?: number
  exclude_centromere?: boolean
  exon_only?: boolean
  page?: number
  page_size?: number
  sort_by?: string
  sort_order?: string
}): Promise<CandidatesResponse> {
  const sp = new URLSearchParams()
  sp.set('gene_id', params.gene_id)
  if (params.min_score !== undefined && params.min_score > 0) {
    sp.set('min_score', String(params.min_score))
  }
  if (params.exclude_centromere) {
    sp.set('exclude_centromere', 'true')
  }
  if (params.exon_only) {
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
  const [minScore, setMinScore] = useState<number>(0)

  const [excludeCentromere, setExcludeCentromere] = useState<boolean>(false)
  const [exonOnly, setExonOnly] = useState<boolean>(false)
  const [sortBy, setSortBy] = useState<string>('efficiency_score')
  const [sortOrder, setSortOrder] = useState<string>('desc')
  const [page, setPage] = useState<number>(1)
  const pageSize = 20

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
      minScore,
      excludeCentromere,
      exonOnly,
      page,
      sortBy,
      sortOrder,
    ],
    queryFn: () =>
      fetchCandidates({
        gene_id: activeGeneId,
        min_score: minScore,
        exclude_centromere: excludeCentromere,
        exon_only: exonOnly,
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
                  选择靶基因 (即输即搜 · 49 个 NLR 代表基因)
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
                        <span>{geneSearchInput ? `匹配结果 (${filteredGenes.length})` : `全部 49 个 NLR 基因`}</span>
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
              <option value="efficiency_score">效率分 (v2.1 推荐排序)</option>
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

        {/* 过滤控制栏 */}
        <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-3 items-center">
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

          {/* 仅限外显子开关 */}
          <div className="flex items-center space-x-2.5">
            <input
              type="checkbox"
              id="exon-only"
              checked={exonOnly}
              onChange={(e) => {
                setExonOnly(e.target.checked)
                setPage(1)
              }}
              className="h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
            />
            <label htmlFor="exon-only" className="text-xs font-medium text-slate-700 cursor-pointer">
              仅限外显子 / 编码区 (Exon / CDS Only)
            </label>
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
                <th className="py-3 px-4">#</th>
                <th className="py-3 px-4">靶点 ID</th>
                <th className="py-3 px-4">方向</th>
                <th className="py-3 px-4">基因组物理坐标</th>
                <th className="py-3 px-4">区域</th>
                <th className="py-3 px-4 font-mono">30nt 靶位点序列 (Guide + PAM)</th>
                <th className="py-3 px-4">PAM</th>
                <th className="py-3 px-4">GC %</th>
                <th className="py-3 px-4">脱靶数 (&le;3)</th>
                <th className="py-3 px-4">着丝粒</th>
                <th className="py-3 px-4 text-right">效率分 (v2.1)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {candidatesLoading ? (
                <tr>
                  <td colSpan={12} className="py-12 text-center text-slate-400">
                    <div className="flex items-center justify-center space-x-2">
                      <div className="h-4 w-4 animate-spin rounded-full border-2 border-emerald-600 border-t-transparent"></div>
                      <span>正在检索候选 gRNA 靶位点...</span>
                    </div>
                  </td>
                </tr>
              ) : !candidatesData?.items || candidatesData.items.length === 0 ? (
                <tr>
                  <td colSpan={12} className="py-12 text-center text-slate-400">
                    未找到符合当前过滤条件的候选 gRNA 靶点，请尝试降低最低效率分限制或关闭过滤项。
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
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-slate-100 text-slate-700">
                          {cand.region_type}
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
                        {cand.offtarget_count_mis3 > 0 ? (
                          <span className="text-amber-600 font-semibold">{cand.offtarget_count_mis3}</span>
                        ) : (
                          <span className="text-emerald-600">0</span>
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
