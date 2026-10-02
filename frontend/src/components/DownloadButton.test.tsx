import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import '@testing-library/jest-dom/vitest'
import { DownloadButton } from './DownloadButton'

describe('DownloadButton', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    URL.createObjectURL = vi.fn(() => 'blob:mock')
    URL.revokeObjectURL = vi.fn()
  })

  it('点击后请求接口并触发下载', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      headers: new Headers({ 'Content-Disposition': 'attachment; filename="result.xlsx"' }),
      blob: async () => new Blob(['x']),
    } as Response)

    render(<DownloadButton url="/api/v1/scoring/jobs/j1/export?format=xlsx">导出结果 (xlsx)</DownloadButton>)
    await userEvent.click(screen.getByRole('button', { name: /导出结果/i }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith('/api/v1/scoring/jobs/j1/export?format=xlsx')
    })
    expect(URL.createObjectURL).toHaveBeenCalled()
    expect(screen.queryByText(/服务未连接/)).not.toBeInTheDocument()
  })

  it('服务未连接时给出明确报错而不是静默失败', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Failed to fetch'))

    render(<DownloadButton url="/api/v1/exports/b1/download">下载文件</DownloadButton>)
    await userEvent.click(screen.getByRole('button', { name: /下载文件/i }))

    await waitFor(() => {
      expect(screen.getByText(/服务未连接/)).toBeInTheDocument()
    })
  })

  it('接口返回错误时透出服务端提示', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({ detail: '未找到任务' }),
    } as unknown as Response)

    render(<DownloadButton url="/api/v1/scoring/jobs/missing/export?format=csv">CSV</DownloadButton>)
    await userEvent.click(screen.getByRole('button', { name: /CSV/i }))

    await waitFor(() => {
      expect(screen.getByText('未找到任务')).toBeInTheDocument()
    })
  })
})
