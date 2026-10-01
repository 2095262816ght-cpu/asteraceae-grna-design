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

  it('defaults to efficiency sort and explains ranking methods in help modal', async () => {
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
          json: async () => ({ items: [], total: 0, page: 1, page_size: 20, total_pages: 1 }),
        } as Response
      }
      if (url.includes('/api/v1/meta/sort-help')) {
        // 帮助条目由后端 /meta/sort-help 供给（公式文案单点定义在 cs_pipeline.core.ranking_semantics）
        return {
          ok: true,
          json: async () => ({
            items: [
              {
                key: 'efficiency_score',
                title: 'on-target 效率分 (v2.1 推荐排序) · 系统默认',
                direction: '降序（分数高者优先）',
                lines: ['排名方式：按分数降序。'],
              },
              {
                key: 'priority_score',
                title: '组织优先指数（叶）· 方案3',
                direction: '降序（指数高者优先）',
                lines: ['排名方式：PriorityScore = 0.50×效率百分位 − 0.25×脱靶罚分 + 0.25×表达项。'],
              },
              {
                key: 'offtarget_count_mis3',
                title: '潜在脱靶位点数',
                direction: '升序优先（位点越少越干净）',
                lines: ['排名方式：按计数升序。注意：这是不加权位点计数，不是 MIT/CFD 评分。'],
              },
            ],
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

    // 默认排序为效率分（v2.1）
    const select = await screen.findByRole('combobox')
    expect(select).toHaveValue('efficiency_score')

    // 打开排序说明弹窗：文案来自后端排序帮助接口
    fireEvent.click(screen.getByTitle('查看各排序方式的详细排名方法'))
    expect(screen.getByText(/排序方式说明/)).toBeInTheDocument()
    expect(await screen.findByText(/不是 MIT\/CFD 评分/)).toBeInTheDocument()
    expect(await screen.findByText(/PriorityScore/)).toBeInTheDocument()
    expect(screen.getByText(/当前选中/)).toBeInTheDocument()

    // Esc 关闭
    fireEvent.keyDown(document, { key: 'Escape' })
    await waitFor(() => {
      expect(screen.queryByText(/排序方式说明/)).not.toBeInTheDocument()
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

  it('opens offtarget detail drawer on count click and shows expression fitness column', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/api/v1/genes')) {
        return {
          ok: true,
          json: async () => [
            { gene_id: 'LsaT2T01G023690', chrom: 'Chr01', start: 100, end: 500, strand: '+', candidate_count: 1 },
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
                offtarget_count_mis3: 3,
                efficiency_score: 82.5,
                poly_t: false,
                five_prime_g: true,
                mfe_kcal: -3.4,
                mfe_risk: true,
                expression_fitness_note: '表达适配测试说明',
              },
            ],
            total: 1,
            page: 1,
            page_size: 20,
            total_pages: 1,
            gene_summary: {
              gene_id: 'LsaT2T01G023690',
              chrom: 'Chr01',
              start: 100,
              end: 500,
              strand: '+',
              total_candidates: 4,
              filtered_candidates: 1,
              poly_t_filtered_count: 2,
            },
          }),
        } as Response
      }
      if (url.includes('/api/v1/offtarget/sites')) {
        return {
          ok: true,
          json: async () => ({
            seq20: 'TGGATTCCGGTAGAATCTGA',
            bundle_id: 'lettuce',
            bundle_name: '莴苣 (LsT2T)',
            genome_note: '扫描参考基因组：莴苣 (LsT2T)（参考包 lettuce）',
            profile: { exact: 1, mis1: 1, mis2: 0, mis3: 1 },
            sites: [
              {
                chrom: 'Chr01',
                start: 120,
                end: 142,
                strand: '+',
                protospacer20: 'TGGATTCCGGTAGAATCTGA',
                pam: 'TGG',
                mismatch_count: 0,
                mismatch_positions: [],
                cfd_score: 1.0,
                mit_hit_score: 100.0,
                region_type: 'exon',
                region_label: '外显子 (exon)',
                gene_id: 'LsaT2T01G023690',
                risk_level: '在靶',
                risk_note: '候选 gRNA 自身的在靶位点（不计入脱靶风险汇总）',
                is_ontarget: true,
              },
              {
                chrom: 'Chr03',
                start: 5000,
                end: 5022,
                strand: '-',
                protospacer20: 'TGGATTCCGGTAGAATCTGG',
                pam: 'AGG',
                mismatch_count: 1,
                mismatch_positions: [4],
                cfd_score: 0.5312,
                mit_hit_score: 60.5,
                region_type: 'promoter',
                region_label: '启动子 (promoter)',
                gene_id: 'LsaT2T03G000010',
                risk_level: '高危',
                risk_note: '1 错配脱靶：风险极高，需重点评估',
                is_ontarget: false,
              },
            ],
            sites_truncated: true,
            specificity: {
              n_offtarget_sites_scored: 2,
              mit_hit_sum: 350.2,
              mit_specificity: 22.15,
              cfd_hit_sum: 3.4,
              cfd_specificity: 29.41,
              on_target_excluded: true,
            },
            method_note: '脱靶搜索口径：Cas-OFFinder 式全基因组扫描——20-mer 窗口 ≤3 错配。',
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

    await waitFor(() => {
      expect(screen.getByText(/Lsat_675191/i)).toBeInTheDocument()
    })

    // 表达适配列：MFE 红色警示 + G-start 徽章 + poly-T 过滤提示
    expect(screen.getByText(/-3\.4 kcal\/mol/)).toBeInTheDocument()
    expect(screen.getByText('G-start')).toBeInTheDocument()
    expect(screen.getByTitle('ΔG < -5 kcal/mol：自折叠可能抑制靶向活性')).toBeInTheDocument()
    expect(screen.getByTitle('表达适配测试说明')).toBeInTheDocument()
    expect(screen.getByText(/另有 2 条含 TTTT poly-T 终止信号已过滤/)).toBeInTheDocument()

    // 点击"脱靶数"数字打开抽屉
    fireEvent.click(screen.getByTitle('点击查看脱靶位点明细（坐标/错配位置/CFD/MIT 评分/区域）'))

    await waitFor(() => {
      expect(screen.getByText('脱靶位点明细（全基因组 ≤3 错配扫描）')).toBeInTheDocument()
    })

    // 顶部摘要：genome_note + 特异性汇总（注明口径、排除在靶）
    expect(screen.getByText('扫描参考基因组：莴苣 (LsT2T)（参考包 lettuce）')).toBeInTheDocument()
    expect(screen.getByText(/MIT Sguide：/)).toBeInTheDocument()
    expect(screen.getByText(/已排除候选自身在靶位点/)).toBeInTheDocument()

    // 位点表格：风险分档、坐标、CFD 4 位小数、MIT 2 位小数、截断提示、method_note
    expect(screen.getByText('在靶')).toBeInTheDocument()
    expect(screen.getByText('高危')).toBeInTheDocument()
    expect(screen.getByText(/Chr03:5/)).toBeInTheDocument()
    expect(screen.getByText('0.5312')).toBeInTheDocument()
    expect(screen.getByText('60.50')).toBeInTheDocument()
    expect(screen.getByText(/明细已截断，计数仍为全量/)).toBeInTheDocument()
    expect(screen.getByText(/Cas-OFFinder 式全基因组扫描/)).toBeInTheDocument()
  })

  it('opens methods and versions modal with sections from /meta/methods', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/api/v1/genes')) {
        return {
          ok: true,
          json: async () => [
            { gene_id: 'LsaT2T01G023690', chrom: 'Chr01', start: 100, end: 500, strand: '+', candidate_count: 1 },
          ],
        } as Response
      }
      if (url.includes('/api/v1/candidates')) {
        return {
          ok: true,
          json: async () => ({ items: [], total: 0, page: 1, page_size: 20, total_pages: 1 }),
        } as Response
      }
      if (url.includes('/api/v1/meta/methods')) {
        return {
          ok: true,
          json: async () => ({
            efficiency_model: {
              name: '自研 Stacking 元模型（效率分 v2.1）',
              kind: '自研（非 Rule Set 2/3）',
              components: ['DeepSpCas9 深度学习模型 on-target 活性分'],
              validation: '留出验证 Spearman ρ=0.464 / 0.342',
              model_card: 'cs_pipeline/results/model_card_hier_bb_nob879_0921.md',
              lineage_note: '业界常用效率模型谱系说明文本',
            },
            offtarget: {
              search: 'Cas-OFFinder 式全基因组扫描（鸽笼原理种子筛 + Hamming 验证）',
              params: {
                pam: 'NGG（SpCas9）',
                gRNA_length: '20nt',
                max_mismatches: 3,
                strands: '正负链分行计数',
              },
              site_scores: ['CFD（Cutting Frequency Determination，Doench et al. 2016）'],
              guide_specificity: 'CRISPOR 口径：MIT Sguide=100/(100+ΣhitScore)×100',
              risk_note: '0 错配脱靶（除在靶外完全匹配）致命、1 错配高危、2–3 错配相对可接受',
            },
            expression_fitness: {
              poly_t: '含 TTTT 的 spacer 在候选枚举阶段硬过滤',
              five_prime_g: "5' 端为 G 提高 U6 转录效率",
              mfe: '风险阈值 ΔG < -5 kcal/mol',
              gc: 'GC 含量建议 40%–70%',
            },
            gene_structure: {
              source: '参考包 GFF 注释（gene/mRNA/exon/CDS 层级解析）',
              protein_domains: '蛋白功能域来自 NLR-Annotator v2.1b',
            },
            reference_genomes: [
              { id: 'lettuce', display_name: '莴苣 (LsT2T)', fasta_available: true, gff_available: true },
            ],
            disclaimer: '所有预测指标为计算估计值，非实验测量。',
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

    fireEvent.click(screen.getByTitle('查看算法、版本、参数与参考基因组口径说明'))

    await waitFor(() => {
      expect(screen.getByText(/方法与版本 · 算法口径与参考基因组说明/)).toBeInTheDocument()
    })

    // 分节渲染：效率模型 / 脱靶 / 表达适配 / 基因结构 / 参考基因组 / 免责声明
    expect(screen.getByText(/效率分模型（on-target 效率分）/)).toBeInTheDocument()
    expect(screen.getByText(/自研 Stacking 元模型（效率分 v2.1）/)).toBeInTheDocument()
    expect(screen.getByText(/脱靶检测（全基因组扫描与位点评分）/)).toBeInTheDocument()
    expect(screen.getByText(/表达适配度（poly-T/)).toBeInTheDocument()
    expect(screen.getByText('基因结构注释')).toBeInTheDocument()
    expect(screen.getByText(/参考基因组（1 个参考包）/)).toBeInTheDocument()
    expect(screen.getByText(/FASTA 可用/)).toBeInTheDocument()
    expect(screen.getByText(/免责声明：/)).toBeInTheDocument()
    expect(screen.getByText(/非实验测量/)).toBeInTheDocument()
  })

  it('prompts "要计算脱靶吗" on 未计算 cell, computes after confirm and opens detail drawer', async () => {
    let computed = false
    const computeBodies: string[] = []

    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.includes('/api/v1/genes')) {
        return {
          ok: true,
          json: async () => [
            { gene_id: 'LsaT2T01G023690', chrom: 'Chr01', start: 100, end: 500, strand: '+', candidate_count: 1 },
          ],
        } as Response
      }
      if (url.includes('/api/v1/offtarget/compute')) {
        computeBodies.push(String(init?.body || ''))
        computed = true
        return {
          ok: true,
          json: async () => ({ computed: 1, items: [{ id: 1, offtarget_count_mis3: 7, n_intra_panel_sites: 0 }] }),
        } as Response
      }
      if (url.includes('/api/v1/offtarget/sites')) {
        return {
          ok: true,
          json: async () => ({
            seq20: 'TGGATTCCGGTAGAATCTGA',
            bundle_id: 'lettuce',
            bundle_name: '莴苣 (LsT2T)',
            genome_note: '扫描参考基因组：莴苣 (LsT2T)（参考包 lettuce）',
            profile: { exact: 1, mis1: 1, mis2: 1, mis3: 1 },
            sites: [],
            sites_truncated: false,
            specificity: {
              n_offtarget_sites_scored: 0,
              mit_hit_sum: 0,
              mit_specificity: 100.0,
              cfd_hit_sum: 0,
              cfd_specificity: 100.0,
              on_target_excluded: true,
            },
            method_note: '脱靶搜索口径：Cas-OFFinder 式全基因组扫描——20-mer 窗口 ≤3 错配。',
          }),
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
                // 计算前为"未计算"；POST /offtarget/compute 之后返回回填值
                offtarget_count_mis3: computed ? 7 : null,
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

    render(
      <QueryClientProvider client={queryClient}>
        <CandidateSearchPanel />
      </QueryClientProvider>
    )

    await waitFor(() => {
      expect(screen.getByText(/Lsat_675191/i)).toBeInTheDocument()
    })

    // "未计算"格可点击 → 确认框"要计算脱靶吗"
    fireEvent.click(screen.getByRole('button', { name: '未计算' }))
    expect(screen.getByText('要计算脱靶吗？')).toBeInTheDocument()
    expect(screen.getByText(/约 1 分钟/)).toBeInTheDocument()

    // 确认后调用按需计算接口
    fireEvent.click(screen.getByRole('button', { name: /计算脱靶/ }))
    await waitFor(() => {
      expect(computeBodies.length).toBe(1)
    })
    expect(JSON.parse(computeBodies[0]).candidate_ids).toEqual([1])

    // 计算完成后：数字回填 + 自动打开脱靶位点明细抽屉
    await waitFor(() => {
      expect(screen.getByText('脱靶位点明细（全基因组 ≤3 错配扫描）')).toBeInTheDocument()
    })
    const countBtn = await screen.findByTitle('点击查看脱靶位点明细（坐标/错配位置/CFD/MIT 评分/区域）')
    expect(countBtn).toHaveTextContent('7')
  })

  it('shows progress bar and spinner while scanning offtarget before export download', async () => {
    const pendingCompute: Array<(v?: unknown) => void> = []
    const computeBodies: string[] = []
    const requested: string[] = []
    // jsdom 无 createObjectURL
    const createObjectURL = vi.fn(() => 'blob:mock')
    const revokeObjectURL = vi.fn()
    vi.stubGlobal('URL', Object.assign(URL, { createObjectURL, revokeObjectURL }))

    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      requested.push(url)
      if (url.includes('/api/v1/genes')) {
        return {
          ok: true,
          json: async () => [
            { gene_id: 'LsaT2T01G023690', chrom: 'Chr01', start: 100, end: 500, strand: '+', candidate_count: 2 },
          ],
        } as Response
      }
      if (url.includes('/api/v1/offtarget/compute')) {
        computeBodies.push(String(init?.body || ''))
        // 挂起直至测试手动放行：用于稳定观察进度条
        return new Promise((resolve) => {
          pendingCompute.push(() =>
            resolve({
              ok: true,
              json: async () => ({ computed: 1, items: [] }),
            } as Response)
          )
        })
      }
      if (url.includes('/download')) {
        return {
          ok: true,
          blob: async () => new Blob(['csv']),
          headers: new Headers({ 'Content-Disposition': 'attachment; filename="demo.csv"' }),
        } as unknown as Response
      }
      if (url.includes('/api/v1/exports')) {
        return {
          ok: true,
          json: async () => ({ id: 'batch-1', name: 'demo', format: 'csv', candidate_count: 2, created_at: '' }),
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
              {
                id: 2,
                guide_id: 'Lsat_675192',
                gene_id: 'LsaT2T01G023690',
                chrom: 'Chr01',
                start: 220,
                end: 250,
                strand: '-',
                seq30: 'TTTGTGGATTCCGGTAGAATCTGATGGAAT',
                seq20: 'TGGATTCCGGTAGAATCTGA',
                pam: 'TGG',
                region_type: 'exon',
                is_centromere: false,
                is_exon: true,
                gc_pct: 45.0,
                tm_c: 58.0,
                offtarget_count_mis3: null,
                efficiency_score: 70.0,
              },
            ],
            total: 2,
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

    fireEvent.click(getByRole('checkbox', { name: /选择靶点 Lsat_675191/i }))
    fireEvent.click(getByRole('checkbox', { name: /选择靶点 Lsat_675192/i }))
    fireEvent.click(screen.getByText('导出 CSV'))

    // 第 1 条扫描中：旋转圈圈 + 进度条 + n/N 文案
    await waitFor(() => {
      expect(screen.getByRole('progressbar')).toBeInTheDocument()
    })
    expect(screen.getByText('脱靶扫描中 1/2…约 1 分钟/条')).toBeInTheDocument()
    expect(document.querySelector('.animate-spin')).toBeInTheDocument()

    // 放行第 1 条 → 进度推进到 2/2
    pendingCompute[0]()
    await waitFor(() => {
      expect(screen.getByText('脱靶扫描中 2/2…约 1 分钟/条')).toBeInTheDocument()
    })

    // 放行第 2 条 → 进入生成文件阶段并完成下载
    pendingCompute[1]()
    await waitFor(() => {
      expect(requested.some((u) => u.includes('/api/v1/exports/batch-1/download'))).toBe(true)
    })
    expect(computeBodies.length).toBe(2)
    expect(JSON.parse(computeBodies[0]).candidate_ids).toEqual([1])
    expect(JSON.parse(computeBodies[1]).candidate_ids).toEqual([2])

    // 导出完成后进度条收起，按钮复位
    await waitFor(() => {
      expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
      expect(screen.getByText('导出 CSV')).toBeInTheDocument()
    })
  })
})

