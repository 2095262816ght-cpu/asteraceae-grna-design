import React, { useState, useRef } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  UploadCloud,
  FileSpreadsheet,
  Download,
  CheckCircle,
  AlertTriangle,
  XCircle,
  RefreshCw,
  Search,
  Loader2,
  FileCheck,
  Clock,
} from 'lucide-react'

export interface JobItemDetail {
  id: number
  custom_id: string | null
  seq30: string
  flank_5p: string | null
  guide_seq: string | null
  pam: string | null
  flank_3p: string | null
  gc_pct: number | null
  tm_c: number | null
  deepspcas9_score: number | null
  crispron_source: string | null
  efficiency_score: number | null
  is_valid: boolean
  error_message: string | null
}

export interface ScoringJobResponse {
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
  items: JobItemDetail[]
}

export const BatchUploadCard: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isDragOver, setIsDragOver] = useState(false)
  const [activeJobId, setActiveJobId] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [validityFilter, setValidityFilter] = useState<'all' | 'valid' | 'invalid'>('all')

  const fileInputRef = useRef<HTMLInputElement>(null)

  // 1. 文件上传 Mutation
  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData()
      formData.append('file', file)
      const res = await fetch('/api/v1/scoring/upload', {
        method: 'POST',
        body: formData,
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: '上传失败' }))
        throw new Error(err.detail || '文件解析或上传错误')
      }
      return res.json()
    },
    onSuccess: (data) => {
      setActiveJobId(data.job_id)
    },
  })

  // 2. 轮询获取任务状态机进度与结果
  const { data: jobData, refetch } = useQuery<ScoringJobResponse>({
    queryKey: ['scoring_job', activeJobId],
    queryFn: async () => {
      if (!activeJobId) throw new Error('No active job')
      const res = await fetch(`/api/v1/scoring/jobs/${activeJobId}`)
      if (!res.ok) throw new Error('获取任务详情失败')
      return res.json()
    },
    enabled: !!activeJobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      if (status === 'pending' || status === 'running') {
        return 1500 // 1.5s 动态轮询
      }
      return false
    },
  })

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(true)
  }

  const handleDragLeave = () => {
    setIsDragOver(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0]
      validateAndSetFile(file)
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndSetFile(e.target.files[0])
    }
  }

  const validateAndSetFile = (file: File) => {
    const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase()
    if (!['.csv', '.xlsx', '.xls'].includes(ext)) {
      alert('仅支持上传 CSV (.csv) 或 Excel (.xlsx, .xls) 表格文件')
      return
    }
    setSelectedFile(file)
  }

  const handleStartAnalysis = () => {
    if (!selectedFile) return
    uploadMutation.mutate(selectedFile)
  }

  const handleReset = () => {
    setSelectedFile(null)
    setActiveJobId(null)
    setSearchQuery('')
    uploadMutation.reset()
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const filteredItems = (jobData?.items || []).filter((item) => {
    if (validityFilter === 'valid' && !item.is_valid) return false
    if (validityFilter === 'invalid' && item.is_valid) return false
    if (!searchQuery.trim()) return true
    const q = searchQuery.toLowerCase().trim()
    const idMatch = (item.custom_id || '').toLowerCase().includes(q)
    const seqMatch = item.seq30.toLowerCase().includes(q)
    return idMatch || seqMatch
  })

  const validCount = (jobData?.items || []).filter((i) => i.is_valid).length
  const invalidCount = (jobData?.items || []).filter((i) => !i.is_valid).length

  return (
    <div className="space-y-6">
      {/* 头部标题与模板下载 */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <FileSpreadsheet className="h-5 w-5 text-emerald-600" />
              <span>批量 gRNA 序列上传与异步打分流水线</span>
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              支持上传百条以上 30bp 序列（.csv / .xlsx）。系统自动识别序列列与编号列，后台异步并发运行模型预测。
            </p>
          </div>

          {/* 模板下载按钮组 */}
          <div className="flex items-center gap-2">
            <a
              href="/api/v1/scoring/template?format=csv"
              download="grna_batch_template.csv"
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-100 transition-colors shadow-sm"
            >
              <Download className="h-3.5 w-3.5 text-slate-500" />
              <span>下载 CSV 模板</span>
            </a>
            <a
              href="/api/v1/scoring/template?format=xlsx"
              download="grna_batch_template.xlsx"
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-100 transition-colors shadow-sm"
            >
              <Download className="h-3.5 w-3.5 text-emerald-600" />
              <span>下载 Excel 模板</span>
            </a>
          </div>
        </div>

        {/* 文件上传区 (未上传或正在上传) */}
        {!activeJobId && (
          <div className="mt-6 space-y-4">
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`flex flex-col items-center justify-center rounded-2xl border-2 border-dashed p-8 text-center transition-all cursor-pointer ${
                isDragOver
                  ? 'border-emerald-500 bg-emerald-50/50'
                  : 'border-slate-200 bg-slate-50/50 hover:border-slate-300 hover:bg-slate-50'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv, .xlsx, .xls"
                onChange={handleFileChange}
                className="hidden"
              />
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white shadow-sm border border-slate-100 text-emerald-600 mb-3">
                <UploadCloud className="h-6 w-6" />
              </div>
              <p className="text-sm font-semibold text-slate-800">
                点击选择文件 或 将表格拖拽至此处
              </p>
              <p className="mt-1 text-xs text-slate-400">
                支持标准 UTF-8 CSV、Excel 2007+ (.xlsx) 或 Excel 97-2003 (.xls)
              </p>
            </div>

            {/* 已选文件信息与提交按钮 */}
            {selectedFile && (
              <div className="flex items-center justify-between rounded-xl border border-emerald-100 bg-emerald-50/60 p-4">
                <div className="flex items-center gap-3">
                  <FileCheck className="h-5 w-5 text-emerald-600" />
                  <div>
                    <p className="text-sm font-medium text-slate-900">{selectedFile.name}</p>
                    <p className="text-xs text-slate-500">
                      {(selectedFile.size / 1024).toFixed(1)} KB
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setSelectedFile(null)}
                    className="rounded-lg px-3 py-1.5 text-xs text-slate-500 hover:bg-slate-200/50 transition-colors"
                  >
                    取消
                  </button>
                  <button
                    onClick={handleStartAnalysis}
                    disabled={uploadMutation.isPending}
                    className="inline-flex items-center gap-1.5 rounded-xl bg-emerald-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-emerald-700 disabled:opacity-50 transition-colors"
                  >
                    {uploadMutation.isPending ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        <span>上传并排队中...</span>
                      </>
                    ) : (
                      <>
                        <CheckCircle className="h-4 w-4" />
                        <span>启动批处理流水线</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}

            {uploadMutation.isError && (
              <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs text-rose-700 flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 flex-shrink-0" />
                <span>{uploadMutation.error?.message || '文件上传或分析失败'}</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 任务状态卡片与进度条 (当有 activeJobId 时展示) */}
      {activeJobId && (
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-6">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b border-slate-100 pb-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-base font-bold text-slate-900">
                  {jobData?.title || '批量打分任务'}
                </span>
                {/* 状态 Badge */}
                {jobData?.status === 'pending' && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-700 border border-amber-200">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    任务排队中
                  </span>
                )}
                {jobData?.status === 'running' && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700 border border-blue-200">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    模型并发打分中
                  </span>
                )}
                {jobData?.status === 'completed' && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-700 border border-emerald-200">
                    <CheckCircle className="h-3 w-3" />
                    计算全部完成
                  </span>
                )}
                {jobData?.status === 'failed' && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2.5 py-0.5 text-xs font-medium text-rose-700 border border-rose-200">
                    <XCircle className="h-3 w-3" />
                    执行失败
                  </span>
                )}
              </div>
              <p className="mt-1 text-xs text-slate-400 font-mono">Job ID: {activeJobId}</p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => refetch()}
                className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs text-slate-600 hover:bg-slate-50 transition-colors"
                title="手动刷新状态"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                <span>刷新</span>
              </button>
              <button
                onClick={handleReset}
                className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-100 transition-colors"
              >
                上传新表格
              </button>
            </div>
          </div>

          {/* 进度条与动态百分比 */}
          <div className="space-y-2">
            <div className="flex justify-between text-xs text-slate-600 font-medium">
              <span>处理进度</span>
              <span>
                {jobData?.processed_sequences || 0} / {jobData?.total_sequences || 0} (
                {jobData?.progress_pct ?? 0}%)
              </span>
            </div>
            <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-100">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  jobData?.status === 'completed'
                    ? 'bg-emerald-500'
                    : jobData?.status === 'failed'
                    ? 'bg-rose-500'
                    : 'bg-emerald-600'
                }`}
                style={{ width: `${Math.min(100, Math.max(0, jobData?.progress_pct ?? 0))}%` }}
              />
            </div>
          </div>

          {/* 统计指标卡片 */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="rounded-xl border border-slate-100 bg-slate-50 p-3">
              <span className="text-xs text-slate-500">总序列数</span>
              <p className="mt-0.5 text-lg font-bold text-slate-900">
                {jobData?.total_sequences ?? 0}
              </p>
            </div>
            <div className="rounded-xl border border-emerald-100 bg-emerald-50/50 p-3">
              <span className="text-xs text-emerald-700 flex items-center gap-1">
                <CheckCircle className="h-3 w-3" />
                <span>合规有效序列</span>
              </span>
              <p className="mt-0.5 text-lg font-bold text-emerald-700">{validCount}</p>
            </div>
            <div className="rounded-xl border border-amber-100 bg-amber-50/50 p-3">
              <span className="text-xs text-amber-700 flex items-center gap-1">
                <AlertTriangle className="h-3 w-3" />
                <span>格式异常过滤</span>
              </span>
              <p className="mt-0.5 text-lg font-bold text-amber-700">{invalidCount}</p>
            </div>
            <div className="rounded-xl border border-slate-100 bg-slate-50 p-3">
              <span className="text-xs text-slate-500 flex items-center gap-1">
                <Clock className="h-3 w-3" />
                <span>耗时</span>
              </span>
              <p className="mt-0.5 text-lg font-bold text-slate-900">
                {jobData?.duration_seconds ? `${jobData.duration_seconds}s` : '--'}
              </p>
            </div>
          </div>

          {/* 结果表格展示 (当任务已完成或部分有结果时) */}
          {jobData?.items && jobData.items.length > 0 && (
            <div className="space-y-4 pt-2">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <span>检测结果明细清单</span>
                  <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-normal text-slate-600">
                    共 {filteredItems.length} 条
                  </span>
                </h3>

                {/* 搜索与过滤栏 */}
                <div className="flex flex-wrap items-center gap-2">
                  <div className="relative">
                    <Search className="pointer-events-none absolute left-2.5 top-2 h-3.5 w-3.5 text-slate-400" />
                    <input
                      type="text"
                      placeholder="搜索 ID 或序列..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="rounded-lg border border-slate-200 bg-white pl-8 pr-3 py-1.5 text-xs text-slate-800 placeholder-slate-400 focus:border-emerald-500 focus:outline-none"
                    />
                  </div>

                  <select
                    value={validityFilter}
                    onChange={(e) => setValidityFilter(e.target.value as any)}
                    className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-700 focus:border-emerald-500 focus:outline-none"
                  >
                    <option value="all">全部条目</option>
                    <option value="valid">仅合规条目</option>
                    <option value="invalid">仅异常条目</option>
                  </select>
                </div>
              </div>

              {/* 结果表格 */}
              <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-slate-200 bg-slate-50 text-slate-600">
                    <tr>
                      <th className="px-3 py-2.5 font-semibold">编号 / ID</th>
                      <th className="px-3 py-2.5 font-semibold">
                        30bp 靶点序列 (5'上游 - Guide - PAM - 3'下游)
                      </th>
                      <th className="px-3 py-2.5 font-semibold text-center">GC%</th>
                      <th className="px-3 py-2.5 font-semibold text-center">Tm (°C)</th>
                      <th className="px-3 py-2.5 font-semibold text-right">预测效率分</th>
                      <th className="px-3 py-2.5 font-semibold text-center">DeepSpCas9</th>
                      <th className="px-3 py-2.5 font-semibold text-center">状态 / 备注</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-mono">
                    {filteredItems.map((item) => (
                      <tr
                        key={item.id}
                        className={
                          item.is_valid
                            ? 'hover:bg-slate-50/80 transition-colors'
                            : 'bg-rose-50/40 text-rose-900 hover:bg-rose-50/70'
                        }
                      >
                        <td className="px-3 py-2.5 font-sans font-medium text-slate-800">
                          {item.custom_id || `Seq_${item.id}`}
                        </td>
                        <td className="px-3 py-2.5">
                          {item.is_valid && item.guide_seq && item.pam ? (
                            <span className="tracking-wider">
                              <span className="text-slate-400 font-sans text-[11px]">
                                {item.flank_5p}
                              </span>
                              <span className="font-bold text-emerald-700 bg-emerald-50 px-1 py-0.5 rounded mx-0.5">
                                {item.guide_seq}
                              </span>
                              <span className="font-bold text-rose-600 bg-rose-50 px-1 py-0.5 rounded mx-0.5">
                                {item.pam}
                              </span>
                              <span className="text-slate-400 font-sans text-[11px]">
                                {item.flank_3p}
                              </span>
                            </span>
                          ) : (
                            <span className="text-rose-600">{item.seq30}</span>
                          )}
                        </td>
                        <td className="px-3 py-2.5 text-center font-sans">
                          {item.gc_pct !== null ? `${item.gc_pct}%` : '--'}
                        </td>
                        <td className="px-3 py-2.5 text-center font-sans">
                          {item.tm_c !== null ? `${item.tm_c}` : '--'}
                        </td>
                        <td className="px-3 py-2.5 text-right font-sans">
                          {item.efficiency_score !== null ? (
                            <span
                              className={`inline-block font-bold rounded px-2 py-0.5 text-xs ${
                                item.efficiency_score >= 80
                                  ? 'bg-emerald-100 text-emerald-800'
                                  : item.efficiency_score >= 60
                                  ? 'bg-blue-100 text-blue-800'
                                  : 'bg-amber-100 text-amber-800'
                              }`}
                            >
                              {item.efficiency_score.toFixed(2)}
                            </span>
                          ) : (
                            <span className="text-slate-400">--</span>
                          )}
                        </td>
                        <td className="px-3 py-2.5 text-center font-sans">
                          {item.deepspcas9_score !== null ? item.deepspcas9_score.toFixed(2) : '--'}
                        </td>
                        <td className="px-3 py-2.5 text-center font-sans">
                          {item.is_valid ? (
                            <span className="inline-flex items-center gap-1 text-[11px] text-emerald-700">
                              <CheckCircle className="h-3 w-3" />
                              <span>{item.crispron_source === 'wsl_real' ? '真实模型' : '标准'}</span>
                            </span>
                          ) : (
                            <span
                              className="inline-flex items-center gap-1 text-[11px] text-rose-600"
                              title={item.error_message || '格式校验未通过'}
                            >
                              <XCircle className="h-3 w-3" />
                              <span>{item.error_message || '格式错误'}</span>
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
export default BatchUploadCard
