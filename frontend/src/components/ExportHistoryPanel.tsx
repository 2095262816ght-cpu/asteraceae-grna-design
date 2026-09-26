import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Download,
  FileSpreadsheet,
  History,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Loader2,
  RefreshCw,
  Sparkles,
  FileText,
  Clock,
  Layers,
} from 'lucide-react'

export interface ExportBatchItem {
  id: string
  name: string
  format: 'csv' | 'xlsx'
  gene_id: string | null
  candidate_count: number
  created_at: string
}

export interface ScoringJobSummaryItem {
  job_id: string
  title: string
  job_type: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  total_sequences: number
  processed_sequences: number
  progress_pct: number
  duration_seconds: number
  warning_message: string | null
  error_message: string | null
  created_at: string
  completed_at: string | null
}

export const ExportHistoryPanel: React.FC = () => {
  const [activeSubTab, setActiveSubTab] = useState<'exports' | 'jobs'>('exports')

  // 1. 获取导出批次列表
  const {
    data: exportBatches,
    isLoading: exportsLoading,
    refetch: refetchExports,
  } = useQuery<ExportBatchItem[]>({
    queryKey: ['export_batches'],
    queryFn: async () => {
      const res = await fetch('/api/v1/exports?limit=100')
      if (!res.ok) throw new Error('获取导出批次失败')
      return res.json()
    },
  })

  // 2. 获取打分作业列表
  const {
    data: scoringJobs,
    isLoading: jobsLoading,
    refetch: refetchJobs,
  } = useQuery<ScoringJobSummaryItem[]>({
    queryKey: ['scoring_jobs_history'],
    queryFn: async () => {
      const res = await fetch('/api/v1/scoring/jobs?limit=100')
      if (!res.ok) throw new Error('获取打分历史失败')
      return res.json()
    },
  })

  return (
    <div className="space-y-6">
      {/* 头部统计与导航 */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-100 pb-5">
          <div>
            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <History className="h-5 w-5 text-emerald-600" />
              <span>实验设计成果导出批次与任务历史</span>
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              集中追踪所有筛选并固化的湿实验靶点方案、历史计算作业以及即时下载下单规格清单。
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                refetchExports()
                refetchJobs()
              }}
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-100 transition-colors shadow-sm"
            >
              <RefreshCw className="h-3.5 w-3.5 text-slate-500" />
              <span>刷新记录</span>
            </button>
          </div>
        </div>

        {/* 概览统计指标 */}
        <div className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div className="rounded-xl border border-slate-100 bg-slate-50 p-3.5">
            <span className="text-xs text-slate-500 flex items-center gap-1">
              <Layers className="h-3.5 w-3.5 text-emerald-600" />
              <span>累计导出批次</span>
            </span>
            <p className="mt-1 text-xl font-bold text-slate-900">
              {exportBatches?.length ?? 0}
            </p>
          </div>
          <div className="rounded-xl border border-slate-100 bg-slate-50 p-3.5">
            <span className="text-xs text-slate-500 flex items-center gap-1">
              <Sparkles className="h-3.5 w-3.5 text-sky-600" />
              <span>累计打分任务</span>
            </span>
            <p className="mt-1 text-xl font-bold text-slate-900">
              {scoringJobs?.length ?? 0}
            </p>
          </div>
          <div className="rounded-xl border border-slate-100 bg-slate-50 p-3.5">
            <span className="text-xs text-slate-500 flex items-center gap-1">
              <CheckCircle className="h-3.5 w-3.5 text-emerald-600" />
              <span>计算成功率</span>
            </span>
            <p className="mt-1 text-xl font-bold text-emerald-700">
              {scoringJobs && scoringJobs.length > 0
                ? `${Math.round(
                    (scoringJobs.filter((j) => j.status === 'completed').length /
                      scoringJobs.length) *
                      100
                  )}%`
                : '100%'}
            </p>
          </div>
          <div className="rounded-xl border border-slate-100 bg-slate-50 p-3.5">
            <span className="text-xs text-slate-500 flex items-center gap-1">
              <Clock className="h-3.5 w-3.5 text-slate-500" />
              <span>平均计算耗时</span>
            </span>
            <p className="mt-1 text-xl font-bold text-slate-900">
              {scoringJobs && scoringJobs.length > 0
                ? `${(
                    scoringJobs.reduce((acc, cur) => acc + (cur.duration_seconds || 0), 0) /
                    scoringJobs.length
                  ).toFixed(1)}s`
                : '--'}
            </p>
          </div>
        </div>

        {/* 二级切换标签 */}
        <div className="mt-6 flex border-b border-slate-200">
          <button
            onClick={() => setActiveSubTab('exports')}
            className={`inline-flex items-center gap-2 border-b-2 px-4 py-2.5 text-xs font-semibold transition-all ${
              activeSubTab === 'exports'
                ? 'border-emerald-600 text-emerald-700'
                : 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-800'
            }`}
          >
            <Download className="h-4 w-4" />
            <span>实验方案导出批次 ({exportBatches?.length || 0})</span>
          </button>
          <button
            onClick={() => setActiveSubTab('jobs')}
            className={`inline-flex items-center gap-2 border-b-2 px-4 py-2.5 text-xs font-semibold transition-all ${
              activeSubTab === 'jobs'
                ? 'border-emerald-600 text-emerald-700'
                : 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-800'
            }`}
          >
            <History className="h-4 w-4" />
            <span>算法计算作业履历 ({scoringJobs?.length || 0})</span>
          </button>
        </div>

        {/* 选项卡一：导出批次列表 */}
        {activeSubTab === 'exports' && (
          <div className="mt-4">
            {exportsLoading ? (
              <div className="flex items-center justify-center py-12 text-slate-400">
                <Loader2 className="h-5 w-5 animate-spin text-emerald-600" />
                <span className="ml-2 text-xs">加载导出批次中...</span>
              </div>
            ) : !exportBatches || exportBatches.length === 0 ? (
              <div className="py-12 text-center text-slate-400 text-xs">
                暂无已保存的导出批次。请前往「候选靶点检索」勾选理想靶点并生成导出方案。
              </div>
            ) : (
              <div className="overflow-x-auto rounded-xl border border-slate-200">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-slate-200 bg-slate-50 text-slate-600">
                    <tr>
                      <th className="px-4 py-3 font-semibold">批次自定义名称</th>
                      <th className="px-4 py-3 font-semibold">关联基因</th>
                      <th className="px-4 py-3 font-semibold text-center">文件格式</th>
                      <th className="px-4 py-3 font-semibold text-center">包含靶点数</th>
                      <th className="px-4 py-3 font-semibold">创建时间</th>
                      <th className="px-4 py-3 font-semibold text-right">下载操作</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {exportBatches.map((batch) => (
                      <tr key={batch.id} className="hover:bg-slate-50/70 transition-colors">
                        <td className="px-4 py-3 font-medium text-slate-900 flex items-center gap-2">
                          <FileSpreadsheet className="h-4 w-4 text-emerald-600" />
                          <span>{batch.name}</span>
                        </td>
                        <td className="px-4 py-3 font-mono text-slate-600">
                          {batch.gene_id || '--'}
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span
                            className={`rounded px-2 py-0.5 text-[11px] font-mono font-bold uppercase ${
                              batch.format === 'xlsx'
                                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                : 'bg-sky-50 text-sky-700 border border-sky-200'
                            }`}
                          >
                            {batch.format}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-center font-bold text-slate-800">
                          {batch.candidate_count}
                        </td>
                        <td className="px-4 py-3 text-slate-500 font-mono text-[11px]">
                          {new Date(batch.created_at).toLocaleString()}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <a
                            href={`/api/v1/exports/${batch.id}/download`}
                            download
                            className="inline-flex items-center gap-1 rounded-lg bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700 hover:bg-emerald-100 transition-colors"
                          >
                            <Download className="h-3.5 w-3.5" />
                            <span>下载文件</span>
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* 选项卡二：模型打分作业履历 */}
        {activeSubTab === 'jobs' && (
          <div className="mt-4">
            {jobsLoading ? (
              <div className="flex items-center justify-center py-12 text-slate-400">
                <Loader2 className="h-5 w-5 animate-spin text-emerald-600" />
                <span className="ml-2 text-xs">加载打分历史中...</span>
              </div>
            ) : !scoringJobs || scoringJobs.length === 0 ? (
              <div className="py-12 text-center text-slate-400 text-xs">
                暂无打分作业记录。
              </div>
            ) : (
              <div className="overflow-x-auto rounded-xl border border-slate-200">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-slate-200 bg-slate-50 text-slate-600">
                    <tr>
                      <th className="px-4 py-3 font-semibold">任务标题 / 序列标识</th>
                      <th className="px-4 py-3 font-semibold text-center">作业类型</th>
                      <th className="px-4 py-3 font-semibold text-center">状态</th>
                      <th className="px-4 py-3 font-semibold text-center">序列条数</th>
                      <th className="px-4 py-3 font-semibold text-center">执行耗时</th>
                      <th className="px-4 py-3 font-semibold">创建时间</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {scoringJobs.map((job) => (
                      <tr key={job.job_id} className="hover:bg-slate-50/70 transition-colors">
                        <td className="px-4 py-3 font-medium text-slate-900 flex items-center gap-2">
                          {job.job_type === 'batch' ? (
                            <FileSpreadsheet className="h-4 w-4 text-emerald-600" />
                          ) : (
                            <FileText className="h-4 w-4 text-sky-600" />
                          )}
                          <span>{job.title}</span>
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600">
                            {job.job_type === 'batch' ? '批量表格' : '单序列'}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-center">
                          {job.status === 'completed' && (
                            <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-700">
                              <CheckCircle className="h-3 w-3" />
                              <span>已完成</span>
                            </span>
                          )}
                          {job.status === 'running' && (
                            <span className="inline-flex items-center gap-1 text-[11px] font-medium text-blue-700">
                              <Loader2 className="h-3 w-3 animate-spin" />
                              <span>运行中</span>
                            </span>
                          )}
                          {job.status === 'pending' && (
                            <span className="inline-flex items-center gap-1 text-[11px] font-medium text-amber-700">
                              <AlertTriangle className="h-3 w-3" />
                              <span>排队中</span>
                            </span>
                          )}
                          {job.status === 'failed' && (
                            <span className="inline-flex items-center gap-1 text-[11px] font-medium text-rose-700">
                              <XCircle className="h-3 w-3" />
                              <span>失败</span>
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-center font-bold text-slate-800">
                          {job.total_sequences}
                        </td>
                        <td className="px-4 py-3 text-center font-mono text-slate-600">
                          {job.duration_seconds}s
                        </td>
                        <td className="px-4 py-3 text-slate-500 font-mono text-[11px]">
                          {new Date(job.created_at).toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
export default ExportHistoryPanel
