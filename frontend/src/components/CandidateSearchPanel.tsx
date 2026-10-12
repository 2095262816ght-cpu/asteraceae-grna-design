import React, { Suspense, lazy, useCallback, useState, useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  computeOfftarget,
  fetchCandidates,
  fetchSortHelp,
  precomputeOfftargetForExport,
  type CandidateItem,
  type CandidatesResponse,
  type SortHelpItem,
} from '../lib/candidateQuery'
import { TISSUE_NAMES, TISSUE_ORDER, type TargetTissue } from '../lib/tissues'
import { useUrlSynced } from '../lib/urlState'
import { SORT_RECOMMENDED_ORDER } from '../lib/sortOrder'
import type {
  GeneExpressionData,
  GeneInfo,
  MethodsInfo,
  OfftargetSitesResponse,
} from '../lib/types'
// 基因组图谱按需加载：echarts 相关代码不阻塞首屏表格渲染
const GenomicTargetMap = lazy(() =>
  import('./GenomicTargetMap').then((m) => ({ default: m.GenomicTargetMap }))
)

// 稳定空数组：避免每次渲染生成新引用导致下游 memo 失效
const NO_ITEMS: CandidateItem[] = []
import { GeneCombobox } from './candidates/GeneCombobox'
import { TissueSelector } from './candidates/TissueSelector'
import { SortControl } from './candidates/SortControl'
import { FilterControls } from './candidates/FilterControls'
import { ExpressionDashboard } from './candidates/ExpressionDashboard'
import { CandidateTable } from './candidates/CandidateTable'
import { Spinner } from './ui'
import { ExportToolbar, type ExportProgress } from './candidates/ExportToolbar'
import { ComputeConfirmDialog } from './candidates/ComputeConfirmDialog'
import { SortHelpDialog } from './candidates/SortHelpDialog'
import { OfftargetDrawer } from './candidates/OfftargetDrawer'
import { MethodsDialog } from './candidates/MethodsDialog'

// 兼容 re-export：类型与常量的单一来源已迁至 lib/types、lib/tissues
export { TISSUE_NAMES, TISSUE_ORDER }
export type {
  GeneInfo,
  GeneExpressionData,
  OfftargetSite,
  OfftargetSitesResponse,
  MethodsInfo,
} from '../lib/types'

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

