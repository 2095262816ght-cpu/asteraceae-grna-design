import React, { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import {
  Sparkles,
  AlertTriangle,
  Clock,
  Dna,
  Zap,
  Info,
  FolderPlus,
} from 'lucide-react'
import { GeneratedIcon } from './icons/GeneratedIcon'
import { DownloadButton } from './DownloadButton'
import { ReferenceBundleImporter, type BundleSummary } from './ReferenceBundleImporter'

export interface ExpressionFitness {
  poly_t: boolean
  poly_t_filtered?: boolean
  five_prime_g: boolean
  mfe_kcal: number | null
  mfe_risk: boolean
  mfe_threshold?: number | null
  note?: string | null
}

export interface ScoringResult {
  job_id: string
  title: string
  seq30: string
  flank_5p: string
  guide_seq: string
  pam: string
  flank_3p: string
  gc_pct: number
  tm_c: number
  deepspcas9_score?: number
  crispron_score?: number
  crispron_source?: string
  efficiency_score?: number
  features?: Record<string, number>
  expression_fitness?: ExpressionFitness | null
  warning_message?: string | null
  duration_seconds: number
  created_at: string
}

async function requestSingleScore(params: {
  seq30: string
  title?: string
  bundle_id?: string
}): Promise<ScoringResult> {
  const res = await fetch('/api/v1/scoring/single', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '打分请求失败' }))
    throw new Error(err.detail || '打分计算失败')
  }
  return res.json()
}

export interface AnnotateResult {
  state: 'precomputed' | 'annotated' | 'custom' | 'invalid'
  seq30: string
  species: string
  bundle_id?: string
  bundle_name?: string
  gene_id?: string | null
  region_type?: string | null
  annotation_note?: string
  hit?: { chrom: string; start: number; end: number; strand: string } | null
  candidate?: Record<string, number | string | null> | null
  offtarget?: { exact: number; mis1: number; mis2: number; mis3: number } | null
  priority_scores?: Record<string, number> | null
  priority_note?: string | null
  percentile?: number | null
  percentile_basis?: string | null
  missing_requirements?: string[]
  tks_expression?: {
    matched_id: string
    stage_means: Record<string, Record<string, number>>
    peak_stage_latex?: string | null
    peak_stage_root?: string | null
    recommended_window: string
    evidence_note: string
  } | null
  error?: string
}

