import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import '@testing-library/jest-dom/vitest'
import { CandidateSearchPanel } from './CandidateSearchPanel'

describe('CandidateSearchPanel', () => {
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

  it('renders genes list and fetches candidate data', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/api/v1/genes')) {
        return {
          ok: true,
          json: async () => [
            {
              gene_id: 'LsaT2T01G023690',
              chrom: 'Chr01',
              start: 83870025,
              end: 83876080,
              strand: '+',
              nlr_type: 'NLR-LRR',
              candidate_count: 42,
            },
          ],
        } as Response
      }
      if (url.includes('/api/v1/candidates')) {
        return {
          ok: true,
          json: async () => ({
            items: [
              {
                id: 1,
                guide_id: 'Lsat_675191',
                gene_id: 'LsaT2T01G023690',
                chrom: 'Chr01',
                start: 83868028,
                end: 83868050,
                strand: '+',
                seq30: 'TTTGTGGATTCCGGTAGAATCTGATGGAAT',
                seq20: 'TGGATTCCGGTAGAATCTGA',
                pam: 'TGG',
                region_type: 'exon',
                is_centromere: false,
                is_exon: true,
                gc_pct: 45.0,
                tm_c: 58.0,
                offtarget_count_mis3: 3,
                efficiency_score: 82.5,
              },
            ],
            total: 1,
            page: 1,
            page_size: 50,
            total_pages: 1,
            gene_summary: {
              gene_id: 'LsaT2T01G023690',
              chrom: 'Chr01',
              start: 83870025,
              end: 83876080,
              strand: '+',
              total_candidates: 42,
              filtered_candidates: 1,
            },
          }),
        } as Response
      }
      return { ok: false } as Response
    })

    render(
      <QueryClientProvider client={queryClient}>
        <CandidateSearchPanel />
      </QueryClientProvider>
    )

    // 应该展示基因选择器
    await waitFor(() => {
      expect(screen.getByText(/LsaT2T01G023690/i)).toBeInTheDocument()
    })

    // 应该展示候选靶点表格项
    await waitFor(() => {
      expect(screen.getByText(/Lsat_675191/i)).toBeInTheDocument()
      expect(screen.getByText(/82.5/i)).toBeInTheDocument()
      expect(screen.getByText(/TGGATTCCGGTAGAATCTGA/i)).toBeInTheDocument()
    })
  })

  it('selects candidate and displays floating export action bar', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/api/v1/genes')) {
        return {
          ok: true,
          json: async () => [{ gene_id: 'LsaT2T01G023690', chrom: 'Chr01', start: 100, end: 500, strand: '+', candidate_count: 1 }],
        } as Response
      }
      if (url.includes('/api/v1/candidates')) {
        return {
          ok: true,
          json: async () => ({
            items: [
              {
                id: 1,
                guide_id: 'Lsat_675191',
                gene_id: 'LsaT2T01G023690',
                chrom: 'Chr01',
                start: 120,
                end: 150,
                strand: '+',
                seq30: 'TTTGTGGATTCCGGTAGAATCTGATGGAAT',
                seq20: 'TGGATTCCGGTAGAATCTGA',
                pam: 'TGG',
                region_type: 'exon',
                is_centromere: false,
                is_exon: true,
                gc_pct: 45.0,
                tm_c: 58.0,
                offtarget_count_mis3: 0,
                efficiency_score: 82.5,
              },
            ],
            total: 1,
            page: 1,
            page_size: 20,
            total_pages: 1,
          }),
        } as Response
      }
      return { ok: false } as Response
    })

    const { getByRole } = render(
      <QueryClientProvider client={queryClient}>
        <CandidateSearchPanel />
      </QueryClientProvider>
    )

    await waitFor(() => {
      expect(screen.getByText(/Lsat_675191/i)).toBeInTheDocument()
    })

    // 勾选靶点
    const checkbox = getByRole('checkbox', { name: /选择靶点 Lsat_675191/i })
    expect(checkbox).toBeInTheDocument()
    fireEvent.click(checkbox)

    // 悬浮工具栏应显示已勾选提示与导出按钮
    await waitFor(() => {
      expect(screen.getByText('个靶点已勾选')).toBeInTheDocument()
      expect(screen.getByText('导出 CSV')).toBeInTheDocument()
      expect(screen.getByText('导出 Excel')).toBeInTheDocument()
    })
  })

  it('renders target tissue segmented selector, expression dashboard, and priority score columns', async () => {
    let requestedTissue: string | null = null

    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/api/v1/genes/') && url.includes('/expression')) {
        return {
          ok: true,
          json: async () => ({
            gene_id: 'LsaT2T01G023690',
            lsa_id: 'LSA25643',
            tier: 1,
            lsa_vote_frac: 0.82,
            is_mappable: true,
            top_tissue: '根',
            top_tpm: 3.39,
            tau: 0.62,
            n_cluster: 1,
            tpm_dict: {
              Root: 3.39,
              Stem: 1.43,
              Leaf: 0.95,
              Flower: 1.09,
              Seed: 1.72,
            },
          }),
        } as Response
      }
      if (url.includes('/api/v1/genes')) {
        return {
          ok: true,
          json: async () => [
            { gene_id: 'LsaT2T01G023690', chrom: 'Chr01', start: 100, end: 500, strand: '+', candidate_count: 1 },
          ],
        } as Response
      }
      if (url.includes('/api/v1/candidates')) {
        const u = new URL(url, 'http://localhost')
        requestedTissue = u.searchParams.get('target_tissue')
        return {
          ok: true,
          json: async () => ({
            items: [
              {
                id: 1,
                guide_id: 'Lsat_675191',
                gene_id: 'LsaT2T01G023690',
                chrom: 'Chr01',
                start: 120,
                end: 150,
                strand: '+',
                seq30: 'TTTGTGGATTCCGGTAGAATCTGATGGAAT',
                seq20: 'TGGATTCCGGTAGAATCTGA',
                pam: 'TGG',
                region_type: 'exon',
                is_centromere: false,
                is_exon: true,
                gc_pct: 45.0,
                tm_c: 58.0,
                offtarget_count_mis3: 0,
                efficiency_score: 82.5,
                priority_score: 0.742,
                hazard_score: 0.0,
                expression_status: 'mapped',
                expression_status_display: '已映射',
              },
            ],
            total: 1,
            page: 1,
            page_size: 20,
            total_pages: 1,
          }),
        } as Response
      }
      return { ok: false } as Response
    })

    render(
      <QueryClientProvider client={queryClient}>
        <CandidateSearchPanel />
      </QueryClientProvider>
    )

    // 1. 验证目标组织选择器按钮组与表达看板渲染
    await waitFor(() => {
      expect(screen.getByText('目标组织 (方案3联动)')).toBeInTheDocument()
      expect(screen.getByText('多组织表达看板与靶向适宜性诊断')).toBeInTheDocument()
      expect(screen.getByText('LSA25643')).toBeInTheDocument()
      expect(screen.getByText(/中等表达/i)).toBeInTheDocument()
      expect(screen.getByText(/组织优先 \(叶\)/i)).toBeInTheDocument()
      expect(screen.getByText('0.742')).toBeInTheDocument()
      expect(screen.getByText('已映射')).toBeInTheDocument()
    })

    // 默认请求组织为 Leaf
    expect(requestedTissue).toBe('Leaf')

    // 2. 切换目标组织至“根”
    const rootButton = screen.getByRole('button', { name: /根.*Root/i })
    fireEvent.click(rootButton)

    await waitFor(() => {
      expect(requestedTissue).toBe('Root')
      expect(screen.getByText(/组织优先 \(根\)/i)).toBeInTheDocument()
    })
  })
})