export const CandidateSearchPanel: React.FC = () => {
  // 筛选与视图状态进 URL（F5/分享不丢）；默认值不写入 URL，非法参数静默回落
  const [selectedGeneId, setSelectedGeneId] = useUrlSynced<string>({
    key: 'gene',
    defaultValue: '',
    parse: (raw) => (raw.trim() ? raw.trim() : null),
    serialize: (v) => (v === '' ? null : v),
    mode: 'push',
  })
  const [selectedGuideId, setSelectedGuideId] = useState<string | null>(null)
  const [targetTissue, setTargetTissue] = useUrlSynced<TargetTissue>({
    key: 'tissue',
    defaultValue: 'Leaf',
    parse: (raw) => (TISSUE_ORDER.includes(raw as TargetTissue) ? (raw as TargetTissue) : null),
    serialize: (v) => (v === 'Leaf' ? null : v),
  })
  const [minScore, setMinScore] = useUrlSynced<number>({
    key: 'min',
    defaultValue: 0,
    parse: (raw) => {
      const n = Number(raw)
      return Number.isFinite(n) && n >= 0 && n <= 90 ? n : null
    },
    serialize: (v) => (v === 0 ? null : String(v)),
  })

  const [excludeCentromere, setExcludeCentromere] = useUrlSynced<boolean>({
    key: 'cent',
    defaultValue: false,
    parse: (raw) =>
      raw === '1' || raw === 'true' ? true : raw === '0' || raw === 'false' ? false : null,
    serialize: (v) => (v ? '1' : null),
  })
  // 区域过滤：外显子/启动子勾选状态以单一 region 参数进出 URL
  const [region, setRegion] = useUrlSynced<'all' | 'exon' | 'promoter' | 'none'>({
    key: 'region',
    defaultValue: 'all',
    parse: (raw) =>
      raw === 'all' || raw === 'exon' || raw === 'promoter' || raw === 'none' ? raw : null,
    serialize: (v) => (v === 'all' ? null : v),
  })
  const includeExon = region === 'all' || region === 'exon'
  const includePromoter = region === 'all' || region === 'promoter'
  const setRegionFlags = (exon: boolean, promoter: boolean) =>
    setRegion(exon && promoter ? 'all' : exon ? 'exon' : promoter ? 'promoter' : 'none')
  const [sortBy, setSortBy] = useUrlSynced<string>({
    key: 'sort',
    defaultValue: 'efficiency_score',
    parse: (raw) => (raw in SORT_RECOMMENDED_ORDER ? raw : null),
    serialize: (v) => (v === 'efficiency_score' ? null : v),
  })
  const [sortOrder, setSortOrder] = useUrlSynced<string>({
    key: 'order',
    defaultValue: 'desc',
    parse: (raw) => (raw === 'asc' || raw === 'desc' ? raw : null),
    serialize: (v) => (v === 'desc' ? null : v),
  })
  const [showSortHelp, setShowSortHelp] = useState<boolean>(false)
  // 排序帮助条目取自后端（公式文案单点定义在 cs_pipeline.core.ranking_semantics）
  const [sortHelpItems, setSortHelpItems] = useState<SortHelpItem[]>([])
  const [page, setPage] = useUrlSynced<number>({
    key: 'page',
    defaultValue: 1,
    parse: (raw) => {
      const n = Number(raw)
      return Number.isInteger(n) && n >= 1 ? n : null
    },
    serialize: (v) => (v === 1 ? null : String(v)),
  })
  const pageSize = 20
  const currentRegionType = region

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
  const [exportProgress, setExportProgress] = useState<ExportProgress | null>(null)

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

  const handleSelectGene = (geneId: string) => {
    setSelectedGeneId(geneId)
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

  // 打开脱靶明细抽屉并按需拉取位点明细（seq20 无效 / 请求失败时优雅降级）
  const openOfftargetDrawer = useCallback(async (cand: CandidateItem) => {
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
  }, [])

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

  // 打开方法与版本弹窗（已加载则复用缓存，不重复请求）
  const openMethods = useCallback(async () => {
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
  }, [methodsData, methodsLoading])

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

  const currentItems = candidatesData?.items ?? NO_ITEMS
  const pendingScanCount = currentItems.filter(
    (c) => selectedCandidateIds.has(c.id) && (c.offtarget_count_mis3 === null || c.offtarget_count_mis3 === undefined)
  ).length
  const isAllCurrentSelected =
    currentItems.length > 0 && currentItems.every((c) => selectedCandidateIds.has(c.id))

  const toggleSelectAllCurrent = useCallback(() => {
    const next = new Set(selectedCandidateIds)
    if (isAllCurrentSelected) {
      currentItems.forEach((c) => next.delete(c.id))
    } else {
      currentItems.forEach((c) => next.add(c.id))
    }
    setSelectedCandidateIds(next)
  }, [selectedCandidateIds, isAllCurrentSelected, currentItems])

  const toggleSelectOne = useCallback(
    (id: number) => {
      const next = new Set(selectedCandidateIds)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      setSelectedCandidateIds(next)
    },
    [selectedCandidateIds]
  )

  const restoreRegions = useCallback(() => {
    setRegion('all')
    setPage(1)
  }, [setRegion, setPage])

  return (
    <div className="space-y-6">
      {/* 顶部控制栏：基因选择与多维过滤面板 */}
      <div className="card p-6">
        <div className="flex flex-col gap-5 border-b border-line pb-5 lg:flex-row lg:items-center lg:justify-between">
          <GeneCombobox
            genes={genes}
            genesLoading={genesLoading}
            activeGeneId={activeGeneId}
            onSelectGene={handleSelectGene}
          />
          <TissueSelector
            value={targetTissue}
            onChange={(t) => {
              setTargetTissue(t)
              setPage(1)
            }}
          />
          <SortControl
            targetTissue={targetTissue}
            sortBy={sortBy}
            sortOrder={sortOrder}
            onSortByChange={(v) => {
              setSortBy(v)
              const rec = SORT_RECOMMENDED_ORDER[v]
              if (rec) setSortOrder(rec)
              setPage(1)
            }}
            onSortOrderToggle={() => {
              setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')
              setPage(1)
            }}
            onOpenSortHelp={() => setShowSortHelp(true)}
          />
        </div>

        <FilterControls
          includeExon={includeExon}
          includePromoter={includePromoter}
          onRegionChange={(exon, promoter) => {
            setRegionFlags(exon, promoter)
            setPage(1)
          }}
          minScore={minScore}
          onMinScoreChange={(v) => {
            setMinScore(v)
            setPage(1)
          }}
          excludeCentromere={excludeCentromere}
          onExcludeCentromereChange={(v) => {
            setExcludeCentromere(v)
            setPage(1)
          }}
          currentGene={currentGene}
          filteredCandidates={summary?.filtered_candidates}
          totalCandidates={currentGene?.candidate_count}
        />
      </div>

      {/* 多组织表达看板与靶向适宜性诊断 (方案1 & 方案3联动) */}
      <ExpressionDashboard data={expressionData} loading={exprLoading} targetTissue={targetTissue} />

      {/* 基因组物理坐标 ECharts 交互分布图谱 (Ticket 03) */}
      <Suspense
        fallback={
          <div className="card flex items-center justify-center py-10">
            <Spinner label="加载基因组图谱…" />
          </div>
        }
      >
        <GenomicTargetMap
          gene={currentGene}
          candidates={candidatesData?.items ?? NO_ITEMS}
          selectedGuideId={selectedGuideId}
          onSelectCandidate={setSelectedGuideId}
        />
      </Suspense>

      {/* 候选靶点大表 */}
      <CandidateTable
        data={candidatesData}
        loading={candidatesLoading}
        isFetching={isFetching}
        page={page}
        pageSize={pageSize}
        targetTissue={targetTissue}
        currentRegionType={currentRegionType}
        selectedIds={selectedCandidateIds}
        selectedGuideId={selectedGuideId}
        computingIds={computingIds}
        isAllSelected={isAllCurrentSelected}
        onSelectGuide={setSelectedGuideId}
        onToggleOne={toggleSelectOne}
        onToggleAll={toggleSelectAllCurrent}
        onPage={setPage}
        onOpenMethods={openMethods}
        onOpenOfftarget={openOfftargetDrawer}
        onComputeConfirm={setComputeConfirm}
        onRestoreRegions={restoreRegions}
      />

      {/* 悬浮多选导出操作栏 */}
      {selectedCandidateIds.size > 0 && (
        <ExportToolbar
          selectedCount={selectedCandidateIds.size}
          batchName={batchName}
          onBatchNameChange={setBatchName}
          isExporting={isExporting}
          exportProgress={exportProgress}
          pendingScanCount={pendingScanCount}
          onExport={handleExport}
          onClear={() => setSelectedCandidateIds(new Set())}
        />
      )}

      {/* 计算脱靶确认框：点击"未计算"格弹出，确认后按需全基因组扫描并回填 */}
      {computeConfirm && (
        <ComputeConfirmDialog
          cand={computeConfirm}
          onCancel={() => setComputeConfirm(null)}
          onConfirm={confirmComputeOfftarget}
        />
      )}

      {/* 排序方式说明弹窗 */}
      <SortHelpDialog
        open={showSortHelp}
        onClose={() => setShowSortHelp(false)}
        items={sortHelpItems}
        sortBy={sortBy}
      />

      {/* 脱靶位点明细抽屉（教师反馈 #1）：点击"脱靶数"数字打开，按需加载 */}
      {offtargetCand && (
        <OfftargetDrawer
          cand={offtargetCand}
          data={offtargetData}
          loading={offtargetLoading}
          error={offtargetError}
          onClose={() => setOfftargetCand(null)}
        />
      )}

      {/* 方法与版本弹窗（教师反馈 #4/#5）：算法、版本、参数与参考基因组口径 */}
      <MethodsDialog
        open={showMethods}
        onClose={() => setShowMethods(false)}
        data={methodsData}
        loading={methodsLoading}
        error={methodsError}
      />
    </div>
  )
}