async function requestAnnotate(params: {
  seq30: string
  bundle_id: string
  efficiency_score?: number
  compute_offtarget: boolean
}): Promise<AnnotateResult> {
  const res = await fetch('/api/v1/sequence/annotate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
  if (!res.ok) throw new Error('回贴注释请求失败')
  return res.json()
}

export const SingleScoringCard: React.FC = () => {
  const [seqInput, setSeqInput] = useState<string>('')
  const [titleInput, setTitleInput] = useState<string>('')
  const [bundleId, setBundleId] = useState<string>('lettuce')
  const [showImporter, setShowImporter] = useState<boolean>(false)
  const [annotateRes, setAnnotateRes] = useState<AnnotateResult | null>(null)

  const bundlesQuery = useQuery<BundleSummary[]>({
    queryKey: ['reference-bundles'],
    queryFn: async () => {
      const res = await fetch('/api/v1/sequence/bundles')
      if (!res.ok) throw new Error('参考包清单加载失败')
      return res.json()
    },
  })
  const bundles = Array.isArray(bundlesQuery.data) ? bundlesQuery.data : []
  const currentBundle = bundles.find((b) => b.id === bundleId)

  const cleanSeq = seqInput.trim().toUpperCase()
  const len = cleanSeq.length

  // 序列即时语法校验
  let validationError: string | null = null
  if (len > 0) {
    if (len !== 30) {
      validationError = `序列长度为 ${len} nt，须精确为 30bp (4nt 上游 + 20nt Guide + 3nt PAM + 3nt 下游)`
    } else if (!/^[ACGT]{30}$/.test(cleanSeq)) {
      validationError = '含非法字符，仅支持 A / C / G / T 碱基'
    } else if (cleanSeq.slice(25, 27) !== 'GG') {
      validationError = '第 25-27 位须为 NGG PAM 基序（即第 26、27 位须为 GG）'
    }
  }

  const isValid = len === 30 && validationError === null

  const mutation = useMutation<ScoringResult, Error, { seq30: string; title?: string; bundle_id?: string }>({
    mutationFn: requestSingleScore,
  })

  // 基因组回贴三态注释（C4/C5/C6）：compute_offtarget=true 时含按需脱靶与优先指数
  const annotateMutation = useMutation<
    AnnotateResult,
    Error,
    { computeOfftarget: boolean }
  >({
    mutationFn: ({ computeOfftarget }) => {
      const seq = mutation.data?.seq30
      if (!seq) throw new Error('无可用序列')
      return requestAnnotate({
        seq30: seq,
        bundle_id: bundleId,
        efficiency_score: mutation.data?.efficiency_score ?? undefined,
        compute_offtarget: computeOfftarget,
      })
    },
    onSuccess: (data) => setAnnotateRes(data),
  })

  React.useEffect(() => {
    if (mutation.data) {
      setAnnotateRes(null)
      annotateMutation.mutate({ computeOfftarget: false })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mutation.data?.seq30, bundleId])

  const handleFillExample = (exampleSeq: string, title: string) => {
    setSeqInput(exampleSeq)
    setTitleInput(title)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!isValid) return
    mutation.mutate({ seq30: cleanSeq, title: titleInput || undefined, bundle_id: bundleId })
  }

  const result = mutation.data

  return (
    <div className="space-y-6">
      {/* 序列输入与预测控制卡片 */}
      <div className="card p-6">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4 mb-5">
          <div className="flex items-center space-x-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
              <GeneratedIcon name="calculator" className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-ink">30nt 靶位点序列实时打分</h3>
              <p className="text-xs text-ink-muted">
                规范：4nt 5'侧翼 + 20nt 间隔识别序列 + 3nt NGG PAM + 3nt 3'侧翼 · 严格校验并持久化入库
              </p>
              <p className="text-[11px] text-brand-700">
                支持任意物种 30bp 靶位点（橡胶草 / 莴苣等）：v2.1 生产模型以橡胶草 Hi-TOM 实测金标准训练，橡胶草序列属同物种对口预测 · 效率分为同一基因内候选的相对排序参考，非绝对 indel% 承诺
              </p>
            </div>
          </div>

          {/* 快速填入示例按钮 */}
          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={() =>
                handleFillExample('TTTGTGGATTCCGGTAGAATCTGATGGAAT', 'Lsat_675191 代表靶位点')
              }
              className="inline-flex items-center rounded-lg border border-line bg-surface-sunken px-2.5 py-1.5 text-xs font-medium text-ink-muted hover:bg-slate-100"
            >
              <Sparkles className="mr-1.5 h-3.5 w-3.5 text-amber-500" />
              填入示例 1
            </button>
            <button
              type="button"
              onClick={() =>
                handleFillExample('TGACAGCGTCTCGTTTCACGCTCAAGGTGG', '外显子高活性靶点')
              }
              className="inline-flex items-center rounded-lg border border-line bg-surface-sunken px-2.5 py-1.5 text-xs font-medium text-ink-muted hover:bg-slate-100"
            >
              <Sparkles className="mr-1.5 h-3.5 w-3.5 text-brand-600" />
              填入示例 2
            </button>
            <button
              type="button"
              onClick={() =>
                handleFillExample('ATATGAAAATGTCAGGATGCCTGAAGGACA', '橡胶草 LG07.3296 实测靶点 (Hi-TOM)')
              }
              className="inline-flex items-center rounded-lg border border-brand-200 bg-brand-50 px-2.5 py-1.5 text-xs font-medium text-brand-700 hover:bg-brand-100"
            >
              <Sparkles className="mr-1.5 h-3.5 w-3.5 text-brand-600" />
              橡胶草示例
            </button>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <div className="flex justify-between items-center mb-1.5">
              <label htmlFor="seq-input" className="text-xs font-semibold text-ink-muted">
                靶位点全长序列 (30bp)
              </label>
              <span
                className={`font-mono text-xs font-semibold ${
                  len === 30 && isValid
                    ? 'text-brand-600'
                    : len > 0
                    ? 'text-rose-500'
                    : 'text-ink-faint'
                }`}
              >
                {len} / 30 nt
              </span>
            </div>

            <div className="relative">
              <input
                id="seq-input"
                type="text"
                value={seqInput}
                onChange={(e) => setSeqInput(e.target.value.toUpperCase().replace(/[^A-Z]/g, ''))}
                placeholder="例如：TTTGTGGATTCCGGTAGAATCTGATGGAAT"
                className={`w-full rounded-xl border px-3.5 py-2.5 font-mono text-sm tracking-widest text-ink shadow-sm focus:outline-none transition-colors ${
                  validationError
                    ? 'border-rose-300 bg-rose-50/20 focus:border-rose-500 focus:ring-1 focus:ring-rose-500'
                    : isValid
                    ? 'border-brand-300 bg-brand-50/20 focus:border-brand-500 focus:ring-1 focus:ring-brand-500'
                    : 'border-line focus:border-brand-500 focus:ring-1 focus:ring-brand-500'
                }`}
              />
            </div>

            {/* 校验提示 */}
            {validationError ? (
              <div className="mt-1.5 flex items-center space-x-1.5 text-xs text-rose-600">
                <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0" />
                <span>{validationError}</span>
              </div>
            ) : isValid ? (
              <div className="mt-1.5 flex items-center space-x-1.5 text-xs text-brand-600">
                <GeneratedIcon name="checkCircle" className="h-3.5 w-3.5 flex-shrink-0" />
                <span>序列规格合规：20nt 引导区 + {cleanSeq.slice(24, 27)} PAM 基序</span>
              </div>
            ) : null}
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pt-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs text-ink-muted">回贴参考包:</span>
              <div className="inline-flex flex-wrap rounded-lg border border-line bg-surface p-0.5">
                {(bundles.length > 0
                  ? bundles
                  : [{ id: 'lettuce', display_name: '莴苣 (LsT2T)', kind: 'preset' } as BundleSummary]
                ).map((b) => (
                  <button
                    key={b.id}
                    type="button"
                    onClick={() => setBundleId(b.id)}
                    className={`px-2.5 py-1.5 text-xs rounded-md transition-colors ${
                      bundleId === b.id ? 'bg-brand-600 text-white font-semibold' : 'text-ink-muted hover:bg-surface-sunken'
                    }`}
                  >
                    {b.display_name}
                  </button>
                ))}
              </div>
              <button
                type="button"
                onClick={() => setShowImporter(!showImporter)}
                className="inline-flex items-center rounded-lg border border-brand-200 bg-brand-50 px-2.5 py-1.5 text-xs font-medium text-brand-700 hover:bg-brand-100"
              >
                <FolderPlus className="mr-1 h-3.5 w-3.5" />
                导入参考包
              </button>
              {currentBundle && !currentBundle.fasta_available && (
                <span className="text-[11px] text-amber-600">该参考包基因组文件缺失，回贴不可用</span>
              )}
            </div>
            <div className="flex-1 max-w-sm">
              <input
                type="text"
                value={titleInput}
                onChange={(e) => setTitleInput(e.target.value)}
                placeholder="自定义任务备注名称（可选）"
                className="w-full rounded-lg border border-line px-3 py-1.5 text-xs text-ink-muted shadow-sm focus:border-brand-500 focus:outline-none"
              />
            </div>

            <button
              type="submit"
              disabled={!isValid || mutation.isPending}
              className="inline-flex items-center justify-center rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              {mutation.isPending ? (
                <>
                  <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"></div>
                  <span>正在调用模型推理...</span>
                </>
              ) : (
                <>
                  <Zap className="mr-1.5 h-4 w-4" />
                  <span>开始实时打分</span>
                </>
              )}
            </button>
          </div>
        </form>

        {mutation.isError && (
          <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-3.5 text-xs text-rose-700">
            <strong>预测执行失败：</strong> {mutation.error.message}
          </div>
        )}

        {showImporter && (
          <div className="mt-4">
            <ReferenceBundleImporter
              onRegistered={(id) => {
                setBundleId(id)
                setShowImporter(false)
                bundlesQuery.refetch()
              }}
            />
          </div>
        )}
      </div>

      {/* 预测产物与分子解构展示卡片 */}
      {result && (
        <div className="card space-y-6 p-6">
          <div className="flex flex-wrap items-center justify-between border-b border-slate-100 pb-4">
            <div className="flex items-center space-x-2.5">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
                <GeneratedIcon name="checkCircle" className="h-5 w-5" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-ink">{result.title}</h4>
                <p className="text-xs text-ink-muted">
                  任务编号: <span className="font-mono">{result.job_id}</span> · 已持久化保存至数据库
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="flex items-center space-x-2 text-xs text-ink-muted">
                <Clock className="h-3.5 w-3.5" />
                <span>计算耗时: {result.duration_seconds} 秒</span>
              </div>

              <DownloadButton
                url={`/api/v1/scoring/jobs/${result.job_id}/export?format=xlsx&bundle_id=${encodeURIComponent(bundleId)}`}
                className="inline-flex items-center gap-1 rounded-lg border border-brand-200 bg-brand-50 px-2.5 py-1.5 text-xs font-medium text-brand-700 hover:bg-brand-100 transition-colors disabled:opacity-60"
                title="导出打分结果与多组学注释（缺啥写啥：缺失原因/所需数据/所用参考包/百分位口径）"
              >
                导出结果 (xlsx)
              </DownloadButton>
              <DownloadButton
                url={`/api/v1/scoring/jobs/${result.job_id}/export?format=csv&bundle_id=${encodeURIComponent(bundleId)}`}
                title="CSV 格式导出（仅数据表）"
              >
                CSV
              </DownloadButton>
            </div>
          </div>

          {/* 核心分数指标栏 */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {/* 综合相对效率分 */}
            <div className="rounded-xl bg-gradient-to-br from-brand-50 to-teal-50 border border-brand-100 p-4">
              <div className="text-xs font-semibold text-brand-800">
                预测相对效率分 (v2.1 / noB879)
              </div>
              <div className="mt-2 flex items-baseline space-x-2">
                <span className="text-3xl font-extrabold font-mono text-brand-700">
                  {result.efficiency_score?.toFixed(1) ?? '-'}
                </span>
                <span className="text-xs text-brand-600 font-medium">/ 100 分</span>
              </div>
              <p className="mt-1 text-[11px] text-brand-700">
                基于形态二分层选择性 GLMM 金标准排序参考
              </p>
            </div>

            {/* DeepSpCas9 活性 */}
            <div className="glass-inner rounded-xl p-4">
              <div className="text-xs font-semibold text-ink-muted">DeepSpCas9 预测分</div>
              <div className="mt-2 flex items-baseline space-x-2">
                <span className="text-3xl font-extrabold font-mono text-ink">
                  {result.deepspcas9_score?.toFixed(1) ?? '-'}
                </span>
              </div>
              <p className="mt-1 text-[11px] text-ink-muted">序列物理特征与深度 CNN 活性打分</p>
            </div>

            {/* 模型来源与降级状态 */}
            <div className="glass-inner rounded-xl p-4">
              <div className="text-xs font-semibold text-ink-muted">CRISPRon 预测分与来源</div>
              <div className="mt-2 flex items-center space-x-2">
                <span className="text-3xl font-extrabold font-mono text-ink">
                  {result.crispron_score?.toFixed(1) ?? '-'}
                </span>
                <span
                  className={`inline-flex items-center rounded-lg px-2.5 py-1 text-xs font-semibold ${
                    result.crispron_source === 'wsl_real'
                      ? 'bg-brand-100 text-brand-800'
                      : result.crispron_source
                        ? 'bg-amber-100 text-amber-800'
                        : 'bg-surface-sunken text-ink-faint'
                  }`}
                >
                  {result.crispron_source || '未计算'}
                </span>
              </div>
              <p className="mt-1 text-[11px] text-ink-muted">
                {result.crispron_source === 'wsl_real'
                  ? '真实模型实跑（WSL/容器原生）'
                  : result.crispron_source
                    ? '管线物理经验公式近似式降级值'
                    : '模型推理未产出 CRISPRon 分，如实标注未计算'}
              </p>
            </div>
          </div>

          {/* 30nt 序列物理分子解构 */}
          <div>
            <h5 className="text-xs font-bold text-ink-muted tracking-wider mb-2 flex items-center space-x-1.5">
              <Dna className="h-4 w-4 text-brand-600" />
              <span>30bp 靶位点分子区段解构</span>
            </h5>

            <div className="glass-inner rounded-xl p-4 font-mono">
              <div className="flex flex-wrap items-center gap-2 text-sm sm:text-base">
                <div className="flex flex-col items-center">
                  <span className="rounded bg-slate-200/80 px-2 py-1 text-ink-muted">
                    {result.flank_5p}
                  </span>
                  <span className="text-[10px] text-ink-faint mt-1">5' 侧翼 (4nt)</span>
                </div>

                <div className="text-slate-300">-</div>

                <div className="flex flex-col items-center">
                  <span className="rounded bg-amber-100 px-3 py-1 font-bold text-amber-900 border border-amber-300/60">
                    {result.guide_seq}
                  </span>
                  <span className="text-[10px] text-amber-700 font-semibold mt-1">
                    引导序列 Guide (20nt)
                  </span>
                </div>

                <div className="text-slate-300">-</div>

                <div className="flex flex-col items-center">
                  <span className="rounded bg-brand-100 px-2.5 py-1 font-extrabold text-brand-900 border border-brand-300">
                    {result.pam}
                  </span>
                  <span className="text-[10px] text-brand-700 font-bold mt-1">PAM (3nt NGG)</span>
                </div>

                <div className="text-slate-300">-</div>

                <div className="flex flex-col items-center">
                  <span className="rounded bg-slate-200/80 px-2 py-1 text-ink-muted">
                    {result.flank_3p}
                  </span>
                  <span className="text-[10px] text-ink-faint mt-1">3' 侧翼 (3nt)</span>
                </div>
              </div>

              {/* 生物物理特征参数 */}
              <div className="mt-4 pt-3 border-t border-line grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div>
                  <span className="text-ink-muted">GC 含量:</span>{' '}
                  <strong className="text-ink">{result.gc_pct.toFixed(1)}%</strong>
                </div>
                <div>
                  <span className="text-ink-muted">退火温度 Tm:</span>{' '}
                  <strong className="text-ink">{result.tm_c.toFixed(1)} °C</strong>
                </div>
                <div>
                  <span className="text-ink-muted">种子区 (Seed):</span>{' '}
                  <strong className="text-ink font-mono">{result.guide_seq.slice(14, 20)}</strong>
                </div>
                <div>
                  <span className="text-ink-muted">PAM 首位 (N):</span>{' '}
                  <strong className="text-ink font-mono">{result.pam[0]}</strong>
                </div>
              </div>
            </div>
          </div>

          {/* 表达适配度（U6 表达）小面板：Poly-T / 5'G / MFE 三指标 */}
          <div>
            <h5 className="text-xs font-bold text-ink-muted tracking-wider mb-2 flex items-center space-x-1.5">
              <Dna className="h-4 w-4 text-brand-600" />
              <span>表达适配度（U6 表达）</span>
            </h5>
            <div className="glass-inner rounded-xl p-4">
              {result.expression_fitness ? (
                <>
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-3 text-xs">
                    {/* ① Poly-T：U6 转录终止信号 */}
                    <div
                      className={`rounded-lg border px-3 py-2 ${
                        result.expression_fitness.poly_t
                          ? 'border-rose-200 bg-rose-50'
                          : 'border-brand-200 bg-brand-50'
                      }`}
                    >
                      <div className="text-[11px] font-semibold text-ink-muted">Poly-T（U6 终止信号）</div>
                      {result.expression_fitness.poly_t ? (
                        <p className="mt-1 flex items-start space-x-1.5 font-semibold text-rose-700">
                          <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0 mt-0.5" />
                          <span>含 TTTT（U6 转录终止，应避免）</span>
                        </p>
                      ) : (
                        <p className="mt-1 font-semibold text-brand-700">无 TTTT ✓</p>
                      )}
                      {result.expression_fitness.poly_t_filtered && (
                        <p className="mt-0.5 text-[10px] text-ink-faint">（poly-T 经侧翼过滤判定）</p>
                      )}
                    </div>

                    {/* ② 5'G：U6 转录起始偏好 */}
                    <div
                      className={`rounded-lg border px-3 py-2 ${
                        result.expression_fitness.five_prime_g
                          ? 'border-brand-200 bg-brand-50'
                          : 'border-line bg-surface'
                      }`}
                    >
                      <div className="text-[11px] font-semibold text-ink-muted">5' 端碱基（U6 起始偏好）</div>
                      {result.expression_fitness.five_prime_g ? (
                        <p className="mt-1 font-semibold text-brand-700">G-start ✓（U6 起始偏好）</p>
                      ) : (
                        <p className="mt-1 font-semibold text-ink-muted">5' 非 G</p>
                      )}
                    </div>

                    {/* ③ MFE：spacer 自折叠自由能 */}
                    <div
                      className={`rounded-lg border px-3 py-2 ${
                        result.expression_fitness.mfe_risk
                          ? 'border-rose-200 bg-rose-50'
                          : 'border-line bg-surface'
                      }`}
                    >
                      <div className="text-[11px] font-semibold text-ink-muted">MFE（spacer 自折叠）</div>
                      {result.expression_fitness.mfe_kcal === null ||
                      result.expression_fitness.mfe_kcal === undefined ? (
                        <p className="mt-1 font-semibold text-ink-muted">ViennaRNA 不可用</p>
                      ) : (
                        <>
                          <p
                            className={`mt-1 font-mono text-lg font-bold ${
                              result.expression_fitness.mfe_risk ? 'text-rose-700' : 'text-brand-700'
                            }`}
                          >
                            {result.expression_fitness.mfe_kcal.toFixed(2)}{' '}
                            <span className="font-sans text-[11px] font-medium text-ink-muted">kcal/mol</span>
                          </p>
                          {result.expression_fitness.mfe_risk ? (
                            <p className="mt-0.5 flex items-start space-x-1 font-semibold text-rose-600">
                              <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0 mt-0.5" />
                              <span>&Delta;G &lt; -5 kcal/mol 自折叠风险</span>
                            </p>
                          ) : (
                            <p className="mt-0.5 text-brand-600">自折叠风险可接受</p>
                          )}
                        </>
                      )}
                      <p className="mt-1 text-[10px] text-ink-faint">
                        -5 kcal/mol 为风险警示线（参考阈值，非绝对判据）
                      </p>
                    </div>
                  </div>

                  {result.expression_fitness.note && (
                    <p className="mt-3 text-[11px] leading-relaxed text-ink-muted">
                      {result.expression_fitness.note}
                    </p>
                  )}
                </>
              ) : (
                /* 旧响应未返回 expression_fitness：降级显示占位 */
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-3 text-xs">
                  {['Poly-T（U6 终止信号）', "5' 端碱基（U6 起始偏好）", 'MFE（spacer 自折叠）'].map(
                    (label) => (
                      <div key={label} className="rounded-lg border border-line bg-surface px-3 py-2">
                        <div className="text-[11px] font-semibold text-ink-muted">{label}</div>
                        <p className="mt-1 font-mono text-lg font-bold text-ink-faint">—</p>
                      </div>
                    )
                  )}
                </div>
              )}
            </div>
          </div>

          {/* 10 维模型特征向量（定义单一来源：features_common.seq_features，与训练/推理同口径） */}
          {result.features && (
            <div>
              <h5 className="text-xs font-bold text-ink-muted tracking-wider mb-2 flex items-center space-x-1.5">
                <Info className="h-4 w-4 text-brand-600" />
                <span>10 维模型特征向量（单一来源：features_common.seq_features）</span>
              </h5>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                {[
                  ['gc_total', 'GC 总量'],
                  ['gc_seed', 'GC 种子区'],
                  ['tm', 'Tm (NN, °C)'],
                  ['poly_t', 'poly-T (0/1)'],
                  ['pam_n_A', 'PAM N=A'],
                  ['pam_n_C', 'PAM N=C'],
                  ['pam_n_G', 'PAM N=G'],
                  ['pam_n_T', 'PAM N=T'],
                ].map(([k, label]) => (
                  <div key={k} className="rounded-lg bg-surface-sunken border border-line px-2.5 py-1.5">
                    <span className="text-ink-muted">{label}:</span>{' '}
                    <strong className="text-ink font-mono">
                      {result.features && result.features[k] !== undefined
                        ? Number(result.features[k]).toFixed(3)
                        : '-'}
                    </strong>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 基因组回贴三态注释（C4 命中复用内嵌 / C5 按需脱靶 / C6 按需多组学） */}
          {(annotateRes || annotateMutation.isPending) && (
            <div className="glass-inner rounded-xl p-4 space-y-3">
              <div className="flex items-center justify-between">
                <h5 className="text-xs font-bold text-ink-muted tracking-wider">
                  基因组回贴注释（{annotateRes?.bundle_name ?? currentBundle?.display_name ?? '参考包'}）
                </h5>
                {annotateRes && (annotateRes.state === 'annotated' || annotateRes.state === 'custom') && (
                  <button
                    type="button"
                    onClick={() => annotateMutation.mutate({ computeOfftarget: true })}
                    disabled={annotateMutation.isPending}
                    className="inline-flex items-center rounded-lg border border-brand-200 bg-brand-50 px-2.5 py-1.5 text-xs font-medium text-brand-700 hover:bg-brand-100 disabled:opacity-50"
                  >
                    {annotateMutation.isPending ? '脱靶扫描中…' : '计算脱靶 + 优先指数'}
                  </button>
                )}
              </div>

              {annotateMutation.isPending && (
                <div className="flex items-center gap-2 text-xs text-ink-muted">
                  <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-brand-500 border-t-transparent"></div>
                  <span>正在运行基因组回贴与按需脱靶扫描（全基因组比对，约 1 分钟）…</span>
                </div>
              )}

              {annotateRes && !annotateMutation.isPending && (
                <>
                  <div className="flex items-start gap-2">
                    <span
                      className={`inline-flex shrink-0 items-center rounded-lg px-2.5 py-1 text-xs font-semibold ${
                        annotateRes.state === 'precomputed'
                          ? 'bg-brand-100 text-brand-800'
                          : annotateRes.state === 'annotated'
                          ? 'bg-blue-100 text-blue-800'
                          : 'bg-amber-100 text-amber-800'
                      }`}
                    >
                      {annotateRes.state === 'precomputed'
                        ? '命中预计算候选'
                        : annotateRes.state === 'annotated'
                        ? '基因组回贴命中'
                        : '自定义序列（未锚定）'}
                    </span>
                    <span className="text-xs text-ink-muted">{annotateRes.annotation_note}</span>
                  </div>

                  {annotateRes.state === 'precomputed' && annotateRes.candidate && (
                    <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-xs">
                      {[
                        ['脱靶 mis≤3', annotateRes.candidate.offtarget_count_mis3],
                        ['优先指数(叶)', annotateRes.candidate.priority_score_leaf],
                        ['危害指数(叶)', annotateRes.candidate.hazard_leaf],
                        ['表达证据', annotateRes.candidate.expression_status],
                        ['面板内位点', annotateRes.candidate.n_intra_panel_sites],
                      ].map(([label, val]) => (
                        <div key={String(label)} className="rounded-lg bg-surface border border-line px-2.5 py-1.5">
                          <span className="text-ink-muted">{label}:</span>{' '}
                          <strong className="text-ink font-mono">{val === null || val === undefined ? '—' : String(val)}</strong>
                        </div>
                      ))}
                    </div>
                  )}

                  {(annotateRes.state === 'annotated' || annotateRes.state === 'custom') && (
                    <>
                      {annotateRes.offtarget && (
                        <div>
                          <div className="text-[11px] font-semibold text-ink-muted mb-1">
                            按需脱靶分档（口径同 Cas-OFFinder 聚合）
                          </div>
                          <div className="grid grid-cols-4 gap-2 text-xs">
                            {[
                              ['exact', annotateRes.offtarget.exact],
                              ['mis≤1', annotateRes.offtarget.mis1],
                              ['mis≤2', annotateRes.offtarget.mis2],
                              ['mis≤3', annotateRes.offtarget.mis3],
                            ].map(([label, val]) => (
                              <div key={String(label)} className="rounded-lg bg-surface border border-line px-2.5 py-1.5 text-center">
                                <span className="text-ink-muted">{label}</span>
                                <p className="font-mono font-bold text-ink">{String(val)}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      {annotateRes.priority_scores && (
                        <div>
                          <div className="text-[11px] font-semibold text-ink-muted mb-1">
                            按需组织优先指数（方案3 公式与 Tab 1 同源；组织键随参考包表达口径）
                          </div>
                          <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-xs">
                            {Object.entries(annotateRes.priority_scores).map(([t, v]) => (
                              <div key={t} className="rounded-lg bg-surface border border-line px-2.5 py-1.5 text-center">
                                <span className="text-ink-muted">{t}</span>
                                <p className="font-mono font-bold text-brand-700">
                                  {typeof v === 'number' ? v.toFixed(3) : '—'}
                                </p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      {annotateRes.priority_note && (
                        <p className="text-[11px] text-ink-muted">{annotateRes.priority_note}</p>
                      )}
                      {annotateRes.percentile !== null && annotateRes.percentile !== undefined && (
                        <div className="rounded-lg bg-surface border border-line px-2.5 py-1.5 text-xs">
                          <span className="text-ink-muted">效率百分位:</span>{' '}
                          <strong className="text-ink font-mono">
                            {(annotateRes.percentile * 100).toFixed(1)}%
                          </strong>
                          {annotateRes.percentile_basis && (
                            <span className="ml-2 text-[11px] text-ink-muted">{annotateRes.percentile_basis}</span>
                          )}
                        </div>
                      )}
                      {annotateRes.missing_requirements && annotateRes.missing_requirements.length > 0 && (
                        <div className="rounded-lg border border-amber-200 bg-amber-50 px-2.5 py-1.5 text-[11px] text-amber-800">
                          <strong>缺数据说明：</strong>补齐以下数据后可计算对应指标：
                          {annotateRes.missing_requirements.join('；')}
                        </div>
                      )}
                      {annotateRes.tks_expression && (
                        <div>
                          <div className="text-[11px] font-semibold text-ink-muted mb-1">
                            橡胶草 S1–S9 时相表达（{annotateRes.tks_expression.matched_id} · 方案6）
                          </div>
                          <div className="flex flex-wrap gap-2 text-[11px] mb-1.5">
                            <span className="rounded-lg bg-blue-50 border border-blue-200 px-2 py-0.5 text-blue-700">
                              胶乳峰值 {annotateRes.tks_expression.peak_stage_latex || '—'}
                            </span>
                            <span className="rounded-lg bg-blue-50 border border-blue-200 px-2 py-0.5 text-blue-700">
                              根峰值 {annotateRes.tks_expression.peak_stage_root || '—'}
                            </span>
                            <span className="rounded-lg bg-brand-50 border border-brand-200 px-2 py-0.5 text-brand-700 font-semibold">
                              推荐转化窗口 {annotateRes.tks_expression.recommended_window}
                            </span>
                          </div>
                          <div className="overflow-x-auto">
                            <table className="text-[11px] w-full">
                              <thead>
                                <tr className="text-ink-muted">
                                  <th className="px-1.5 py-0.5 text-left font-medium">阶段</th>
                                  {['S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8', 'S9'].map((s) => (
                                    <th key={s} className="px-1.5 py-0.5 text-right font-medium">{s}</th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody>
                                {[
                                  ['gen', '根'],
                                  ['jiaoru', '胶乳'],
                                  ['ye', '叶'],
                                  ['hua', '花'],
                                  ['huating', '花葶'],
                                ].map(([k, label]) => (
                                  <tr key={k} className="border-t border-slate-100">
                                    <td className="px-1.5 py-0.5 text-ink-muted">{label}</td>
                                    {['S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8', 'S9'].map((s) => {
                                      const v = annotateRes.tks_expression!.stage_means[s]?.[k]
                                      return (
                                        <td key={s} className="px-1.5 py-0.5 text-right font-mono text-ink">
                                          {v !== undefined ? v.toFixed(1) : '—'}
                                        </td>
                                      )
                                    })}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                          <p className="mt-1 text-[11px] text-ink-muted">{annotateRes.tks_expression.evidence_note}</p>
                        </div>
                      )}
                    </>
                  )}
                </>
              )}
            </div>
          )}

          {result.warning_message && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-3.5 text-xs text-amber-800 flex items-start space-x-2">
              <Info className="h-4 w-4 text-amber-600 flex-shrink-0 mt-0.5" />
              <span>{result.warning_message}</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
