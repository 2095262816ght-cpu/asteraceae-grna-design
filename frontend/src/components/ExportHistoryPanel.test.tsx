import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ExportHistoryPanel } from './ExportHistoryPanel'

describe('ExportHistoryPanel', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    })
    vi.restoreAllMocks()
  })

  it('renders export batches and switches to jobs history subtab', async () => {
    const user = userEvent.setup()

    const mockBatches = [
      {
        id: 'batch-1234-uuid',
        name: 'LsaT2T01G023690 重点候选',
        format: 'csv',
        gene_id: 'LsaT2T01G023690',
        candidate_count: 5,
        created_at: new Date().toISOString(),
      },
    ]

    const mockJobs = [
      {
        job_id: 'job-5678-uuid',
        title: '测试单打分 (TGGATTCC...)',
        job_type: 'single',
        status: 'completed',
        total_sequences: 1,
        processed_sequences: 1,
        progress_pct: 100.0,
        duration_seconds: 0.8,
        warning_message: null,
        error_message: null,
        created_at: new Date().toISOString(),
        completed_at: new Date().toISOString(),
      },
    ]

    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/export?')) {
        return {
          ok: true,
          headers: new Headers({ 'Content-Disposition': 'attachment; filename="export.xlsx"' }),
          blob: async () => new Blob(['x']),
        } as unknown as Response
      }
      if (url.includes('/api/v1/exports')) {
        return {
          ok: true,
          json: async () => mockBatches,
        } as Response
      }
      if (url.includes('/api/v1/scoring/jobs')) {
        return {
          ok: true,
          json: async () => mockJobs,
        } as Response
      }
      return { ok: false } as Response
    })

    render(
      <QueryClientProvider client={queryClient}>
        <ExportHistoryPanel />
      </QueryClientProvider>
    )

    // 默认展示导出批次选项卡
    await waitFor(() => {
      expect(screen.getByText('LsaT2T01G023690 重点候选')).toBeInTheDocument()
      expect(screen.getByText('下载文件')).toBeInTheDocument()
      expect(screen.getByText('csv')).toBeInTheDocument()
    })

    // 切换到算法计算作业履历
    const jobsTabBtn = screen.getByRole('tab', { name: /算法计算作业履历/i })
    await user.click(jobsTabBtn)

    // 应展示打分任务记录
    await waitFor(() => {
      expect(screen.getByText(/测试单打分/i)).toBeInTheDocument()
      expect(screen.getByText('已完成')).toBeInTheDocument()
    })

    // 作业履历每行可从记录直接导出（xlsx / CSV）
    URL.createObjectURL = vi.fn(() => 'blob:mock')
    URL.revokeObjectURL = vi.fn()
    await user.click(screen.getByRole('button', { name: /导出 \(xlsx\)/i }))
    await waitFor(() => {
      const urls = (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mock.calls.map((c) =>
        String(c[0])
      )
      expect(
        urls.some((u) => u.includes('/api/v1/scoring/jobs/job-5678-uuid/export?format=xlsx'))
      ).toBe(true)
    })
    expect(screen.queryByText(/服务未连接/)).not.toBeInTheDocument()
  })

  it('deletes a job only after confirmation and removes it from the list', async () => {
    const user = userEvent.setup()

    let jobs = [
      {
        job_id: 'job-5678-uuid',
        title: '测试单打分 (TGGATTCC...)',
        job_type: 'single',
        status: 'completed',
        total_sequences: 1,
        processed_sequences: 1,
        progress_pct: 100.0,
        duration_seconds: 0.8,
        warning_message: null,
        error_message: null,
        created_at: new Date().toISOString(),
        completed_at: new Date().toISOString(),
      },
    ]
    const deleteCalls: string[] = []

    vi.spyOn(globalThis, 'fetch').mockImplementation(
      async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input)
        if ((init?.method || 'GET') === 'DELETE') {
          deleteCalls.push(url)
          jobs = []
          return { ok: true, json: async () => ({ deleted: true }) } as Response
        }
        if (url.includes('/api/v1/exports')) {
          return { ok: true, json: async () => [] } as Response
        }
        if (url.includes('/api/v1/scoring/jobs')) {
          return { ok: true, json: async () => jobs } as Response
        }
        return { ok: false } as Response
      }
    )

    render(
      <QueryClientProvider client={queryClient}>
        <ExportHistoryPanel />
      </QueryClientProvider>
    )

    await user.click(screen.getByRole('tab', { name: /算法计算作业履历/i }))
    await waitFor(() => {
      expect(screen.getByText(/测试单打分/i)).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: /^删除$/i }))
    // 确认弹窗：说明连带明细与算好的数据保留
    expect(screen.getByText('确认删除？')).toBeInTheDocument()
    expect(screen.getByText(/条序列明细（不可恢复）/)).toBeInTheDocument()
    expect(screen.getByText(/已算好的脱靶与多组学结果保留/)).toBeInTheDocument()

    // 取消不发删除请求
    await user.click(screen.getByRole('button', { name: '取消' }))
    expect(deleteCalls).toHaveLength(0)

    // 确认后硬删除并从列表移除
    await user.click(screen.getByRole('button', { name: /^删除$/i }))
    await user.click(screen.getByRole('button', { name: '确认删除' }))
    await waitFor(() => {
      expect(deleteCalls.some((u) => u.includes('/api/v1/scoring/jobs/job-5678-uuid'))).toBe(true)
      expect(screen.queryByText(/测试单打分/i)).not.toBeInTheDocument()
    })
  })

  it('deletes an export batch archive after confirmation', async () => {
    const user = userEvent.setup()

    let batches = [
      {
        id: 'batch-1234-uuid',
        name: 'LsaT2T01G023690 重点候选',
        format: 'csv',
        gene_id: 'LsaT2T01G023690',
        candidate_count: 5,
        created_at: new Date().toISOString(),
      },
    ]
    const deleteCalls: string[] = []

    vi.spyOn(globalThis, 'fetch').mockImplementation(
      async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input)
        if ((init?.method || 'GET') === 'DELETE') {
          deleteCalls.push(url)
          batches = []
          return { ok: true, json: async () => ({ deleted: true }) } as Response
        }
        if (url.includes('/api/v1/exports')) {
          return { ok: true, json: async () => batches } as Response
        }
        return { ok: false } as Response
      }
    )

    render(
      <QueryClientProvider client={queryClient}>
        <ExportHistoryPanel />
      </QueryClientProvider>
    )

    await waitFor(() => {
      expect(screen.getByText('LsaT2T01G023690 重点候选')).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: /^删除$/i }))
    expect(screen.getByText(/导出归档记录（不可恢复）/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '确认删除' }))
    await waitFor(() => {
      expect(deleteCalls.some((u) => u.includes('/api/v1/exports/batch-1234-uuid'))).toBe(true)
      expect(screen.queryByText('LsaT2T01G023690 重点候选')).not.toBeInTheDocument()
    })
  })
})
