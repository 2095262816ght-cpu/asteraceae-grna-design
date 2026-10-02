import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { DownloadButton } from './DownloadButton'
import {
  Download,
  FileSpreadsheet,
  History,
  AlertTriangle,
  XCircle,
  Loader2,
  RefreshCw,
  Sparkles,
  FileText,
  Clock,
  Layers,
  Trash2,
} from 'lucide-react'
import { Badge, Button, Card, Dialog, EmptyState, Spinner, Table, Tabs, Tbody, Td, Th, Thead, Tr } from './ui'
import { GeneratedIcon } from './icons/GeneratedIcon'

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

  // 删除确认（硬删除）：批次只删归档记录；作业连带逐条明细，算好的数据均保留
  const [deleteTarget, setDeleteTarget] = useState<
    { kind: 'batch' | 'job'; id: string; label: string; seqCount?: number } | null
  >(null)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const confirmDelete = async () => {
    if (!deleteTarget) return
    setDeleting(true)
    setDeleteError(null)
    try {
      const url =
        deleteTarget.kind === 'batch'
          ? `/api/v1/exports/${deleteTarget.id}`
          : `/api/v1/scoring/jobs/${deleteTarget.id}`
      const res = await fetch(url, { method: 'DELETE' })
      if (!res.ok) {
        const data = await res.json().catch(() => null)
        throw new Error(data?.detail || '删除失败，请稍后重试')
      }
      setDeleteTarget(null)
      if (deleteTarget.kind === 'batch') refetchExports()
      else refetchJobs()
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : '删除失败，请稍后重试')
    } finally {
      setDeleting(false)
    }
  }

  // 1. 获取导出批次列表
  const {
    data: exportBatches,
    isLoading: exportsLoading,
    isFetching: exportsFetching,
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
    isFetching: jobsFetching,
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
      <Card>
        <div className="flex flex-col gap-4 border-b border-line pb-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="flex items-center gap-2 text-lg font-bold text-ink">
              <History className="h-5 w-5 text-brand-600" />
              <span>实验设计成果导出批次与任务历史</span>
            </h2>
            <p className="mt-1 text-sm text-ink-muted">
              集中追踪所有筛选并固化的湿实验靶点方案、历史计算作业以及即时下载下单规格清单。
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button
              onClick={() => {
                refetchExports()
                refetchJobs()
              }}
              disabled={exportsFetching || jobsFetching}
            >
              <RefreshCw
                className={`h-3.5 w-3.5 text-ink-muted ${exportsFetching || jobsFetching ? 'animate-spin' : ''}`}
              />
              <span>刷新记录</span>
            </Button>
          </div>
        </div>

        {/* 概览统计指标 */}
        <div className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div className="glass-inner rounded-card p-3.5">
            <span className="flex items-center gap-1 text-xs text-ink-muted">
              <Layers className="h-3.5 w-3.5 text-brand-600" />
              <span>累计导出批次</span>
            </span>
            <p className="mt-1 text-xl font-bold text-ink">{exportBatches?.length ?? 0}</p>
          </div>
          <div className="glass-inner rounded-card p-3.5">
            <span className="flex items-center gap-1 text-xs text-ink-muted">
              <Sparkles className="h-3.5 w-3.5 text-sky-600" />
              <span>累计打分任务</span>
            </span>
            <p className="mt-1 text-xl font-bold text-ink">{scoringJobs?.length ?? 0}</p>
          </div>
          <div className="glass-inner rounded-card p-3.5">
            <span className="flex items-center gap-1 text-xs text-ink-muted">
              <GeneratedIcon name="checkCircle" className="h-3.5 w-3.5" />
              <span>计算成功率</span>
            </span>
            <p className="mt-1 text-xl font-bold text-brand-700">
              {scoringJobs && scoringJobs.length > 0
                ? `${Math.round(
                    (scoringJobs.filter((j) => j.status === 'completed').length /
                      scoringJobs.length) *
                      100
                  )}%`
                : '100%'}
            </p>
          </div>
          <div className="glass-inner rounded-card p-3.5">
            <span className="flex items-center gap-1 text-xs text-ink-muted">
              <Clock className="h-3.5 w-3.5 text-ink-muted" />
              <span>平均计算耗时</span>
            </span>
            <p className="mt-1 text-xl font-bold text-ink">
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
        <Tabs
          variant="underline"
          className="mt-6"
          value={activeSubTab}
          onChange={(id) => setActiveSubTab(id as 'exports' | 'jobs')}
          aria-label="历史记录分类"
          items={[
            {
              id: 'exports',
              icon: <Download className="h-4 w-4" />,
              label: <span>实验方案导出批次 ({exportBatches?.length || 0})</span>,
            },
            {
              id: 'jobs',
              icon: <History className="h-4 w-4" />,
              label: <span>算法计算作业履历 ({scoringJobs?.length || 0})</span>,
            },
          ]}
        />

        {/* 选项卡一：导出批次列表 */}
        {activeSubTab === 'exports' && (
          <div className="mt-4">
            {exportsLoading ? (
              <div className="flex items-center justify-center py-12">
                <Spinner label="加载导出批次中..." />
              </div>
            ) : !exportBatches || exportBatches.length === 0 ? (
              <EmptyState className="py-12">
                <div className="text-xs text-ink-faint">
                  暂无已保存的导出批次。请前往「候选靶点检索」勾选理想靶点并生成导出方案。
                </div>
              </EmptyState>
            ) : (
              <div className="overflow-x-auto rounded-card border border-line">
                <Table density="compact">
                  <caption className="sr-only">实验方案导出批次列表</caption>
                  <Thead>
                    <Tr hover={false}>
                      <Th>批次自定义名称</Th>
                      <Th>关联基因</Th>
                      <Th align="center">文件格式</Th>
                      <Th align="center">包含靶点数</Th>
                      <Th>创建时间</Th>
                      <Th align="right">操作</Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {exportBatches.map((batch) => (
                      <Tr key={batch.id}>
                        <Td>
                          <span className="flex items-center gap-2 font-medium text-ink">
                            <FileSpreadsheet className="h-4 w-4 text-brand-600" />
                            <span>{batch.name}</span>
                          </span>
                        </Td>
                        <Td className="font-mono text-ink-muted">{batch.gene_id || '--'}</Td>
                        <Td align="center">
                          <Badge
                            tone={batch.format === 'xlsx' ? 'success' : 'info'}
                            className="border font-mono text-2xs font-bold"
                          >
                            {batch.format}
                          </Badge>
                        </Td>
                        <Td align="center" numeric className="font-bold text-ink">
                          {batch.candidate_count}
                        </Td>
                        <Td className="font-mono text-2xs text-ink-muted">
                          {new Date(batch.created_at).toLocaleString()}
                        </Td>
                        <Td align="right" className="whitespace-nowrap">
                          <span className="inline-flex items-center gap-1.5">
                            <DownloadButton
                              url={`/api/v1/exports/${batch.id}/download`}
                              className="inline-flex items-center gap-1 rounded-control bg-brand-50 px-2.5 py-1 text-xs font-semibold text-brand-700 transition-colors hover:bg-brand-100 disabled:opacity-60"
                            >
                              下载文件
                            </DownloadButton>
                            <Button
                              variant="ghost"
                              onClick={() => {
                                setDeleteError(null)
                                setDeleteTarget({ kind: 'batch', id: batch.id, label: batch.name })
                              }}
                              title="删除该导出批次归档（已算好的候选数据保留）"
                              className="border border-rose-200 bg-rose-50 text-rose-700 hover:bg-rose-100"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                              删除
                            </Button>
                          </span>
                        </Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              </div>
            )}
          </div>
        )}

        {/* 选项卡二：模型打分作业履历 */}
        {activeSubTab === 'jobs' && (
          <div className="mt-4">
            {jobsLoading ? (
              <div className="flex items-center justify-center py-12">
                <Spinner label="加载打分历史中..." />
              </div>
            ) : !scoringJobs || scoringJobs.length === 0 ? (
              <EmptyState className="py-12">
                <div className="text-xs text-ink-faint">暂无打分作业记录。</div>
              </EmptyState>
            ) : (
              <div className="overflow-x-auto rounded-card border border-line">
                <Table density="compact">
                  <caption className="sr-only">模型打分作业履历列表</caption>
                  <Thead>
                    <Tr hover={false}>
                      <Th>任务标题 / 序列标识</Th>
                      <Th align="center">作业类型</Th>
                      <Th align="center">状态</Th>
                      <Th align="center">序列条数</Th>
                      <Th align="center">执行耗时</Th>
                      <Th>创建时间</Th>
                      <Th align="right">操作</Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {scoringJobs.map((job) => (
                      <Tr key={job.job_id}>
                        <Td>
                          <span className="flex items-center gap-2 font-medium text-ink">
                            {job.job_type === 'batch' ? (
                              <FileSpreadsheet className="h-4 w-4 text-brand-600" />
                            ) : (
                              <FileText className="h-4 w-4 text-sky-600" />
                            )}
                            <span>{job.title}</span>
                          </span>
                        </Td>
                        <Td align="center">
                          <Badge tone="neutral">{job.job_type === 'batch' ? '批量表格' : '单序列'}</Badge>
                        </Td>
                        <Td align="center">
                          {job.status === 'completed' && (
                            <span className="inline-flex items-center gap-1 text-2xs font-medium text-brand-700">
                              <GeneratedIcon name="checkCircle" className="h-3 w-3" />
                              <span>已完成</span>
                            </span>
                          )}
                          {job.status === 'running' && (
                            <span className="inline-flex items-center gap-1 text-2xs font-medium text-sky-700">
                              <Loader2 className="h-3 w-3 animate-spin" />
                              <span>运行中</span>
                            </span>
                          )}
                          {job.status === 'pending' && (
                            <span className="inline-flex items-center gap-1 text-2xs font-medium text-amber-700">
                              <AlertTriangle className="h-3 w-3" />
                              <span>排队中</span>
                            </span>
                          )}
                          {job.status === 'failed' && (
                            <span className="inline-flex items-center gap-1 text-2xs font-medium text-rose-700">
                              <XCircle className="h-3 w-3" />
                              <span>失败</span>
                            </span>
                          )}
                        </Td>
                        <Td align="center" numeric className="font-bold text-ink">
                          {job.total_sequences}
                        </Td>
                        <Td align="center" numeric className="font-mono text-ink-muted">
                          {job.duration_seconds}s
                        </Td>
                        <Td className="font-mono text-2xs text-ink-muted">
                          {new Date(job.created_at).toLocaleString()}
                        </Td>
                        <Td align="right" className="whitespace-nowrap">
                          <span className="inline-flex items-center gap-1.5">
                            <DownloadButton
                              url={`/api/v1/scoring/jobs/${job.job_id}/export?format=xlsx`}
                              className="inline-flex items-center gap-1 rounded-control border border-brand-200 bg-brand-50 px-2 py-1 text-2xs font-medium text-brand-700 transition-colors hover:bg-brand-100 disabled:opacity-60"
                              title="导出打分结果与多组学注释（缺啥写啥：缺失原因/所需数据/所用参考包/百分位口径）"
                            >
                              导出 (xlsx)
                            </DownloadButton>
                            <DownloadButton
                              url={`/api/v1/scoring/jobs/${job.job_id}/export?format=csv`}
                              className="inline-flex items-center gap-1 rounded-control border border-line px-2 py-1 text-2xs text-ink-muted transition-colors hover:bg-surface-sunken disabled:opacity-60"
                              title="CSV 格式导出（仅数据表）"
                            >
                              CSV
                            </DownloadButton>
                            <Button
                              variant="ghost"
                              onClick={() => {
                                setDeleteError(null)
                                setDeleteTarget({
                                  kind: 'job',
                                  id: job.job_id,
                                  label: job.title,
                                  seqCount: job.total_sequences,
                                })
                              }}
                              title="删除该作业及其逐条序列明细（已算好的脱靶/多组学结果保留）"
                              className="border border-rose-200 bg-rose-50 px-2 py-1 text-2xs text-rose-700 hover:bg-rose-100"
                            >
                              <Trash2 className="h-3 w-3" />
                              删除
                            </Button>
                          </span>
                        </Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              </div>
            )}
          </div>
        )}
      </Card>

      {/* 删除确认弹窗：硬删除，算好的数据不受影响 */}
      <Dialog
        open={deleteTarget !== null}
        onClose={() => setDeleteTarget(null)}
        title="确认删除？"
        size="sm"
        align="center"
        closePriority={3}
      >
        <div>
          <p className="px-5 pb-1 pt-4 text-2xs leading-relaxed text-ink-muted">
            将删除 <span className="font-semibold text-ink">{deleteTarget?.label}</span>
            {deleteTarget?.kind === 'job'
              ? ` 及其 ${deleteTarget.seqCount ?? 0} 条序列明细（不可恢复）`
              : ' 的导出归档记录（不可恢复）'}
            ；已算好的脱靶与多组学结果保留，不受影响。
          </p>
          {deleteError && (
            <div className="border-t border-line px-5 py-2.5 text-2xs text-rose-600">{deleteError}</div>
          )}
          <div className="flex justify-end gap-2 px-5 py-4">
            <Button onClick={() => setDeleteTarget(null)} disabled={deleting}>
              取消
            </Button>
            <Button variant="danger" onClick={confirmDelete} disabled={deleting} loading={deleting}>
              确认删除
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  )
}
export default ExportHistoryPanel
