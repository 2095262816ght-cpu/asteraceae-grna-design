import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ArrowUpDown, ChevronLeft, ChevronRight, Dna } from 'lucide-react'


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
  const [minScore, setMinScore] = useState<number>(0)
  const [excludeCentromere, setExcludeCentromere] = useState<boolean>(false)
  const [exonOnly, setExonOnly] = useState<boolean>(false)
  const [sortBy, setSortBy] = useState<string>('efficiency_score')
  const [sortOrder, setSortOrder] = useState<string>('desc')
  const [page, setPage] = useState<number>(1)
  const pageSize = 20

  // 1. 获取基因列表
  const { data: genes, isLoading: genesLoading } = useQuery<GeneInfo[]>({
    queryKey: ['genes'],
    queryFn: fetchGenes,
  })

  // 如果没有选定基因，默认选择第一个
  const activeGeneId = selectedGeneId || (genes && genes.length > 0 ? genes[0].gene_id : '')

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

  return (
    <div className="space-y-6">
      {/* 顶部控制栏：基因选择与多维过滤面板 */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between border-b border-slate-100 pb-5">
          {/* 基因选择器 */}
          <div className="flex flex-1 items-center space-x-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600">
              <Dna className="h-5 w-5" />
            </div>
            <div>
              <label htmlFor="gene-select" className="block text-xs font-semibold text-slate-500 uppercase tracking-wider">
                选择靶基因 (49 个 NLR 代表基因)
              </label>
              {genesLoading ? (
                <div className="mt-1 h-9 w-64 animate-pulse rounded-lg bg-slate-100"></div>
              ) : (
                <select
                  id="gene-select"
                  value={activeGeneId}
                  onChange={(e) => {
                    setSelectedGeneId(e.target.value)
                    setPage(1)
                  }}
                  className="mt-1 block w-72 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-800 shadow-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                >
                  {genes?.map((g) => (
                    <option key={g.gene_id} value={g.gene_id}>
                      {g.gene_id} ({g.chrom}, {g.nlr_type || 'NLR'}, {g.candidate_count} 靶点)
                    </option>
                  ))}
                </select>
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
                  <td colSpan={11} className="py-12 text-center text-slate-400">
                    <div className="flex items-center justify-center space-x-2">
                      <div className="h-4 w-4 animate-spin rounded-full border-2 border-emerald-600 border-t-transparent"></div>
                      <span>正在检索候选 gRNA 靶位点...</span>
                    </div>
                  </td>
                </tr>
              ) : !candidatesData?.items || candidatesData.items.length === 0 ? (
                <tr>
                  <td colSpan={11} className="py-12 text-center text-slate-400">
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

                  return (
                    <tr key={cand.id} className="hover:bg-slate-50/70 transition-colors">
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
    </div>
  )
}
