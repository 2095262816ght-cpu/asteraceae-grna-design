import React from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  X,
  History,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Loader2,
  Clock,
  ArrowRight,
  FileSpreadsheet,
  Sparkles,
} from 'lucide-react'

export interface JobSummary {
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

interface HistoryDrawerProps {
  isOpen: boolean
  onClose: () => void
  onSelectJob?: (jobId: string) => void
}

export const HistoryDrawer: React.FC<HistoryDrawerProps> = ({
  isOpen,
  onClose,
  onSelectJob,
}) => {
  const { data: jobs, isLoading, refetch } = useQuery<JobSummary[]>({
    queryKey: ['scoring_jobs_history'],
    queryFn: async () => {
      const res = await fetch('/api/v1/scoring/jobs?limit=50')
      if (!res.ok) throw new Error('获取历史任务失败')
      return res.json()
    },
    enabled: isOpen,
  })

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/40 backdrop-blur-sm transition-opacity">
      <div className="fixed inset-y-0 right-0 flex max-w-full pl-10">
        <div className="w-screen max-w-md border-l border-slate-200 bg-white shadow-2xl flex flex-col">
          {/* 抽屉头部 */}
          <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
            <div className="flex items-center gap-2">
              <History className="h-5 w-5 text-emerald-600" />
              <h2 className="text-base font-bold text-slate-900">模型打分历史任务抽屉</h2>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => refetch()}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors"
                title="刷新历史"
              >
                <Clock className="h-4 w-4" />
              </button>
              <button
                onClick={onClose}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
          </div>

          {/* 抽屉主体列表 */}
          <div className="flex-1 overflow-y-auto p-6 space-y-3">
            {isLoading ? (
              <div className="flex items-center justify-center py-16 text-slate-400">
                <Loader2 className="h-6 w-6 animate-spin text-emerald-600" />
                <span className="ml-2 text-sm">正在加载过往打分任务...</span>
              </div>
            ) : !jobs || jobs.length === 0 ? (
              <div className="py-16 text-center text-slate-400 text-sm">
                暂无历史打分任务记录，可先在工作台提交单序列或批量序列打分。
              </div>
            ) : (
              jobs.map((job) => {
                const isCompleted = job.status === 'completed'
                const isFailed = job.status === 'failed'
                const isRunning = job.status === 'running'

                return (
                  <div
                    key={job.job_id}
                    onClick={() => {
                      if (onSelectJob) {
                        onSelectJob(job.job_id)
                        onClose()
                      }
                    }}
                    className={`group rounded-xl border p-4 transition-all cursor-pointer ${
                      onSelectJob ? 'hover:border-emerald-500 hover:shadow-md' : ''
                    } ${
                      isFailed
                        ? 'border-rose-200 bg-rose-50/30'
                        : 'border-slate-200 bg-white hover:bg-slate-50/50'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-2">
                        {job.job_type === 'batch' ? (
                          <FileSpreadsheet className="h-4 w-4 text-emerald-600" />
                        ) : (
                          <Sparkles className="h-4 w-4 text-sky-600" />
                        )}
                        <h4 className="text-xs font-bold text-slate-900 group-hover:text-emerald-700 transition-colors line-clamp-1">
                          {job.title}
                        </h4>
                      </div>

                      {/* 状态徽章 */}
                      {isCompleted && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-medium text-emerald-700 border border-emerald-200">
                          <CheckCircle className="h-3 w-3" />
                          已完成
                        </span>
                      )}
                      {isRunning && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2 py-0.5 text-[10px] font-medium text-blue-700 border border-blue-200">
                          <Loader2 className="h-3 w-3 animate-spin" />
                          运行中
                        </span>
                      )}
                      {job.status === 'pending' && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-medium text-amber-700 border border-amber-200">
                          <AlertTriangle className="h-3 w-3" />
                          排队中
                        </span>
                      )}
                      {isFailed && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2 py-0.5 text-[10px] font-medium text-rose-700 border border-rose-200">
                          <XCircle className="h-3 w-3" />
                          失败
                        </span>
                      )}
                    </div>

                    <div className="mt-3 flex items-center justify-between text-[11px] text-slate-500">
                      <span>序列数: {job.total_sequences} 条</span>
                      <span>耗时: {job.duration_seconds}s</span>
                    </div>

                    <div className="mt-2 flex items-center justify-between text-[10px] text-slate-400">
                      <span>{new Date(job.created_at).toLocaleString()}</span>
                      {onSelectJob && (
                        <span className="flex items-center gap-1 font-medium text-emerald-600 group-hover:translate-x-0.5 transition-transform">
                          <span>查看视图</span>
                          <ArrowRight className="h-3 w-3" />
                        </span>
                      )}
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
export default HistoryDrawer
