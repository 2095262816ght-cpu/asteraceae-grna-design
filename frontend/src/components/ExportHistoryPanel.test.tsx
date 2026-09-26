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
    const jobsTabBtn = screen.getByRole('button', { name: /算法计算作业履历/i })
    await user.click(jobsTabBtn)

    // 应展示打分任务记录
    await waitFor(() => {
      expect(screen.getByText(/测试单打分/i)).toBeInTheDocument()
      expect(screen.getByText('已完成')).toBeInTheDocument()
    })
  })
})
