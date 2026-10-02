import React from 'react'
import { AlertTriangle, Info } from 'lucide-react'
import { GeneratedIcon } from '../icons/GeneratedIcon'
import { TISSUE_NAMES, type TargetTissue } from '../../lib/tissues'
import type { GeneExpressionData } from '../../lib/types'

const BAR_TISSUES: TargetTissue[] = ['Root', 'Stem', 'Leaf', 'Flower', 'Seed']

interface ExpressionDashboardProps {
  data: GeneExpressionData | undefined
  loading: boolean
  targetTissue: TargetTissue
}

// 多组织表达看板与靶向适宜性诊断 (方案1 & 方案3联动)
export const ExpressionDashboard: React.FC<ExpressionDashboardProps> = ({
  data,
  loading,
  targetTissue,
}) => {
  const maxTpm = Math.max(...BAR_TISSUES.map((t) => data?.tpm_dict?.[t] ?? 0), 1.0)

  return (
    <div className="card p-5">
      <div className="mb-4 flex items-center justify-between border-b border-line pb-3">
        <div className="flex items-center space-x-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-control border border-teal-100/60 bg-teal-50 text-teal-600">
            <GeneratedIcon name="activity" className="h-4 w-4" />
          </div>
          <div>
            <h4 className="flex items-center gap-2 text-sm font-bold text-ink">
              <span>多组织表达看板与靶向适宜性诊断</span>
              <span className="font-mono text-2xs font-normal text-ink-faint">
                (莴苣 v1.1c 表达矩阵 · 根/茎/叶/花/种子)
              </span>
            </h4>
          </div>
        </div>
        {loading && (
          <span className="flex animate-pulse items-center gap-1 text-xs text-ink-faint">
            <div className="h-3 w-3 animate-spin rounded-full border-2 border-brand-600 border-t-transparent"></div>
            加载表达谱...
          </span>
        )}
      </div>

      {/* 顶部元数据指标块（无框，靠分隔线分栏） */}
      <div className="mb-5 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="py-1 sm:border-l sm:border-line sm:pl-5 sm:first:border-l-0 sm:first:pl-0">
          <span className="mb-0.5 block text-2xs font-medium text-ink-muted">v1.1c 注释映射</span>
          <div className="flex items-baseline gap-1.5">
            <span className="font-mono tabular-nums text-sm font-bold text-ink">
              {data?.is_mappable ? data.lsa_id : '无对应注释'}
            </span>
            {data?.is_mappable && data.tier && (
              <span className="font-mono text-[10px] text-ink-faint">
                (tier {data.tier} · 票比 {((data.lsa_vote_frac ?? 0) * 100).toFixed(0)}%)
              </span>
            )}
          </div>
        </div>

        <div className="py-1 sm:border-l sm:border-line sm:pl-5">
          <span className="mb-0.5 block text-2xs font-medium text-ink-muted">最高表达组织</span>
          <div className="flex items-baseline gap-1.5">
            <span className="text-sm font-bold text-ink">{data?.is_mappable ? data.top_tissue : '—'}</span>
            {data?.is_mappable && data.top_tpm !== undefined && (
              <span className="font-mono text-xs font-semibold text-brand-600">
                {data.top_tpm.toFixed(1)} TPM
              </span>
            )}
          </div>
        </div>

        <div className="py-1 sm:border-l sm:border-line sm:pl-5">
          <span className="mb-0.5 flex items-center gap-1 text-2xs font-medium text-ink-muted">
            <span>组织特异性 τ</span>
            <span className="text-[10px] font-normal text-ink-faint">(τ→1特异, τ→0泛表达)</span>
          </span>
          <div className="flex items-baseline gap-1.5">
            <span className="font-mono tabular-nums text-sm font-bold text-ink">
              {data?.is_mappable && data.tau !== undefined ? data.tau.toFixed(2) : '—'}
            </span>
          </div>
        </div>
      </div>

      {/* 5 组织 TPM 表达柱状图 */}
      {data?.is_mappable && (
        <div className="mb-4 space-y-2">
          <div className="mb-1 flex items-center justify-between text-xs text-ink-muted">
            <span className="font-semibold text-ink-muted">5 组织转录丰度对比 (TPM)</span>
            <span className="text-2xs text-ink-faint">当前选中的目标组织高亮突出</span>
          </div>
          {BAR_TISSUES.map((t) => {
            const val = data.tpm_dict?.[t] ?? 0
            const isSelectedTissue = targetTissue === t
            const pct = Math.max((val / maxTpm) * 100, 2)

            return (
              <div key={t} className="flex items-center space-x-3 text-xs">
                <span className="flex w-10 shrink-0 items-center justify-between font-medium text-ink-muted">
                  <span>{TISSUE_NAMES[t]}</span>
                </span>
                <div className="relative flex h-5 flex-1 items-center overflow-hidden rounded-full bg-slate-100">
                  <div
                    className={`h-full rounded-full transition-all duration-300 ${
                      isSelectedTissue
                        ? 'bg-gradient-to-r from-brand-400 to-teal-400'
                        : 'bg-gradient-to-r from-slate-300 to-slate-400'
                    }`}
                    style={{ width: `${pct}%` }}
                  ></div>
                  {isSelectedTissue && (
                    <span className="absolute right-2 rounded-full bg-brand-100/90 px-1.5 py-0.5 text-[10px] font-bold text-brand-800">
                      目标组织
                    </span>
                  )}
                </div>
                <span
                  className={`w-20 shrink-0 text-right font-mono tabular-nums font-semibold ${
                    isSelectedTissue ? 'font-bold text-brand-700' : 'text-ink-muted'
                  }`}
                >
                  {val.toFixed(2)} TPM
                </span>
              </div>
            )
          })}
        </div>
      )}

      {/* 靶向适宜性诊断 Banner */}
      {data?.is_mappable ? (
        (() => {
          const val = data.tpm_dict?.[targetTissue] ?? 0
          if (val < 0.5) {
            return (
              <div className="flex items-start space-x-2.5 rounded-card border border-amber-200 bg-amber-50/80 p-3.5 text-xs text-amber-900">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
                <div>
                  <span className="font-bold">⚠️ 弱表型警示：</span>
                  <span>
                    该基因在所选组织（{TISSUE_NAMES[targetTissue]}）中转录静默（TPM {val.toFixed(2)} &lt; 0.5），CRISPR
                    敲除可能无法诱导明显生物学表型。
                  </span>
                </div>
              </div>
            )
          } else if (val >= 10.0) {
            return (
              <div className="flex items-start space-x-2.5 rounded-card border border-brand-200 bg-brand-50/80 p-3.5 text-xs text-brand-900">
                <GeneratedIcon name="checkCircle" className="mt-0.5 h-4 w-4 shrink-0" />
                <div>
                  <span className="font-bold">✅ 适宜靶向：</span>
                  <span>
                    该基因在所选组织（{TISSUE_NAMES[targetTissue]}）中高度转录（TPM {val.toFixed(1)} ≥
                    10.0），染色质处于开放状态，预期编辑响应好。
                  </span>
                </div>
              </div>
            )
          } else {
            return (
              <div className="flex items-start space-x-2.5 rounded-card border border-sky-200 bg-sky-50/80 p-3.5 text-xs text-sky-900">
                <Info className="mt-0.5 h-4 w-4 shrink-0 text-sky-600" />
                <div>
                  <span className="font-bold">ℹ️ 中等表达：</span>
                  <span>
                    所选组织（{TISSUE_NAMES[targetTissue]}）TPM {val.toFixed(2)}，介于 0.5 与 10.0
                    之间；表型预期中等，建议结合蛋白水平验证。
                  </span>
                </div>
              </div>
            )
          }
        })()
      ) : (
        <div className="flex items-start space-x-2.5 rounded-card border border-amber-200 bg-amber-50/80 p-3.5 text-xs text-amber-900">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
          <div>
            <span className="font-bold">⚠️ 表达证据缺失：</span>
            <span>
              {data?.unmappable_reason || '该基因座在莴苣 v1.1c 表达矩阵中无对应注释，不展示假定表达值。'}
            </span>
          </div>
        </div>
      )}

      {/* 串联重复簇与未挂载 scaffold 说明 */}
      {data && (data.n_cluster > 1 || data.scaffold_evidence) && (
        <div className="mt-2.5 space-y-1 text-2xs text-ink-muted">
          {data.n_cluster > 1 && (
            <div>
              ℹ️ 该基因座为 NLR 串联重复簇：主映射 {data.lsa_id}（投票占比{' '}
              {((data.lsa_vote_frac ?? 0) * 100).toFixed(0)}%），簇成员 {data.lsa_cluster}；看板展示主映射基因的表达。
            </div>
          )}
          {data.scaffold_evidence && (
            <div>
              ℹ️ 映射证据来自未挂载 scaffold（{data.scaffold_evidence}）：该基因座在 v1.1c 中未挂载到染色体上。
            </div>
          )}
        </div>
      )}
    </div>
  )
}
