import { render, screen, waitFor } from '@testing-library/react'
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
})
