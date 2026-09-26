import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import '@testing-library/jest-dom/vitest'
import { GenomicTargetMap } from './GenomicTargetMap'
import type { CandidateItem, GeneInfo } from './CandidateSearchPanel'

describe('GenomicTargetMap', () => {

  const mockGene: GeneInfo = {
    gene_id: 'LsaT2T01G023690',
    chrom: 'Chr01',
    start: 83870000,
    end: 83876000,
    strand: '+',
    nlr_type: 'NLR-LRR',
    candidate_count: 2,
  }

  const mockCandidates: CandidateItem[] = [
    {
      id: 1,
      guide_id: 'Lsat_675191',
      gene_id: 'LsaT2T01G023690',
      chrom: 'Chr01',
      start: 83871000,
      end: 83871022,
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
    {
      id: 2,
      guide_id: 'Lsat_675192',
      gene_id: 'LsaT2T01G023690',
      chrom: 'Chr01',
      start: 83874000,
      end: 83874022,
      strand: '-',
      seq30: 'AAACCCCGGGGTTTTCCCCAAAATTTGGCC',
      seq20: 'CCCCGGGGTTTTCCCCAAAA',
      pam: 'CGG',
      region_type: 'exon',
      is_centromere: false,
      is_exon: true,
      gc_pct: 60.0,
      tm_c: 62.0,
      offtarget_count_mis3: 1,
      efficiency_score: 45.0,
    },
  ]

  it('renders genomic map header and chart container', () => {
    render(
      <GenomicTargetMap
        gene={mockGene}
        candidates={mockCandidates}
        selectedGuideId={null}
        onSelectCandidate={() => {}}
      />
    )

    expect(screen.getByText(/染色体物理分布交互图谱/i)).toBeInTheDocument()
    expect(screen.getByText(/Chr01/i)).toBeInTheDocument()
    expect(screen.getByTestId('echarts-container')).toBeInTheDocument()
  })

  it('triggers onSelectCandidate callback when chart point clicked', () => {
    const onSelect = vi.fn()
    render(
      <GenomicTargetMap
        gene={mockGene}
        candidates={mockCandidates}
        selectedGuideId={null}
        onSelectCandidate={onSelect}
      />
    )

    screen.getByTestId('mock-chart-click').click()
    expect(onSelect).toHaveBeenCalledWith('Lsat_675191')
  })
})
