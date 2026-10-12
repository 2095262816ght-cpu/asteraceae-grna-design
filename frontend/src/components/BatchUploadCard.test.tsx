import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BatchUploadCard } from './BatchUploadCard'

describe('BatchUploadCard', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    })
    vi.restoreAllMocks()
  })

  it('renders initial upload dropzone and template download buttons', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <BatchUploadCard />
      </QueryClientProvider>
    )

    expect(screen.getByText('批量 gRNA 序列上传与异步打分流水线')).toBeInTheDocument()
    expect(screen.getByText('下载 CSV 模板')).toBeInTheDocument()
    expect(screen.getByText('下载 Excel 模板')).toBeInTheDocument()
    expect(screen.getByText(/点击选择文件 或 将表格拖拽至此处/i)).toBeInTheDocument()
  })

  it('handles file selection, uploads file, and polls for completed results', async () => {
    const user = userEvent.setup()

    const mockUploadResponse = {
      job_id: 'job-1234-uuid',
      title: '批量打分: test.csv',
      status: 'pending',
      total_sequences: 2,
      processed_sequences: 0,
      valid_count: 2,
      invalid_count: 0,
      created_at: new Date().toISOString(),
    }

    const mockJobDetail = {
      job_id: 'job-1234-uuid',
      title: '批量打分: test.csv',
      job_type: 'batch',
      status: 'completed',
      total_sequences: 2,
      processed_sequences: 2,
      progress_pct: 100.0,
      duration_seconds: 1.25,
      warning_message: null,
      error_message: null,
      created_at: new Date().toISOString(),
      completed_at: new Date().toISOString(),
      items: [
        {
          id: 1,
          custom_id: 'Sample_G1',
          seq30: 'TTTGTGGATTCCGGTAGAATCTGATGGAAT',
          flank_5p: 'TTTG',
          guide_seq: 'TGGATTCCGGTAGAATCTGA',
          pam: 'TGG',
          flank_3p: 'AAT',
          gc_pct: 45.0,
          tm_c: 69.0,
          deepspcas9_score: 62.5,
          crispron_source: 'approximated',
          efficiency_score: 84.5,
          is_valid: true,
          error_message: null,
        },
        {
          id: 2,
          custom_id: 'Sample_G2',
          seq30: 'INVALID_SEQUENCE',
          flank_5p: null,
          guide_seq: null,
          pam: null,
          flank_3p: null,
          gc_pct: null,
          tm_c: null,
          deepspcas9_score: null,
          crispron_source: null,
          efficiency_score: null,
          is_valid: false,
          error_message: '序列长度需为 30nt',
        },
      ],
    }

    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/api/v1/scoring/upload')) {
        return {
          ok: true,
          json: async () => mockUploadResponse,
        } as Response
      }
      if (url.includes('/api/v1/scoring/jobs/job-1234-uuid')) {
        return {
          ok: true,
          json: async () => mockJobDetail,
        } as Response
      }
      return { ok: false } as Response
    })

    const { container } = render(
      <QueryClientProvider client={queryClient}>
        <BatchUploadCard />
      </QueryClientProvider>
    )

    // 选择测试文件
    const file = new File(['靶点编号,30bp靶位点序列\nG1,TTTGTGGATTCCGGTAGAATCTGATGGAAT'], 'test.csv', {
      type: 'text/csv',
    })
    const input = container.querySelector('input[type="file"]') as HTMLInputElement
    expect(input).not.toBeNull()

    fireEvent.change(input, { target: { files: [file] } })

    // 确认已选文件提示展示
    expect(screen.getByText('test.csv')).toBeInTheDocument()
    expect(screen.getByText('启动批处理流水线')).toBeInTheDocument()

    // 点击启动批处理流水线
    const startBtn = screen.getByText('启动批处理流水线')
    await user.click(startBtn)

    // 等待轮询结果加载完成并展示表格
    await waitFor(() => {
      expect(screen.getByText('计算全部完成')).toBeInTheDocument()
    })

    // 验证渲染的统计和表格内容
    expect(screen.getByText('检测结果明细清单')).toBeInTheDocument()
    expect(screen.getByText('Sample_G1')).toBeInTheDocument()
    expect(screen.getByText('84.50')).toBeInTheDocument()
    expect(screen.getByText('Sample_G2')).toBeInTheDocument()
    expect(screen.getByText('序列长度需为 30nt')).toBeInTheDocument()
  })
})
