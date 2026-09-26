import React, { useMemo } from 'react'
import ReactECharts from 'echarts-for-react'
import type { CandidateItem, GeneInfo } from './CandidateSearchPanel'
import { MapPin, ZoomIn, Info } from 'lucide-react'

interface GenomicTargetMapProps {
  gene?: GeneInfo | null
  candidates: CandidateItem[]
  selectedGuideId?: string | null
  onSelectCandidate: (guideId: string) => void
}

export const GenomicTargetMap: React.FC<GenomicTargetMapProps> = ({
  gene,
  candidates,
  selectedGuideId,
  onSelectCandidate,
}) => {
  // 计算坐标范围 (基因区间前后留出 2% 边距)
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

  // ECharts 选项配置
  const option = useMemo(() => {
    if (!gene) return {}

    return {
      grid: {
        top: 40,
        bottom: 70,
        left: 90,
        right: 40,
      },
      tooltip: {
        trigger: 'item',
        formatter: (params: { data?: { cand?: CandidateItem } }) => {
          const c = params.data?.cand
          if (!c) return ''
          const eff = c.efficiency_score !== undefined && c.efficiency_score !== null ? c.efficiency_score.toFixed(2) : '未计算'
          return `
            <div style="font-size: 12px; line-height: 1.6; font-family: monospace;">
              <strong style="color: #0f172a; font-size: 13px;">${c.guide_id}</strong> (${c.strand} 链)<br/>
              <strong>物理坐标:</strong> ${c.start.toLocaleString()} - ${c.end.toLocaleString()}<br/>
              <strong>PAM:</strong> <span style="color: #059669; font-weight: bold;">${c.pam}</span> (${c.region_type})<br/>
              <strong>Guide (20nt):</strong> ${c.seq20}<br/>
              <strong>效率分 (v2.1):</strong> <span style="color: #0284c7; font-weight: bold;">${eff}</span><br/>
              <strong>脱靶数 (&le;3 mis):</strong> ${c.offtarget_count_mis3} | <strong>GC:</strong> ${c.gc_pct.toFixed(1)}%<br/>
              <span style="color: #64748b; font-size: 11px;">点击图上锚点可定位联动表格</span>
            </div>
          `
        },
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
        min: -1.8,
        max: 1.8,
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
            if (val === 1) return '+ 正向链'
            if (val === -1) return '- 反向链'
            if (val === 0) return '基因模型'
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
                { coord: [gene.start, 0] },
                { coord: [gene.end, 0] },
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
        // 2. 正向链靶点散点 (Y=1)
        {
          name: '正向链靶点',
          type: 'scatter',
          data: forwardPoints,
          cursor: 'pointer',
        },
        // 3. 反向链靶点散点 (Y=-1)
        {
          name: '反向链靶点',
          type: 'scatter',
          data: reversePoints,
          cursor: 'pointer',
        },
      ],
    }
  }, [gene, minCoord, maxCoord, forwardPoints, reversePoints])

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

      {/* ECharts 图表容器 */}
      <div className="mt-2">
        <ReactECharts
          option={option}
          onEvents={onChartEvents}
          style={{ height: '240px', width: '100%' }}
          opts={{ renderer: 'canvas' }}
        />
      </div>

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
