import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import '@testing-library/jest-dom/vitest'
import { SingleScoringCard } from './SingleScoringCard'

describe('SingleScoringCard', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    })
    vi.restoreAllMocks()
  })

  it('renders input form with example button and validates 30bp', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <SingleScoringCard />
      </QueryClientProvider>
    )

    expect(screen.getByText(/30nt 靶位点序列实时打分/i)).toBeInTheDocument()
    const exampleBtn = screen.getByText(/填入示例 1/i)
    expect(exampleBtn).toBeInTheDocument()

    // 点击示例按钮自动填入 30bp
    await userEvent.click(exampleBtn)
    expect(screen.getByDisplayValue('TTTGTGGATTCCGGTAGAATCTGATGGAAT')).toBeInTheDocument()
    expect(screen.getByText(/30 \/ 30 nt/i)).toBeInTheDocument()
  })

  it('submits valid sequence and renders prediction result card', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        job_id: 'job-123456',
        title: '测试靶点',
        seq30: 'TTTGTGGATTCCGGTAGAATCTGATGGAAT',
        flank_5p: 'TTTG',
        guide_seq: 'TGGATTCCGGTAGAATCTGA',
        pam: 'TGG',
        flank_3p: 'AAT',
        gc_pct: 45.0,
        tm_c: 69.0,
        deepspcas9_score: 46.28,
        crispron_source: 'wsl_real',
        efficiency_score: 76.6,
        warning_message: null,
        duration_seconds: 0.85,
        created_at: '2026-09-26T12:00:00Z',
      }),
    } as Response)

    render(
      <QueryClientProvider client={queryClient}>
        <SingleScoringCard />
      </QueryClientProvider>
    )

    await userEvent.click(screen.getByText(/填入示例 1/i))
    const submitBtn = screen.getByRole('button', { name: /开始实时打分/i })
    await userEvent.click(submitBtn)

    await waitFor(() => {
      expect(screen.getByText(/76.6/i)).toBeInTheDocument()
      expect(screen.getByText(/45.0%/i)).toBeInTheDocument()
      expect(screen.getByText(/TGGATTCCGGTAGAATCTGA/i)).toBeInTheDocument()
      expect(screen.getByText(/wsl_real/i)).toBeInTheDocument()
    })
  })
})
