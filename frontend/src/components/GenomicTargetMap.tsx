import React, { useEffect, useMemo, useState } from 'react'
import ReactECharts from 'echarts-for-react'
import type { GeneInfo } from './CandidateSearchPanel'
import type { CandidateItem } from '../lib/candidateQuery'
import { MapPin, ZoomIn, Info, AlertTriangle } from 'lucide-react'

// ============ 基因结构 / 蛋白功能域注释类型（GET /api/v1/annotation/gene-structure） ============

export interface ProteinDomain {
  gene_id: string
  chrom: string
  start: number
  end: number
  strand: string
  domain_type: string // CC / TIR / NBS / LRR / Other
  domain_name?: string | null
  source?: string | null
}

export interface GeneStructureInfo {
  gene_id: string
  available: boolean
  bundle_id?: string
  chrom?: string
  start?: number
  end?: number
  strand?: string
  tss?: number | null
  exons?: Array<[number, number]>
  cds?: Array<[number, number]>
  transcripts?: string[]
  domains?: ProteinDomain[]
  domain_note?: string | null
  missing_requirements?: string[]
}

// 轨道配色（图例与轨道共用同一来源）
export const EXON_COLOR = '#38bdf8' // 外显子：天蓝
export const INTRON_COLOR = '#94a3b8' // 内含子：横线灰（细线，需与青色外显子块区分）
export const TSS_COLOR = '#f59e0b' // TSS：琥珀
export const DOMAIN_COLORS: Record<string, string> = {
  CC: '#3b82f6', // 蓝
  TIR: '#8b5cf6', // 紫
  NBS: '#ef4444', // 红
  LRR: '#22c55e', // 绿
  Other: '#94a3b8', // 灰
}

export function domainColor(domainType?: string | null): string {
  return DOMAIN_COLORS[domainType ?? ''] ?? DOMAIN_COLORS.Other
}

// ============ tooltip 文案（导出便于测试） ============

export interface MapTooltipItem {
  cand?: CandidateItem
  track?: 'exon' | 'intron' | 'tss' | 'domain'
  exon?: [number, number]
  isCds?: boolean
  intron?: [number, number]
  tss?: number
  domain?: ProteinDomain
}

function formatNumber(n: number): string {
  return n.toLocaleString()
}

export function formatMapTooltip(data?: MapTooltipItem): string {
  if (!data) return ''
  const c = data.cand
  if (c) {
    const eff =
      c.efficiency_score !== undefined && c.efficiency_score !== null
        ? c.efficiency_score.toFixed(2)
        : '未计算'
    return `
      <div style="font-size: 12px; line-height: 1.6; font-family: monospace;">
        <strong style="color: #0f172a; font-size: 13px;">${c.guide_id}</strong> (${c.strand} 链)<br/>
        <strong>物理坐标:</strong> ${formatNumber(c.start)} - ${formatNumber(c.end)}<br/>
        <strong>PAM:</strong> <span style="color: #059669; font-weight: bold;">${c.pam}</span> (${c.region_type})<br/>
        <strong>Guide (20nt):</strong> ${c.seq20}<br/>
        <strong>效率分 (v2.1):</strong> <span style="color: #0284c7; font-weight: bold;">${eff}</span><br/>
        <strong>脱靶数 (&le;3 mis):</strong> ${c.offtarget_count_mis3 ?? '未计算'} | <strong>GC:</strong> ${c.gc_pct.toFixed(1)}%<br/>
        <span style="color: #64748b; font-size: 11px;">点击图上锚点可定位联动表格</span>
      </div>
    `
  }
  if (data.track === 'exon' && data.exon) {
    const [s, e] = data.exon
    return `
      <div style="font-size: 12px; line-height: 1.6;">
        <strong style="color: #0369a1;">外显子 ${s}-${e}</strong>${data.isCds ? ' <span style="color:#0369a1;">(CDS)</span>' : ''}<br/>
        <span style="color:#64748b;">长度 ${e - s + 1} bp</span>
      </div>
    `
  }
  if (data.track === 'intron' && data.intron) {
    const [s, e] = data.intron
    return `
      <div style="font-size: 12px; line-height: 1.6;">
        <strong style="color: #64748b;">内含子 ${s}-${e}</strong><br/>
        <span style="color:#94a3b8;">长度 ${e - s} bp</span>
      </div>
    `
  }
  if (data.track === 'tss' && data.tss !== undefined) {
    return `
      <div style="font-size: 12px; line-height: 1.6;">
        <strong style="color: #b45309;">TSS 转录起始位点 ${data.tss}</strong>
      </div>
    `
  }
  if (data.track === 'domain' && data.domain) {
    const d = data.domain
    return `
      <div style="font-size: 12px; line-height: 1.6;">
        <strong style="color:${domainColor(d.domain_type)};">${d.domain_type}</strong>${
          d.domain_name ? ` · ${d.domain_name}` : ''
        }<br/>
        <span style="color:#64748b;">坐标 ${d.start}-${d.end}${d.source ? ` · 来源 ${d.source}` : ''}</span>
      </div>
    `
  }
  return ''
}

