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
    // 路由化 fetch mock：参考包清单 / 注释 / 打分各走各的返回
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(typeof input === 'string' ? input : (input as Request).url)
      const json = (body: unknown) =>
        ({ ok: true, json: async () => body }) as Response
      if (url.includes('/sequence/bundles')) return json([])
      if (url.includes('/export?'))
        return {
          ok: true,
          headers: new Headers({ 'Content-Disposition': 'attachment; filename="export.xlsx"' }),
          blob: async () => new Blob(['x']),
        } as unknown as Response
      if (url.includes('/sequence/annotate'))
        return json({
          state: 'custom',
          seq30: 'TTTGTGGATTCCGGTAGAATCTGATGGAAT',
          species: 'lettuce',
          bundle_id: 'lettuce',
          bundle_name: '莴苣 (LsT2T)',
          annotation_note: '该序列未精确匹配测试基因组：多组学指标不适用，不硬算。',
        })
      return json({
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
      })
    })
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

    // 结果卡片提供 xlsx / CSV 导出入口：点击后请求对应导出接口并触发浏览器下载
    URL.createObjectURL = vi.fn(() => 'blob:mock')
    URL.revokeObjectURL = vi.fn()
    await userEvent.click(screen.getByRole('button', { name: /导出结果 \(xlsx\)/i }))
    await userEvent.click(screen.getByRole('button', { name: /^CSV$/i }))
    await waitFor(() => {
      const urls = (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mock.calls.map((c) =>
        String(c[0])
      )
      expect(
        urls.some((u) => u.includes('/api/v1/scoring/jobs/job-123456/export?format=xlsx&bundle_id=lettuce'))
      ).toBe(true)
      expect(
        urls.some((u) => u.includes('/api/v1/scoring/jobs/job-123456/export?format=csv&bundle_id=lettuce'))
      ).toBe(true)
    })
    expect(screen.queryByText(/服务未连接/)).not.toBeInTheDocument()
  })

  it('shows placeholder dashes when expression_fitness is missing (legacy response)', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <SingleScoringCard />
      </QueryClientProvider>
    )

    await userEvent.click(screen.getByText(/填入示例 1/i))
    await userEvent.click(screen.getByRole('button', { name: /开始实时打分/i }))

    await waitFor(() => {
      expect(screen.getByText(/表达适配度（U6 表达）/i)).toBeInTheDocument()
    })
    // 旧响应无 expression_fitness：三指标均显示占位“—”，不崩溃
    expect(screen.getAllByText('—').length).toBeGreaterThanOrEqual(3)
  })

  it('renders expression fitness panel with poly-T warning, G-start and MFE', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(typeof input === 'string' ? input : (input as Request).url)
      const json = (body: unknown) => ({ ok: true, json: async () => body }) as Response
      if (url.includes('/sequence/bundles')) return json([])
      if (url.includes('/export?'))
        return {
          ok: true,
          headers: new Headers({ 'Content-Disposition': 'attachment; filename="export.xlsx"' }),
          blob: async () => new Blob(['x']),
        } as unknown as Response
      if (url.includes('/sequence/annotate'))
        return json({
          state: 'custom',
          seq30: 'TTTGTGGATTCCGGTAGAATCTGATGGAAT',
          species: 'lettuce',
          bundle_id: 'lettuce',
          annotation_note: '该序列未精确匹配测试基因组：多组学指标不适用，不硬算。',
        })
      return json({
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
        expression_fitness: {
          poly_t: true,
          poly_t_filtered: false,
          five_prime_g: true,
          mfe_kcal: -3.2,
          mfe_risk: false,
          mfe_threshold: -5.0,
          note: "5' 端为 G（U6 转录起始偏好，表达加分）；spacer MFE -3.20 ≥ -5 kcal/mol：自折叠风险可接受",
        },
        warning_message: null,
        duration_seconds: 0.85,
        created_at: '2026-09-26T12:00:00Z',
      })
    })

    render(
      <QueryClientProvider client={queryClient}>
        <SingleScoringCard />
      </QueryClientProvider>
    )

    await userEvent.click(screen.getByText(/填入示例 1/i))
    await userEvent.click(screen.getByRole('button', { name: /开始实时打分/i }))

    await waitFor(() => {
      // ① Poly-T 红色警示
      expect(screen.getByText(/含 TTTT（U6 转录终止，应避免）/i)).toBeInTheDocument()
      // ② 5'G 绿色加分
      expect(screen.getByText(/G-start ✓（U6 起始偏好）/i)).toBeInTheDocument()
      // ③ MFE 数值（2 位小数）+ 阈值说明（note 全文中也含 -3.20，故用 getAllByText）
      expect(screen.getAllByText(/-3\.20/).length).toBeGreaterThanOrEqual(1)
      expect(screen.getByText('自折叠风险可接受')).toBeInTheDocument()
      expect(screen.getByText(/-5 kcal\/mol 为风险警示线（参考阈值，非绝对判据）/)).toBeInTheDocument()
    })
    // note 全文放面板底部小字
    expect(screen.getByText(/5' 端为 G（U6 转录起始偏好，表达加分）/)).toBeInTheDocument()
  })

  it('marks MFE self-folding risk and ViennaRNA fallback correctly', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(typeof input === 'string' ? input : (input as Request).url)
      const json = (body: unknown) => ({ ok: true, json: async () => body }) as Response
      if (url.includes('/sequence/bundles')) return json([])
      if (url.includes('/export?'))
        return {
          ok: true,
          headers: new Headers({ 'Content-Disposition': 'attachment; filename="export.xlsx"' }),
          blob: async () => new Blob(['x']),
        } as unknown as Response
      if (url.includes('/sequence/annotate'))
        return json({
          state: 'custom',
          seq30: 'TTTGTGGATTCCGGTAGAATCTGATGGAAT',
          species: 'lettuce',
          annotation_note: '该序列未精确匹配测试基因组：多组学指标不适用，不硬算。',
        })
      return json({
        job_id: 'job-123457',
        title: '测试靶点-风险',
        seq30: 'TTTGTGGATTCCGGTAGAATCTGATGGAAT',
        flank_5p: 'TTTG',
        guide_seq: 'TGGATTCCGGTAGAATCTGA',
        pam: 'TGG',
        flank_3p: 'AAT',
        gc_pct: 45.0,
        tm_c: 69.0,
        efficiency_score: 76.6,
        expression_fitness: {
          poly_t: false,
          five_prime_g: false,
          mfe_kcal: -8.4,
          mfe_risk: true,
          mfe_threshold: -5.0,
        },
        warning_message: null,
        duration_seconds: 0.85,
        created_at: '2026-09-26T12:00:00Z',
      })
    })

    render(
      <QueryClientProvider client={queryClient}>
        <SingleScoringCard />
      </QueryClientProvider>
    )

    await userEvent.click(screen.getByText(/填入示例 1/i))
    await userEvent.click(screen.getByRole('button', { name: /开始实时打分/i }))

    await waitFor(() => {
      expect(screen.getByText(/无 TTTT ✓/i)).toBeInTheDocument()
      expect(screen.getByText(/5' 非 G/i)).toBeInTheDocument()
      expect(screen.getByText(/-8\.40/)).toBeInTheDocument()
      expect(screen.getByText(/ΔG < -5 kcal\/mol 自折叠风险/i)).toBeInTheDocument()
    })
  })

  it('renders bundle-specific priority tissue keys for TKS stage-peak 口径', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(typeof input === 'string' ? input : (input as Request).url)
      const json = (body: unknown) => ({ ok: true, json: async () => body }) as Response
      if (url.includes('/sequence/bundles')) return json([])
      if (url.includes('/export?'))
        return {
          ok: true,
          headers: new Headers({ 'Content-Disposition': 'attachment; filename="export.xlsx"' }),
          blob: async () => new Blob(['x']),
        } as unknown as Response
      if (url.includes('/sequence/annotate'))
        return json({
          state: 'annotated',
          seq30: 'ATATGAAAATGTCAGGATGCCTGAAGGACA',
          species: 'tks',
          bundle_id: 'tks',
          bundle_name: '橡胶草 (TKS)',
          annotation_note: '精确匹配橡胶草 (TKS) 基因组：LG07:109028891-109028920 (-链)；命中基因 evm.TU.LG07.3296。',
          hit: { chrom: 'LG07', start: 109028891, end: 109028920, strand: '-' },
          offtarget: { exact: 1, mis1: 0, mis2: 0, mis3: 1 },
          priority_scores: { 根: 0.715, 叶: 0.628, 胶乳: 0.723, 花: 0.599, 花葶: 0.602 },
          priority_note:
            '按需计算（方案3 公式与 Tab 1 同源）：效率百分位 100.0%（现场枚举同基因候选分布，rank(pct=True) 同口径）；表达项取各组织 S1–S9 时相峰值 TPM（不加权、非单点 TPM，与莴苣单点 TPM 口径不可互比）',
          percentile: 1.0,
          percentile_basis: '现场枚举同基因候选分布（rank(pct=True) 同口径）',
          missing_requirements: [],
        })
      return json({
        job_id: 'job-123458',
        title: '测试靶点-TKS',
        seq30: 'ATATGAAAATGTCAGGATGCCTGAAGGACA',
        flank_5p: 'ATAT',
        guide_seq: 'GAAAATGTCAGGATGCCTGA',
        pam: 'AGG',
        flank_3p: 'ACA',
        gc_pct: 40.0,
        tm_c: 55.0,
        deepspcas9_score: 33.3,
        crispron_source: 'wsl_real',
        efficiency_score: 85.0,
        warning_message: null,
        duration_seconds: 0.85,
        created_at: '2026-09-30T12:00:00Z',
      })
    })

    render(
      <QueryClientProvider client={queryClient}>
        <SingleScoringCard />
      </QueryClientProvider>
    )

    await userEvent.click(screen.getByText(/填入示例 1/i))
    await userEvent.click(screen.getByRole('button', { name: /开始实时打分/i }))

    await waitFor(() => {
      expect(screen.getByText(/按需组织优先指数/)).toBeInTheDocument()
    })
    // 组织键随参考包：TKS 五组织（根/叶/胶乳/花/花葶），不是莴苣 root/stem/leaf/flower/seed
    for (const t of ['根', '叶', '胶乳', '花', '花葶']) {
      expect(screen.getByText(t)).toBeInTheDocument()
    }
    expect(screen.queryByText('stem')).not.toBeInTheDocument()
    expect(screen.getByText('0.723')).toBeInTheDocument() // 胶乳（时相峰值口径）
    expect(screen.getByText(/时相峰值 TPM/)).toBeInTheDocument()
    // 按需脱靶分档同时展示
    expect(screen.getByText('mis≤3')).toBeInTheDocument()
  })
})
