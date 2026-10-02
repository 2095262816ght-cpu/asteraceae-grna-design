import React from 'react'
import { AlertTriangle } from 'lucide-react'
import { Drawer, Spinner } from '../ui'
import type { CandidateItem } from '../../lib/candidateQuery'
import type { OfftargetSitesResponse } from '../../lib/types'
import { renderAlignedSeq, riskBadgeClass } from './offtargetUtils'

interface OfftargetDrawerProps {
  cand: CandidateItem
  data: OfftargetSitesResponse | null
  loading: boolean
  error: string | null
  onClose: () => void
}

// 脱靶位点明细抽屉（教师反馈 #1）：点击"脱靶数"数字打开，按需加载
export const OfftargetDrawer: React.FC<OfftargetDrawerProps> = ({
  cand,
  data,
  loading,
  error,
  onClose,
}) => {
  const sp = data?.specificity

  return (
    <Drawer
      open
      onClose={onClose}
      width="max-w-3xl"
      closePriority={2}
      title="脱靶位点明细（全基因组 ≤3 错配扫描）"
      subtitle={
        <span className="flex flex-wrap items-center gap-x-2">
          <span className="font-mono font-semibold text-ink">{cand.guide_id}</span>
          <span className="font-mono text-ink-muted">{cand.seq20}</span>
          <span>按 Esc 或点击左侧空白关闭</span>
        </span>
      }
    >
      <div className="space-y-4 px-5 py-4">
        {loading && (
          <div className="glass-inner flex items-center justify-center rounded-card py-10">
            <Spinner label="正在扫描全基因组脱靶位点（Cas-OFFinder 口径，≤3 错配、PAM=NGG）…首次查询可能需要数秒到数分钟，请稍候" />
          </div>
        )}

        {error && (
          <div className="flex items-start space-x-2 rounded-card border border-rose-200 bg-rose-50/80 p-3.5 text-xs text-rose-800">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" />
            <div>
              <span className="font-bold">脱靶明细获取失败：</span>
              <span>{error}</span>
            </div>
          </div>
        )}

        {data && sp && (
          <>
            {/* ① 顶部摘要：profile 四档计数 + 参考基因组 + 特异性汇总 */}
            <div className="glass-inner space-y-2.5 rounded-card p-3.5">
              <div className="grid grid-cols-4 gap-2">
                {[
                  { label: '完全匹配', value: data.profile.exact, cls: 'text-ink' },
                  { label: '1 错配', value: data.profile.mis1, cls: 'text-orange-700' },
                  { label: '2 错配', value: data.profile.mis2, cls: 'text-amber-700' },
                  { label: '3 错配', value: data.profile.mis3, cls: 'text-brand-700' },
                ].map((it) => (
                  <div key={it.label} className="rounded-control border border-line bg-surface p-2 text-center">
                    <div className={`font-mono text-lg font-bold ${it.cls}`}>{it.value}</div>
                    <div className="text-[10px] text-ink-muted">{it.label}</div>
                  </div>
                ))}
              </div>
              <p className="text-2xs text-ink-muted">{data.genome_note}</p>
              <div className="rounded-control border border-brand-100 bg-brand-50/60 p-2.5 text-2xs text-ink">
                <div className="mb-1 font-semibold text-brand-800">guide 级特异性汇总（CRISPOR 口径）</div>
                <div className="flex flex-wrap gap-x-4 gap-y-1">
                  <span>
                    MIT Sguide：<strong className="font-mono">{Number(sp.mit_specificity).toFixed(2)}</strong>
                  </span>
                  <span>
                    CFD 特异性：<strong className="font-mono">{Number(sp.cfd_specificity).toFixed(2)}</strong>
                  </span>
                  <span>计分脱靶位点：{sp.n_offtarget_sites_scored} 个</span>
                  <span>Σ MIT hit：{Number(sp.mit_hit_sum).toFixed(1)}</span>
                  <span>Σ CFD site：{Number(sp.cfd_hit_sum).toFixed(2)}</span>
                </div>
                <p className="mt-1 text-ink-muted">
                  口径：MIT Sguide = 100/(100+ΣhitScore)×100；CFD 特异性 = 100/Σcfd_site
                  {sp.on_target_excluded ? '；已排除候选自身在靶位点，不计入脱靶风险汇总' : ''}
                </p>
              </div>
              {data.sites_truncated && (
                <div className="rounded-control border border-amber-200 bg-amber-50/80 px-2.5 py-1.5 text-2xs text-amber-800">
                  明细已截断，计数仍为全量（位点表格仅展示前 {data.sites.length} 行）
                </div>
              )}
            </div>

            {/* ② 位点明细表格 */}
            <div>
              <div className="mb-1.5 flex items-center justify-between">
                <h4 className="text-xs font-bold text-ink">
                  位点明细（{data.sites.length} 行，正负链分行计数）
                </h4>
                <span className="text-[10px] text-ink-faint">
                  错配位置为 gRNA 方向 1-based（PAM 远端为 1）；错配碱基以红色高亮
                </span>
              </div>
              {data.sites.length === 0 ? (
                <div className="glass-inner rounded-card py-8 text-center text-xs text-ink-muted">
                  未发现 ≤3 错配的脱靶位点（含完全匹配行）。
                </div>
              ) : (
                <div className="overflow-x-auto rounded-card border border-line">
                  <table className="w-full text-left text-2xs">
                    <thead>
                      <tr className="border-b border-line bg-white/30 font-semibold text-ink-muted">
                        <th className="px-2 py-2">风险</th>
                        <th className="px-2 py-2">染色体:坐标</th>
                        <th className="px-2 py-2">链</th>
                        <th className="px-2 py-2" title="错配位置为 gRNA 方向 1-based（PAM 远端为 1）">
                          错配数
                        </th>
                        <th className="px-2 py-2" title="错配位置为 gRNA 方向 1-based（PAM 远端为 1）">
                          错配位置
                        </th>
                        <th className="px-2 py-2 font-mono" title="protospacer20，gRNA 方向 5'→3'，错配碱基高亮">
                          比对序列
                        </th>
                        <th className="px-2 py-2">PAM</th>
                        <th className="px-2 py-2" title="CFD（Doench 2016）单位点分，4 位小数">
                          CFD
                        </th>
                        <th className="px-2 py-2" title="MIT/Hsu 2013 单位点 hit score，2 位小数">
                          MIT
                        </th>
                        <th className="px-2 py-2">所在区域</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.sites.map((s, i) => (
                        <tr
                          key={`${s.chrom}-${s.start}-${s.end}-${s.strand}-${i}`}
                          className={`border-b border-line last:border-b-0 ${s.is_ontarget ? 'bg-white/25' : ''}`}
                        >
                          <td className="px-2 py-2">
                            <span
                              title={s.risk_note}
                              className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-semibold ${riskBadgeClass(
                                s.risk_level
                              )}`}
                            >
                              {s.risk_level}
                            </span>
                          </td>
                          <td className="whitespace-nowrap px-2 py-2 font-mono text-ink-muted">
                            {s.chrom}:{s.start.toLocaleString()}-{s.end.toLocaleString()}
                          </td>
                          <td className="px-2 py-2 font-mono text-ink-muted">{s.strand}</td>
                          <td className="px-2 py-2 font-mono text-ink-muted">{s.mismatch_count}</td>
                          <td className="px-2 py-2 font-mono text-ink-muted">
                            {s.mismatch_positions && s.mismatch_positions.length > 0
                              ? s.mismatch_positions.join(', ')
                              : '—'}
                          </td>
                          <td className="whitespace-nowrap px-2 py-2 font-mono">
                            {renderAlignedSeq(s.protospacer20, s.mismatch_positions)}
                          </td>
                          <td className="px-2 py-2 font-mono font-semibold text-brand-700">{s.pam}</td>
                          <td className="px-2 py-2 font-mono text-ink-muted">
                            {Number(s.cfd_score).toFixed(4)}
                          </td>
                          <td className="px-2 py-2 font-mono text-ink-muted">
                            {Number(s.mit_hit_score).toFixed(2)}
                          </td>
                          <td className="px-2 py-2 text-ink-muted">
                            {s.region_label || '—'}
                            {s.gene_id && (
                              <span className="ml-1 font-mono text-[10px] text-ink-faint">{s.gene_id}</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* ③ 搜索与评分口径 */}
            <div className="glass-inner rounded-card p-3">
              <div className="mb-1 text-2xs font-bold text-ink-muted">搜索与评分口径</div>
              <p className="text-2xs leading-relaxed text-ink-muted">{data.method_note}</p>
            </div>
          </>
        )}
      </div>
    </Drawer>
  )
}
