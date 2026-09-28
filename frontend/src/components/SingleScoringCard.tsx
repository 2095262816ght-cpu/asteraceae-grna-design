import React, { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import {
  Calculator,
  Sparkles,
  AlertTriangle,
  Clock,
  Dna,
  Zap,
  Info,
  CheckCircle2,
} from 'lucide-react'

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
  crispron_source?: string
  efficiency_score?: number
  warning_message?: string | null
  duration_seconds: number
  created_at: string
}

async function requestSingleScore(params: {
  seq30: string
  title?: string
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

export const SingleScoringCard: React.FC = () => {
  const [seqInput, setSeqInput] = useState<string>('')
  const [titleInput, setTitleInput] = useState<string>('')

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

  const mutation = useMutation<ScoringResult, Error, { seq30: string; title?: string }>({
    mutationFn: requestSingleScore,
  })

  const handleFillExample = (exampleSeq: string, title: string) => {
    setSeqInput(exampleSeq)
    setTitleInput(title)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!isValid) return
    mutation.mutate({ seq30: cleanSeq, title: titleInput || undefined })
  }

  const result = mutation.data

  return (
    <div className="space-y-6">
      {/* 序列输入与预测控制卡片 */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4 mb-5">
          <div className="flex items-center space-x-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600">
              <Calculator className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">30nt 靶位点序列实时打分</h3>
              <p className="text-xs text-slate-500">
                规范：4nt 5'侧翼 + 20nt 间隔识别序列 + 3nt NGG PAM + 3nt 3'侧翼 · 严格校验并持久化入库
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
              className="inline-flex items-center rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-100"
            >
              <Sparkles className="mr-1.5 h-3.5 w-3.5 text-amber-500" />
              填入示例 1
            </button>
            <button
              type="button"
              onClick={() =>
                handleFillExample('TGACAGCGTCTCGTTTCACGCTCAAGGTGG', '外显子高活性靶点')
              }
              className="inline-flex items-center rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-100"
            >
              <Sparkles className="mr-1.5 h-3.5 w-3.5 text-emerald-600" />
              填入示例 2
            </button>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <div className="flex justify-between items-center mb-1.5">
              <label htmlFor="seq-input" className="text-xs font-semibold text-slate-700">
                靶位点全长序列 (30bp)
              </label>
              <span
                className={`font-mono text-xs font-semibold ${
                  len === 30 && isValid
                    ? 'text-emerald-600'
                    : len > 0
                    ? 'text-rose-500'
                    : 'text-slate-400'
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
                className={`w-full rounded-xl border px-3.5 py-2.5 font-mono text-sm tracking-widest text-slate-900 shadow-sm focus:outline-none transition-colors ${
                  validationError
                    ? 'border-rose-300 bg-rose-50/20 focus:border-rose-500 focus:ring-1 focus:ring-rose-500'
                    : isValid
                    ? 'border-emerald-300 bg-emerald-50/20 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500'
                    : 'border-slate-200 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500'
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
              <div className="mt-1.5 flex items-center space-x-1.5 text-xs text-emerald-600">
                <CheckCircle2 className="h-3.5 w-3.5 flex-shrink-0" />
                <span>序列规格合规：20nt 引导区 + {cleanSeq.slice(24, 27)} PAM 基序</span>
              </div>
            ) : null}
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pt-2">
            <div className="flex-1 max-w-sm">
              <input
                type="text"
                value={titleInput}
                onChange={(e) => setTitleInput(e.target.value)}
                placeholder="自定义任务备注名称（可选）"
                className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-xs text-slate-700 shadow-sm focus:border-emerald-500 focus:outline-none"
              />
            </div>

            <button
              type="submit"
              disabled={!isValid || mutation.isPending}
              className="inline-flex items-center justify-center rounded-xl bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
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
      </div>

      {/* 预测产物与分子解构展示卡片 */}
      {result && (
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-6">
          <div className="flex flex-wrap items-center justify-between border-b border-slate-100 pb-4">
            <div className="flex items-center space-x-2.5">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600">
                <CheckCircle2 className="h-5 w-5" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-slate-900">{result.title}</h4>
                <p className="text-xs text-slate-500">
                  任务编号: <span className="font-mono">{result.job_id}</span> · 已持久化保存至数据库
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-2 text-xs text-slate-500">
              <Clock className="h-3.5 w-3.5" />
              <span>计算耗时: {result.duration_seconds} 秒</span>
            </div>
          </div>

          {/* 核心分数指标栏 */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {/* 综合相对效率分 */}
            <div className="rounded-xl bg-gradient-to-br from-emerald-50 to-teal-50 border border-emerald-100 p-4">
              <div className="text-xs font-semibold text-emerald-800">
                预测相对效率分 (v2.1 / noB879)
              </div>
              <div className="mt-2 flex items-baseline space-x-2">
                <span className="text-3xl font-extrabold font-mono text-emerald-700">
                  {result.efficiency_score !== undefined && result.efficiency_score !== null
                    ? result.efficiency_score.toFixed(1)
                    : '-'}
                </span>
                <span className="text-xs text-emerald-600 font-medium">/ 100 分</span>
              </div>
              <p className="mt-1 text-[11px] text-emerald-700">
                基于形态二分层选择性 GLMM 金标准排序参考
              </p>
            </div>

            {/* DeepSpCas9 活性 */}
            <div className="rounded-xl bg-slate-50 border border-slate-200/80 p-4">
              <div className="text-xs font-semibold text-slate-600">DeepSpCas9 预测分</div>
              <div className="mt-2 flex items-baseline space-x-2">
                <span className="text-3xl font-extrabold font-mono text-slate-800">
                  {result.deepspcas9_score !== undefined && result.deepspcas9_score !== null
                    ? result.deepspcas9_score.toFixed(1)
                    : '-'}
                </span>
              </div>
              <p className="mt-1 text-[11px] text-slate-500">序列物理特征与深度 CNN 活性打分</p>
            </div>

            {/* 模型来源与降级状态 */}
            <div className="rounded-xl bg-slate-50 border border-slate-200/80 p-4">
              <div className="text-xs font-semibold text-slate-600">CRISPRon 模型来源</div>
              <div className="mt-2">
                <span
                  className={`inline-flex items-center rounded-lg px-2.5 py-1 text-xs font-semibold ${
                    result.crispron_source === 'wsl_real'
                      ? 'bg-emerald-100 text-emerald-800'
                      : 'bg-amber-100 text-amber-800'
                  }`}
                >
                  {result.crispron_source || '未知'}
                </span>
              </div>
              <p className="mt-1 text-[11px] text-slate-500">
                {result.crispron_source === 'wsl_real'
                  ? '真实模型实跑（WSL/容器原生）'
                  : '管线物理经验公式近似式降级值'}
              </p>
            </div>
          </div>

          {/* 30nt 序列物理分子解构 */}
          <div>
            <h5 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2 flex items-center space-x-1.5">
              <Dna className="h-4 w-4 text-emerald-600" />
              <span>30bp 靶位点分子区段解构</span>
            </h5>

            <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4 font-mono">
              <div className="flex flex-wrap items-center gap-2 text-sm sm:text-base">
                <div className="flex flex-col items-center">
                  <span className="rounded bg-slate-200/80 px-2 py-1 text-slate-600">
                    {result.flank_5p}
                  </span>
                  <span className="text-[10px] text-slate-400 mt-1">5' 侧翼 (4nt)</span>
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
                  <span className="rounded bg-emerald-100 px-2.5 py-1 font-extrabold text-emerald-900 border border-emerald-300">
                    {result.pam}
                  </span>
                  <span className="text-[10px] text-emerald-700 font-bold mt-1">PAM (3nt NGG)</span>
                </div>

                <div className="text-slate-300">-</div>

                <div className="flex flex-col items-center">
                  <span className="rounded bg-slate-200/80 px-2 py-1 text-slate-600">
                    {result.flank_3p}
                  </span>
                  <span className="text-[10px] text-slate-400 mt-1">3' 侧翼 (3nt)</span>
                </div>
              </div>

              {/* 生物物理特征参数 */}
              <div className="mt-4 pt-3 border-t border-slate-200 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div>
                  <span className="text-slate-500">GC 含量:</span>{' '}
                  <strong className="text-slate-800">{result.gc_pct.toFixed(1)}%</strong>
                </div>
                <div>
                  <span className="text-slate-500">退火温度 Tm:</span>{' '}
                  <strong className="text-slate-800">{result.tm_c.toFixed(1)} °C</strong>
                </div>
                <div>
                  <span className="text-slate-500">种子区 (Seed):</span>{' '}
                  <strong className="text-slate-800 font-mono">{result.guide_seq.slice(14, 20)}</strong>
                </div>
                <div>
                  <span className="text-slate-500">PAM 首位 (N):</span>{' '}
                  <strong className="text-slate-800 font-mono">{result.pam[0]}</strong>
                </div>
              </div>
            </div>
          </div>

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
