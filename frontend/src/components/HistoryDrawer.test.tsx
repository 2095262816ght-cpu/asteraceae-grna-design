import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { HistoryDrawer } from './HistoryDrawer'

describe('HistoryDrawer', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    })
    vi.restoreAllMocks()
  })

  it('renders history jobs when open and handles job selection', async () => {
    const user = userEvent.setup()
    const onSelectJob = vi.fn()
    const onClose = vi.fn()

    const mockJobs = [
      {
        job_id: 'job-999-uuid',
        title: '批量打分: gRNA_candidates.csv',
        job_type: 'batch',
        status: 'completed',
        total_sequences: 10,
        processed_sequences: 10,
        progress_pct: 100.0,
        duration_seconds: 3.5,
        warning_message: null,
        error_message: null,
        created_at: new Date().toISOString(),
        completed_at: new Date().toISOString(),
      },
    ]

    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input)
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
        <HistoryDrawer isOpen={true} onClose={onClose} onSelectJob={onSelectJob} />
      </QueryClientProvider>
    )

    expect(screen.getByText('模型打分历史任务抽屉')).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText('批量打分: gRNA_candidates.csv')).toBeInTheDocument()
      expect(screen.getByText('序列数: 10 条')).toBeInTheDocument()
    })

    // 点击该任务卡片，应触发 onSelectJob 回调
    const jobCard = screen.getByText('批量打分: gRNA_candidates.csv')
    await user.click(jobCard)

    expect(onSelectJob).toHaveBeenCalledWith('job-999-uuid')
    expect(onClose).toHaveBeenCalled()
  })

  it('renders nothing when isOpen is false', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <HistoryDrawer isOpen={false} onClose={vi.fn()} />
      </QueryClientProvider>
    )

    expect(screen.queryByText('模型打分历史任务抽屉')).not.toBeInTheDocument()
  })
})