// ============ 组件 ============

interface GenomicTargetMapProps {
  gene?: GeneInfo | null
  candidates: CandidateItem[]
  selectedGuideId?: string | null
  onSelectCandidate: (guideId: string) => void
  /** 参考包 ID（默认 lettuce，调用方未传时按莴苣参考包请求基因结构注释） */
  bundleId?: string
}

interface StructureTrackItem {
  value: [number, number, number]
  track: 'exon' | 'intron' | 'domain'
  exon?: [number, number]
  isCds?: boolean
  intron?: [number, number]
  domain?: ProteinDomain
}

interface TssTrackItem {
  value: [number, number]
  track: 'tss'
  tss: number
}

interface RenderItemApi {
  value: (i: number) => number
  coord: (v: number[]) => number[]
}function overlapsCds(exon: [number, number], cds?: Array<[number, number]>): boolean {
  return (cds ?? []).some(([s, e]) => exon[0] <= e && exon[1] >= s)
}

export const GenomicTargetMap: React.FC<GenomicTargetMapProps> = ({
  gene,
  candidates,
  selectedGuideId,
  onSelectCandidate,
  bundleId = 'lettuce',
}) => {
  // ---- 基因结构 / 蛋白功能域注释按需请求（gene_id 变化时重新拉取，失败降级不崩溃） ----
  // 结果按 geneId 归档，gene 切换期间派生 loading，避免在 effect 内同步 setState
  const geneId = gene?.gene_id
  const [structureState, setStructureState] = useState<{
    geneId: string
    structure: GeneStructureInfo | null
    error: string | null
  } | null>(null)

  useEffect(() => {
    if (!geneId) return
    const controller = new AbortController()
    const url = `/api/v1/annotation/gene-structure?gene_id=${encodeURIComponent(
      geneId
    )}&bundle_id=${encodeURIComponent(bundleId)}`
    fetch(url, { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then((data) => {
        if (controller.signal.aborted) return
        setStructureState({ geneId, structure: data as GeneStructureInfo, error: null })
      })
      .catch(() => {
        if (controller.signal.aborted) return
        setStructureState({
          geneId,
          structure: null,
          error: '基因结构注释加载失败（接口不可用或缺 GFF 注释），已降级为基础基因图谱',
        })
      })
    return () => controller.abort()
  }, [geneId, bundleId])

  const matchedState = structureState && structureState.geneId === geneId ? structureState : null
  const structure = matchedState?.structure ?? null
  const structureError = matchedState?.error ?? null
  const structureLoading = Boolean(geneId) && (!structureState || structureState.geneId !== geneId)

  const hasTracks = structure?.available === true
  const exons: Array<[number, number]> = useMemo(
    () => ((structure?.exons ?? []) as Array<[number, number]>).slice().sort((a, b) => a[0] - b[0]),
    [structure]
  )
  const domains: ProteinDomain[] = useMemo(() => structure?.domains ?? [], [structure])

  // 计算坐标范围 (基因区间前后留出边距)
  const { minCoord, maxCoord, forwardPoints, reversePoints } = useMemo(() => {
    if (!gene) {
      return { minCoord: 0, maxCoord: 1000, forwardPoints: [], reversePoints: [] }
    }

    const margin = Math.max(500, Math.round((gene.end - gene.start) * 0.03))
    const minC = gene.start - margin
    const maxC = gene.end + margin

    const fwd: Array<{
      value: [number, number]
      guide_id: string
      cand: CandidateItem
      itemStyle: { color: string; borderColor?: string; borderWidth?: number }
      symbolSize: number
    }> = []

    const rev: Array<{
      value: [number, number]
      guide_id: string
      cand: CandidateItem
      itemStyle: { color: string; borderColor?: string; borderWidth?: number }
      symbolSize: number
    }> = []

    candidates.forEach((cand) => {
      const eff = cand.efficiency_score ?? 0
      const isSelected = selectedGuideId === cand.guide_id

      let pointColor = '#94a3b8' // < 40 slate
      if (eff >= 70) pointColor = '#10b981' // >= 70 emerald
      else if (eff >= 40) pointColor = '#f59e0b' // 40-70 amber

      const pointData = {
        value: [cand.start, cand.strand === '+' ? 1 : -1] as [number, number],
        guide_id: cand.guide_id,
        cand,
        itemStyle: {
          color: pointColor,
          borderColor: isSelected ? '#0284c7' : '#ffffff',
          borderWidth: isSelected ? 3 : 1,
        },
        symbolSize: isSelected ? 16 : Math.max(9, Math.min(14, 8 + (eff / 100) * 6)),
      }

      if (cand.strand === '+') {
        fwd.push(pointData)
      } else {
        rev.push(pointData)
      }
    })

    return {
      minCoord: minC,
      maxCoord: maxC,
      forwardPoints: fwd,
      reversePoints: rev,
    }
  }, [gene, candidates, selectedGuideId])

  // ---- 轨道行位（有注释时在基因条带下方展开基因结构 / 功能域两条轨道） ----
  const yFwd = 1
  const yGene = 0
  const yStruct = -1
  const yDomain = -2
  const yRev = hasTracks ? -3 : -1
  const yMin = hasTracks ? -3.6 : -1.8
  const yMax = 1.8

  // 轨道数据（与基因条带共用同一横轴比例尺）
  const { structureTrackData, domainTrackData, tssTrackData } = useMemo(() => {
    const structItems: StructureTrackItem[] = []
    const domainItems: StructureTrackItem[] = []
    const tssItems: TssTrackItem[] = []
    if (hasTracks && structure) {
      // 内含子：相邻外显子之间的细线
      for (let i = 0; i + 1 < exons.length; i += 1) {
        structItems.push({
          value: [exons[i][1], exons[i + 1][0], yStruct],
          track: 'intron',
          intron: [exons[i][1], exons[i + 1][0]],
        })
      }
      // 外显子：实心色块
      exons.forEach((ex) => {
        structItems.push({
          value: [ex[0], ex[1], yStruct],
          track: 'exon',
          exon: ex,
          isCds: overlapsCds(ex, structure.cds),
        })
      })
      // TSS：链感知箭头
      if (typeof structure.tss === 'number') {
        tssItems.push({ value: [structure.tss, yStruct], track: 'tss', tss: structure.tss })
      }
      // 蛋白功能域色块
      domains.forEach((d) => {
        domainItems.push({
          value: [d.start, d.end, yDomain],
          track: 'domain',
          domain: d,
        })
      })
    }
    return {
      structureTrackData: structItems,
      domainTrackData: domainItems,
      tssTrackData: tssItems,
    }
  }, [hasTracks, structure, exons, domains, yStruct, yDomain])

  // ECharts 选项配置
  const option = useMemo(() => {
    if (!gene) return {}

    const strand = structure?.strand ?? gene.strand
    const tss = structure?.tss

    // 轨道色块渲染器（外显子 / 内含子 / 功能域共用）。
    // ECharts 6 的 renderItem 拿不到 params.data（自定义字段如 track 会丢），
    // 故按 params.dataIndex 回查闭包中的数据项；tooltip 的 params.data 仍是原始对象。
    const renderTrackItem =
      (items: StructureTrackItem[]) =>
      (params: { dataIndex: number }, api: RenderItemApi): Record<string, unknown> => {
        const item = items[params.dataIndex]
        const startPt = api.coord([api.value(0), api.value(2)])
        const endPt = api.coord([api.value(1), api.value(2)])
        const width = Math.max(1.5, endPt[0] - startPt[0])
        if (item?.track === 'intron') {
          return {
            type: 'rect',
            shape: { x: startPt[0], y: startPt[1] - 1.5, width, height: 3 },
            style: { fill: INTRON_COLOR },
          }
        }
        const height = 14
        const isDomain = item?.track === 'domain'
        return {
          type: 'rect',
          shape: { x: startPt[0], y: startPt[1] - height / 2, width, height },
          style: {
            fill: isDomain ? domainColor(item?.domain?.domain_type) : EXON_COLOR,
            stroke: isDomain ? '#ffffff' : '#0284c7',
            lineWidth: 1,
          },
        }
      }

    return {
      grid: {
        top: 40,
        bottom: 70,
        left: 90,
        right: 40,
      },
      tooltip: {
        trigger: 'item',
        formatter: (params: { data?: MapTooltipItem }) => formatMapTooltip(params.data),
      },
      xAxis: {
        type: 'value',
        min: minCoord,
        max: maxCoord,
        axisLabel: {
          formatter: (val: number) => `${(val / 1000).toFixed(1)} kb`,
          color: '#64748b',
          fontSize: 11,
        },
        splitLine: {
          show: true,
          lineStyle: {
            color: '#f1f5f9',
            type: 'dashed',
          },
        },
      },
      yAxis: {
        type: 'value',
        min: yMin,
        max: yMax,
        interval: 1,
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: {
          show: true,
          lineStyle: {
            color: '#f8fafc',
          },
        },
        axisLabel: {
          formatter: (val: number) => {
            if (val === yFwd) return '+ 正向链'
            if (val === yGene) return '基因模型'
            if (hasTracks && val === yStruct) return '基因结构'
            if (hasTracks && val === yDomain) return '蛋白功能域'
            if (val === yRev) return '- 反向链'
            return ''
          },
          color: '#475569',
          fontSize: 11,
          fontWeight: 'bold',
        },
      },
      dataZoom: [
        {
          type: 'slider',
          show: true,
          xAxisIndex: [0],
          bottom: 12,
          height: 22,
          borderColor: '#e2e8f0',
          fillerColor: 'rgba(16, 185, 129, 0.15)',
          handleStyle: {
            color: '#10b981',
          },
          textStyle: {
            color: '#64748b',
            fontSize: 10,
          },
        },
        {
          type: 'inside',
          xAxisIndex: [0],
          zoomOnMouseWheel: true,
          moveOnMouseMove: true,
        },
      ],
      series: [
        // 1. 基因结构水平基准线 (中间 Y=0)
        {
          type: 'line',
          markLine: {
            silent: true,
            symbol: ['none', gene.strand === '+' ? 'arrow' : 'none'],
            lineStyle: {
              color: '#3b82f6',
              width: 5,
              type: 'solid',
            },
            data: [
              [
                { coord: [gene.start, yGene] },
                { coord: [gene.end, yGene] },
              ],
            ],
            label: {
              show: true,
              position: 'insideMiddleTop',
              formatter: `${gene.gene_id} (${gene.strand}) [${(gene.end - gene.start).toLocaleString()} bp]`,
              color: '#1e3a8a',
              fontSize: 11,
              fontWeight: 'bold',
            },
          },
        },
        // 2. 正向链靶点散点 (Y=+1)
        {
          name: '正向链靶点',
          type: 'scatter',
          data: forwardPoints,
          cursor: 'pointer',
        },
        // 3. 反向链靶点散点
        {
          name: '反向链靶点',
          type: 'scatter',
          data: reversePoints.map((p) => ({ ...p, value: [p.value[0], yRev] as [number, number] })),
          cursor: 'pointer',
        },
        // 4. 基因结构轨道：内含子细线 + 外显子实心块 (Y=-1)
        ...(hasTracks
          ? [
              {
                name: '基因结构轨道',
                type: 'custom',
                coordinateSystem: 'cartesian2d',
                renderItem: renderTrackItem(structureTrackData),
                clip: true,
                data: structureTrackData,
                tooltip: { trigger: 'item' },
              },
              // 5. TSS 标记（链感知箭头 + 竖线）
              {
                name: 'TSS',
                type: 'scatter',
                symbol: 'triangle',
                symbolRotate: strand === '-' ? -90 : 90,
                symbolSize: 18,
                data: tssTrackData.map((t) => ({
                  ...t,
                  itemStyle: { color: TSS_COLOR, borderColor: '#ffffff', borderWidth: 1 },
                })),
                markLine: {
                  silent: true,
                  symbol: ['none', 'none'],
                  lineStyle: { color: TSS_COLOR, width: 1.5, type: 'dashed' },
                  label: { show: false },
                  data:
                    typeof tss === 'number'
                      ? [
                          [
                            { coord: [tss, yStruct - 0.5] },
                            { coord: [tss, yStruct + 0.5] },
                          ],
                        ]
                      : [],
                },
              },
              // 6. 蛋白功能域轨道 (Y=-2)
              {
                name: '蛋白功能域轨道',
                type: 'custom',
                coordinateSystem: 'cartesian2d',
                renderItem: renderTrackItem(domainTrackData),
                clip: true,
                data: domainTrackData,
                tooltip: { trigger: 'item' },
              },
            ]
          : []),
      ],
    }
  }, [
    gene,
    minCoord,
    maxCoord,
    forwardPoints,
    reversePoints,
    hasTracks,
    structureTrackData,
    domainTrackData,
    tssTrackData,
    structure,
    yFwd,
    yGene,
    yStruct,
    yDomain,
    yRev,
    yMin,
    yMax,
  ])

  if (!gene) {
    return null
  }

  const onChartEvents = {
    click: (params: { data?: { guide_id?: string } }) => {
      if (params.data?.guide_id) {
        onSelectCandidate(params.data.guide_id)
      }
    },
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex flex-wrap items-center justify-between border-b border-slate-100 pb-4">
        <div className="flex items-center space-x-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-50 text-emerald-600">
            <MapPin className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-900">
              染色体物理分布交互图谱 ({gene.chrom} : {gene.start.toLocaleString()} - {gene.end.toLocaleString()})
            </h3>
            <p className="text-xs text-slate-500">
              正反链双轨渲染 · 基因骨架长度: {(gene.end - gene.start).toLocaleString()} bp · 当前匹配靶点: {candidates.length} 条
            </p>
          </div>
        </div>

        {/* 图例与操作提示 */}
        <div className="flex items-center space-x-4 text-xs">
          <div className="flex items-center space-x-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-500"></span>
            <span className="text-slate-600">高活性 (&ge;70)</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-amber-500"></span>
            <span className="text-slate-600">中等 (40-70)</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-slate-400"></span>
            <span className="text-slate-600">较低 (&lt;40)</span>
          </div>
          <div className="flex items-center space-x-1 text-slate-400 pl-2 border-l border-slate-200">
            <ZoomIn className="h-3.5 w-3.5" />
            <span>滚轮/下方滑块缩放</span>
          </div>
        </div>
      </div>

      {/* ECharts 图表容器（基因条带 + 基因结构轨道 + 功能域轨道 + gRNA 散点共用同一比例尺） */}
      <div className="mt-2">
        <ReactECharts
          option={option}
          onEvents={onChartEvents}
          style={{ height: hasTracks ? '360px' : '240px', width: '100%' }}
          opts={{ renderer: 'canvas' }}
        />
      </div>

      {/* 基因结构 / 蛋白功能域轨道图例与明细 */}
      {structureLoading && (
        <div className="mt-2 flex items-center space-x-2 text-xs text-slate-500">
          <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent"></div>
          <span>正在加载基因结构与蛋白功能域注释…</span>
        </div>
      )}

      {structureError && (
        <div className="mt-2 flex items-start space-x-1.5 text-xs text-amber-600">
          <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0 mt-0.5" />
          <span>{structureError}</span>
        </div>
      )}

      {structure && !structure.available && (
        <div className="mt-2 text-xs text-slate-500">
          基因结构注释暂不可用
          {structure.missing_requirements && structure.missing_requirements.length > 0
            ? `：补齐 ${structure.missing_requirements.join('、')} 后可显示外显子/功能域轨道`
            : '：该参考包缺少 GFF 基因结构注释'}
        </div>
      )}

      {hasTracks && (
        <div className="mt-3 space-y-2 border-t border-slate-100 pt-3">
          {/* 轨道图例 */}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs">
            <div className="flex items-center space-x-1.5">
              <span
                className="h-2.5 w-4 rounded-sm"
                style={{ backgroundColor: EXON_COLOR, border: '1px solid #0284c7' }}
              ></span>
              <span className="text-slate-600">外显子</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <span className="h-[3px] w-4" style={{ backgroundColor: INTRON_COLOR }}></span>
              <span className="text-slate-600">内含子</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <span
                className="h-0 w-0"
                style={{
                  borderLeft: '5px solid transparent',
                  borderRight: '5px solid transparent',
                  borderBottom: `8px solid ${TSS_COLOR}`,
                }}
              ></span>
              <span className="text-slate-600">TSS（转录起始位点）</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <span className="text-slate-600">结构域:</span>
              {domains.length > 0 ? (
                (['CC', 'TIR', 'NBS', 'LRR', 'Other'] as const).map((t) => (
                  <span key={t} className="flex items-center space-x-1">
                    <span
                      className="h-2.5 w-2.5 rounded-sm"
                      style={{ backgroundColor: DOMAIN_COLORS[t] }}
                    ></span>
                    <span className="text-slate-500">{t}</span>
                  </span>
                ))
              ) : (
                <span className="text-slate-400">该基因无功能域注释（图中无域色块）</span>
              )}
            </div>
          </div>

          {/* 外显子 / TSS 明细（hover 显示区间） */}
          <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
            <span className="text-slate-500">基因结构：</span>
            {exons.map((ex, i) => (
              <span
                key={`exon-${i}`}
                title={`外显子 ${ex[0]}-${ex[1]}`}
                className="cursor-help rounded border border-sky-200 bg-sky-50 px-1.5 py-0.5 font-mono text-sky-800"
              >
                外显子 {ex[0]}-{ex[1]}
              </span>
            ))}
            {typeof structure?.tss === 'number' && (
              <span
                title={`TSS 转录起始位点 ${structure.tss}`}
                className="cursor-help rounded border border-amber-200 bg-amber-50 px-1.5 py-0.5 font-mono text-amber-800"
              >
                TSS {structure.tss} ({structure.strand ?? gene.strand} 链)
              </span>
            )}
            {typeof structure?.transcripts !== 'undefined' && structure.transcripts.length > 0 && (
              <span className="text-slate-400">转录本: {structure.transcripts.join('、')}</span>
            )}
          </div>

          {/* 蛋白功能域轨道明细 */}
          <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
            <span className="text-slate-500">蛋白功能域：</span>
            {domains.length > 0 ? (
              domains.map((d, i) => (
                <span
                  key={`domain-${i}`}
                  title={`${d.domain_type}${d.domain_name ? ` · ${d.domain_name}` : ''} · ${d.start}-${d.end}`}
                  className="cursor-help rounded border px-1.5 py-0.5 font-mono"
                  style={{
                    color: domainColor(d.domain_type),
                    borderColor: domainColor(d.domain_type),
                    backgroundColor: `${domainColor(d.domain_type)}14`,
                  }}
                >
                  {d.domain_type}
                  {d.domain_name ? ` · ${d.domain_name}` : ''} · {d.start}-{d.end}
                </span>
              ))
            ) : (
              <span className="text-slate-400">
                暂无蛋白功能域注释
                {structure?.domain_note ? `（${structure.domain_note}）` : ''}
              </span>
            )}
          </div>
        </div>
      )}

      {selectedGuideId && (
        <div className="mt-2 flex items-center justify-between rounded-lg bg-sky-50 px-3.5 py-2 text-xs text-sky-800">
          <div className="flex items-center space-x-2">
            <Info className="h-4 w-4 text-sky-600" />
            <span>已聚焦靶点：<strong>{selectedGuideId}</strong></span>
          </div>
          <button
            onClick={() => onSelectCandidate('')}
            className="text-sky-600 hover:text-sky-900 font-medium"
          >
            取消聚焦
          </button>
        </div>
      )}
    </div>
  )
}
