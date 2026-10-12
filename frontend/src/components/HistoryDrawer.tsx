import React from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  History,
  AlertTriangle,
  XCircle,
  Loader2,
  RefreshCw,
  ArrowRight,
  FileSpreadsheet,
  Sparkles,
} from 'lucide-react'
import { Badge, Drawer, EmptyState, Spinner } from './ui'
import { GeneratedIcon } from './icons/GeneratedIcon'

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
  const { data: jobs, isLoading, refetch, isFetching } = useQuery<JobSummary[]>({
    queryKey: ['scoring_jobs_history'],
    queryFn: async () => {
      const res = await fetch('/api/v1/scoring/jobs?limit=50')
      if (!res.ok) throw new Error('获取历史任务失败')
      return res.json()
    },
    enabled: isOpen,
  })

  return (
    <Drawer
      open={isOpen}
      onClose={onClose}
      width="max-w-md"
      title={
        <span className="flex items-center gap-2">
          <History className="h-5 w-5 text-brand-600" />
          模型打分历史任务抽屉
        </span>
      }
      actions={
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="rounded-control p-1.5 text-ink-faint transition-colors hover:bg-surface-sunken hover:text-ink-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40 disabled:opacity-50"
          title="刷新历史"
        >
          <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
        </button>
      }
    >
      <div className="space-y-3 p-6">
        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <Spinner label="正在加载过往打分任务..." />
          </div>
        ) : !jobs || jobs.length === 0 ? (
          <EmptyState className="py-16">
            <div className="text-sm text-ink-faint">
              暂无历史打分任务记录，可先在工作台提交单序列或批量序列打分。
            </div>
          </EmptyState>
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
                className={`group cursor-pointer glass-inner rounded-card p-4 transition-all ${
                  onSelectJob ? 'hover:border-brand-500 hover:shadow-md' : ''
                } ${
                  isFailed
                    ? 'border-rose-200 bg-rose-50/30'
                    : 'hover:bg-white/25'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    {job.job_type === 'batch' ? (
                      <FileSpreadsheet className="h-4 w-4 text-brand-600" />
                    ) : (
                      <Sparkles className="h-4 w-4 text-sky-600" />
                    )}
                    <h4 className="line-clamp-1 text-xs font-bold text-ink transition-colors group-hover:text-brand-700">
                      {job.title}
                    </h4>
                  </div>

                  {isCompleted && (
                    <Badge tone="success" className="gap-1 border border-emerald-200 text-[10px]">
                      <GeneratedIcon name="checkCircle" className="h-3 w-3" />
                      已完成
                    </Badge>
                  )}
                  {isRunning && (
                    <Badge tone="info" className="gap-1 border border-sky-200 text-[10px]">
                      <Loader2 className="h-3 w-3 animate-spin" />
                      运行中
                    </Badge>
                  )}
                  {job.status === 'pending' && (
                    <Badge tone="warning" className="gap-1 border border-amber-200 text-[10px]">
                      <AlertTriangle className="h-3 w-3" />
                      排队中
                    </Badge>
                  )}
                  {isFailed && (
                    <Badge tone="danger" className="gap-1 border border-rose-200 text-[10px]">
                      <XCircle className="h-3 w-3" />
                      失败
                    </Badge>
                  )}
                </div>

                <div className="mt-3 flex items-center justify-between text-2xs text-ink-muted">
                  <span>序列数: {job.total_sequences} 条</span>
                  <span>耗时: {job.duration_seconds}s</span>
                </div>

                <div className="mt-2 flex items-center justify-between text-[10px] text-ink-faint">
                  <span>{new Date(job.created_at).toLocaleString()}</span>
                  {onSelectJob && (
                    <span className="flex items-center gap-1 font-medium text-brand-600 transition-transform group-hover:translate-x-0.5">
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
    </Drawer>
  )
}
export default HistoryDrawer
