// 候选查询深度模块单测：只穿过模块接口验证请求编码（区域优先级规则）与导出预计算编排。
import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  buildCandidatesParams,
  fetchCandidates,
  fetchSortHelp,
  precomputeOfftargetForExport,
} from './candidateQuery'

describe('buildCandidatesParams 区域优先级规则（编码侧单点定义）', () => {
  it('region_type 优先于 exon_only', () => {
    const sp = buildCandidatesParams({
      geneId: 'G1',
      regionType: 'promoter',
      exonOnly: true,
    })
    expect(sp.get('region_type')).toBe('promoter')
    expect(sp.get('exon_only')).toBeNull()
  })

  it("'all' 哨兵不下发，回退 exon_only", () => {
    const sp = buildCandidatesParams({ geneId: 'G1', regionType: 'all', exonOnly: true })
    expect(sp.get('region_type')).toBeNull()
    expect(sp.get('exon_only')).toBe('true')
  })

  it("'none' 显式下发（查无区域注释）", () => {
    const sp = buildCandidatesParams({ geneId: 'G1', regionType: 'none' })
    expect(sp.get('region_type')).toBe('none')
    expect(sp.get('exon_only')).toBeNull()
  })

  it('min_score=0 不下发；正数下发', () => {
    expect(buildCandidatesParams({ geneId: 'G1', minScore: 0 }).get('min_score')).toBeNull()
    expect(buildCandidatesParams({ geneId: 'G1', minScore: 70 }).get('min_score')).toBe('70')
  })
})

describe('fetchCandidates', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('按编码参数请求候选接口', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({ items: [], total: 0, page: 1, page_size: 20, total_pages: 1 }),
    } as Response)
    await fetchCandidates({ geneId: 'G1', regionType: 'exon', page: 2, pageSize: 20 })
    const url = String(fetchMock.mock.calls[0][0])
    expect(url).toContain('/api/v1/candidates?')
    expect(url).toContain('gene_id=G1')
    expect(url).toContain('region_type=exon')
    expect(url).toContain('page=2')
  })
})

describe('precomputeOfftargetForExport 导出预计算编排', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('逐条预计算并按序汇报进度', async () => {
    const calls: number[][] = []
    const progress: Array<[number, number]> = []
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (_input, init) => {
      calls.push(JSON.parse(String(init?.body)).candidate_ids)
      return { ok: true, json: async () => ({ computed: 1, items: [] }) } as Response
    })
    await precomputeOfftargetForExport([11, 22], (done, total) => progress.push([done, total]))
    expect(calls).toEqual([[11], [22]])
    expect(progress).toEqual([
      [0, 2],
      [1, 2],
    ])
  })
})

describe('fetchSortHelp', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('按目标组织展示名取排序帮助条目', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({ items: [{ key: 'priority_score', title: 't', direction: 'd', lines: ['l'] }] }),
    } as Response)
    const items = await fetchSortHelp('叶')
    expect(String(fetchMock.mock.calls[0][0])).toContain('tissue_name=')
    expect(items).toHaveLength(1)
  })
})
