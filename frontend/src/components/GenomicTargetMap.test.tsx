import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import '@testing-library/jest-dom/vitest'
import { GenomicTargetMap, formatMapTooltip } from './GenomicTargetMap'
import type { GeneInfo } from './CandidateSearchPanel'
import type { CandidateItem } from '../lib/candidateQuery'

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

  const mockStructure = {
    gene_id: 'LsaT2T01G023690',
    available: true,
    bundle_id: 'lettuce',
    chrom: 'Chr01',
    start: 83870100,
    end: 83875900,
    strand: '+',
    tss: 83870100,
    exons: [
      [83870100, 83870400],
      [83871500, 83871800],
      [83874000, 83874300],
    ],
    cds: [[83870100, 83870400]],
    transcripts: ['LsaT2T01G023690.mRNA1'],
    domains: [
      {
        gene_id: 'LsaT2T01G023690',
        chrom: 'Chr01',
        start: 83871000,
        end: 83872500,
        strand: '+',
        domain_type: 'NBS',
        domain_name: 'NBARC_1',
        source: 'NLR-Annotator-2.1b',
      },
    ],
    domain_note: '蛋白功能域来自离线注释（NLR-Annotator/HMMER，GFF 不含结构域信息）',
  }

  const mockFetchJson = (body: unknown) =>
    Promise.resolve({ ok: true, json: async () => body }) as unknown as Promise<Response>

  beforeEach(() => {
    // 默认：基因结构注释接口不可用（验证优雅降级，不影响既有断言）
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('network unavailable'))
  })

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

  it('requests gene structure annotation on mount and renders structure/domain tracks', async () => {
    const fetchSpy = vi
      .spyOn(globalThis, 'fetch')
      .mockImplementation(() => mockFetchJson(mockStructure))

    render(
      <GenomicTargetMap
        gene={mockGene}
        candidates={mockCandidates}
        selectedGuideId={null}
        onSelectCandidate={() => {}}
      />
    )

    // 按 gene_id + bundle_id 按需请求
    await waitFor(() => expect(fetchSpy).toHaveBeenCalled())
    const url = String(fetchSpy.mock.calls[0][0])
    expect(url).toContain('/api/v1/annotation/gene-structure')
    expect(url).toContain('gene_id=LsaT2T01G023690')
    expect(url).toContain('bundle_id=lettuce')

    // 基因结构轨道：外显子 hover 显示区间、TSS 标记、图例
    await waitFor(() => {
      expect(screen.getByTitle('外显子 83870100-83870400')).toBeInTheDocument()
      expect(screen.getByTitle('外显子 83871500-83871800')).toBeInTheDocument()
    })
    expect(screen.getByTitle('TSS 转录起始位点 83870100')).toBeInTheDocument()
    expect(screen.getByText(/TSS（转录起始位点）/i)).toBeInTheDocument()
    expect(screen.getByText(/外显子$/i)).toBeInTheDocument()
    expect(screen.getByText(/内含子$/i)).toBeInTheDocument()

    // 蛋白功能域轨道：hover 显示 domain_type + domain_name + 坐标
    const domainChip = screen.getByTitle(/NBS · NBARC_1 · 83871000-83872500/)
    expect(domainChip).toBeInTheDocument()
    expect(domainChip).toHaveTextContent('NBS')
  })

  it('shows placeholder text when no protein domains annotated', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      mockFetchJson({ ...mockStructure, domains: [] })
    )

    render(
      <GenomicTargetMap
        gene={mockGene}
        candidates={mockCandidates}
        selectedGuideId={null}
        onSelectCandidate={() => {}}
      />
    )

    await waitFor(() => {
      expect(screen.getByText(/暂无蛋白功能域注释/)).toBeInTheDocument()
    })
    expect(screen.getByText(/蛋白功能域来自离线注释/)).toBeInTheDocument()
  })

  it('degrades gracefully when annotation is unavailable', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      mockFetchJson({
        gene_id: 'LsaT2T01G023690',
        available: false,
        missing_requirements: ['GFF 基因结构注释'],
      })
    )

    render(
      <GenomicTargetMap
        gene={mockGene}
        candidates={mockCandidates}
        selectedGuideId={null}
        onSelectCandidate={() => {}}
      />
    )

    await waitFor(() => {
      expect(screen.getByText(/基因结构注释暂不可用/)).toBeInTheDocument()
    })
    expect(screen.getByTestId('echarts-container')).toBeInTheDocument()
  })

  it('renders fallback hint and keeps chart when annotation request fails', async () => {
    render(
      <GenomicTargetMap
        gene={mockGene}
        candidates={mockCandidates}
        selectedGuideId={null}
        onSelectCandidate={() => {}}
      />
    )

    await waitFor(() => {
      expect(screen.getByText(/已降级为基础基因图谱/)).toBeInTheDocument()
    })
    expect(screen.getByText(/染色体物理分布交互图谱/i)).toBeInTheDocument()
    expect(screen.getByTestId('echarts-container')).toBeInTheDocument()
  })

  it('formats chart hover tooltips for exon / intron / TSS / domain track items', () => {
    // 外显子 hover 显示区间
    expect(formatMapTooltip({ track: 'exon', exon: [35026, 35167], isCds: true })).toContain(
      '外显子 35026-35167'
    )
    expect(formatMapTooltip({ track: 'intron', intron: [35167, 35345] })).toContain('内含子 35167-35345')
    expect(formatMapTooltip({ track: 'tss', tss: 35026 })).toContain('TSS 转录起始位点 35026')
    const domainTip = formatMapTooltip({
      track: 'domain',
      domain: {
        gene_id: 'LsT2T1G000010',
        chrom: 'Chr1',
        start: 35100,
        end: 35500,
        strand: '+',
        domain_type: 'NBS',
        domain_name: 'NBARC_1',
        source: 'NLR-Annotator-2.1b',
      },
    })
    // 功能域 hover 显示 domain_type + domain_name + 坐标
    expect(domainTip).toContain('NBS')
    expect(domainTip).toContain('NBARC_1')
    expect(domainTip).toContain('35100-35500')
    // gRNA 散点 tooltip 保留原信息
    expect(
      formatMapTooltip({
        cand: {
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
        },
      })
    ).toContain('Lsat_675191')
  })
})
