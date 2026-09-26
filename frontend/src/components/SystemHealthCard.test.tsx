import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import '@testing-library/jest-dom/vitest'
import { SystemHealthCard } from './SystemHealthCard'

describe('SystemHealthCard', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    })
    vi.restoreAllMocks()
  })

  it('renders healthy status when API returns ok', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        status: 'ok',
        version: '2.1.0',
        database: 'connected',
        timestamp: '2026-09-26T12:00:00Z',
      }),
    } as Response)

    render(
      <QueryClientProvider client={queryClient}>
        <SystemHealthCard />
      </QueryClientProvider>
    )

    expect(screen.getByText(/正在检测系统服务/i)).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText(/服务运行正常/i)).toBeInTheDocument()
      expect(screen.getByText(/v2.1.0/i)).toBeInTheDocument()
      expect(screen.getByText(/数据库连接正常/i)).toBeInTheDocument()
    })
  })

  it('renders error state when fetch fails', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new Error('Network error'))

    render(
      <QueryClientProvider client={queryClient}>
        <SystemHealthCard />
      </QueryClientProvider>
    )

    await waitFor(() => {
      expect(screen.getByText(/服务连接异常/i)).toBeInTheDocument()
    })
  })
})
