import React from 'react'
import { AlertTriangle, BookOpen } from 'lucide-react'
import { Table, Thead, Tbody, Tr, Th, Td, Pagination } from '../ui'
import { TISSUE_NAMES, type TargetTissue } from '../../lib/tissues'
import type { CandidateItem, CandidatesResponse } from '../../lib/candidateQuery'

export const TOTAL_COLS = 18

interface CandidateTableProps {
  data: CandidatesResponse | undefined
  loading: boolean
  isFetching: boolean
  page: number
  pageSize: number
  targetTissue: TargetTissue
  currentRegionType: 'all' | 'exon' | 'promoter' | 'none'
  selectedIds: Set<number>
  selectedGuideId: string | null
  computingIds: Set<number>
  isAllSelected: boolean
  onSelectGuide: (guideId: string | null) => void
  onToggleOne: (id: number) => void
  onToggleAll: () => void
  onPage: (page: number) => void
  onOpenMethods: () => void
  onOpenOfftarget: (cand: CandidateItem) => void
  onComputeConfirm: (cand: CandidateItem) => void
  onRestoreRegions: () => void
}

// 识别列（checkbox/#/靶点 ID）sticky 固定：宽度与左偏移成对定义
const STICKY = [
  { width: 40, left: 0 },
  { width: 48, left: 40 },
  { width: 104, left: 88 },
]

// 候选 gRNA 靶位点推荐清单：两层分组表头 + 18 列逐列说明（列名与手册 3.2.8 逐字一致）
// memo：导出进度/计算中等高频状态更新时不重渲染 18 列大表
const CandidateTableInner: React.FC<CandidateTableProps> = ({
  data,
  loading,
  isFetching,
  page,
  pageSize,
  targetTissue,
  currentRegionType,
  selectedIds,
  selectedGuideId,
  computingIds,
  isAllSelected,
  onSelectGuide,
  onToggleOne,
  onToggleAll,
  onPage,
  onOpenMethods,
  onOpenOfftarget,
  onComputeConfirm,
  onRestoreRegions,
}) => {
  const items = data?.items || []
  const summary = data?.gene_summary

  return (
    <div className="card overflow-hidden">
      <div className="flex items-center justify-between border-b border-line px-6 py-4">
        <div className="flex items-center space-x-2">
          <h3 className="text-base font-bold text-ink">候选 gRNA 靶位点推荐清单</h3>
          <button
            type="button"
            onClick={onOpenMethods}
            title="查看算法、版本、参数与参考基因组口径说明"
            className="inline-flex items-center gap-1 rounded-control border border-line bg-surface px-2.5 py-1 text-xs font-medium text-ink-muted shadow-sm transition-colors hover:bg-surface-sunken hover:text-brand-700"
          >
            <BookOpen className="h-3.5 w-3.5" />
            方法与版本
          </button>
          {isFetching && <span className="animate-pulse text-xs text-ink-faint">(更新中...)</span>}
        </div>
        <div className="text-xs text-ink-muted">
          共匹配到 <strong className="text-brand-600">{data?.total || 0}</strong> 条符合条件的靶点
          {(summary?.poly_t_filtered_count ?? 0) > 0 && (
            <span
              className="ml-2 inline-block rounded border border-amber-200 bg-amber-50 px-1.5 py-0.5 text-2xs text-amber-700"
              title="U6 启动子（RNA Pol III）转录遇 TTTT 提前终止，含 poly-T 信号的候选已在枚举阶段硬过滤，不参与列表与排序"
            >
              另有 {summary?.poly_t_filtered_count} 条含 TTTT poly-T 终止信号已过滤
            </span>
          )}
        </div>
      </div>

      <div className="overflow-x-auto">
        <Table density="compact">
          <caption className="sr-only">候选 gRNA 靶位点推荐清单</caption>
          <Thead>
            {/* 第一层：分组表头（纯视觉增行，不替代列名行） */}
            <Tr hover={false} className="bg-slate-100/80">
              <Th colSpan={3} align="center" sticky={{ left: 0 }} className="text-[10px] text-ink-faint">
                识别
              </Th>
              <Th colSpan={3} align="center" className="text-[10px] text-ink-faint">
                定位
              </Th>
              <Th colSpan={3} align="center" className="text-[10px] text-ink-faint">
                序列
              </Th>
              <Th colSpan={3} align="center" className="text-[10px] text-ink-faint">
                活性
              </Th>
              <Th colSpan={1} align="center" className="text-[10px] text-ink-faint">
                脱靶
              </Th>
              <Th colSpan={4} align="center" className="text-[10px] text-ink-faint">
                多组学
              </Th>
              <Th colSpan={1} align="center" className="text-[10px] text-ink-faint">
                评分
              </Th>
            </Tr>
            {/* 第二层：18 列列名（文案冻结） */}
            <Tr hover={false} className="bg-white/25">
              <Th align="center" sticky={STICKY[0]} width={STICKY[0].width}>
                <input
                  type="checkbox"
                  aria-label="全选当前页"
                  checked={isAllSelected}
                  onChange={onToggleAll}
                  className="h-3.5 w-3.5 cursor-pointer rounded border-slate-300 accent-brand-600 text-brand-600 focus:ring-brand-500"
                />
              </Th>
              <Th sticky={STICKY[1]} width={STICKY[1].width}>
                #
              </Th>
              <Th sticky={STICKY[2]} width={STICKY[2].width} className="shadow-[2px_0_4px_-2px_rgb(15_23_42_/_0.12)]">
                靶点 ID
              </Th>
              <Th>方向</Th>
              <Th className="whitespace-nowrap">基因组物理坐标</Th>
              <Th>区域</Th>
              <Th
                title="序列为 gRNA 方向 5'→3'：4nt 侧翼 + 20nt Guide + 3nt PAM + 3nt 侧翼"
                className="font-mono"
              >
                30nt 靶位点序列 (Guide + PAM)
              </Th>
              <Th title="PAM 按 gRNA 方向 5'→3' 恒写作 NGG；负链靶点在基因组正链对应位置读作 CCN">
                PAM
              </Th>
              <Th>GC %</Th>
              <Th
                title="表达适配度：含 TTTT poly-T 终止信号的候选已硬过滤；5' 端为 G 提高 U6 转录效率（G-start 徽章）；MFE 为 20nt spacer 自折叠最小自由能（ViennaRNA RNAfold，不含 scaffold 骨架），ΔG < -5 kcal/mol 标红警示"
              >
                表达适配
              </Th>
              <Th title="DeepSpCas9 深度学习模型预测的 on-target 切割活性分（0–1），业界常用基准；越高预期在靶切割效率越高">
                DeepSpCas9 活性
              </Th>
              <Th title="CRISPRon 模型预测的 on-target 切割活性分；真实模型不可用时降级为经验近似式（详见导出表《指标方法说明》）">
                CRISPRon 活性
              </Th>
              <Th
                title="全基因组潜在脱靶位点计数（错配 1–3 累计，不含完全匹配行）；点击数字查看脱靶位点明细（坐标/错配位置/CFD/MIT 评分/区域）"
              >
                脱靶数 (&le;3)
              </Th>
              <Th align="right">
                组织优先 ({TISSUE_NAMES[targetTissue]})
              </Th>
              <Th align="right">
                功能危害 ({TISSUE_NAMES[targetTissue]})
              </Th>
              <Th align="center">表达证据</Th>
              <Th>着丝粒</Th>
              <Th
                align="right"
                title="on-target 效率分：自训练 Stacking 元模型（v2.1）预测的在靶切割活性综合分，0–100，由 DeepSpCas9 活性、CRISPRon 活性、GC、Tm、polyT 等 10 维序列特征构成；悬停每行分数可查看两个成分分"
              >
                on-target 效率分 (v2.1)
              </Th>
            </Tr>
          </Thead>
          <Tbody>
            {loading ? (
              <Tr hover={false} className="bg-white/15">
                <Td colSpan={TOTAL_COLS} className="py-12 text-center text-ink-faint">
                  <div className="flex items-center justify-center space-x-2">
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-brand-600 border-t-transparent"></div>
                    <span>正在检索候选 gRNA 靶位点...</span>
                  </div>
                </Td>
              </Tr>
            ) : !data?.items || data.items.length === 0 ? (
              <Tr hover={false} className="bg-white/15">
                <Td colSpan={TOTAL_COLS} className="py-12 text-center text-ink-muted">
                  {currentRegionType === 'none' ? (
                    <div className="flex flex-col items-center justify-center space-y-2">
                      <span className="text-sm font-semibold text-ink">当前未勾选任何功能元件</span>
                      <span className="text-xs text-ink-faint">
                        外显子与启动子均处于未勾选状态。请在上方的【功能元件过滤】中勾选对应区段以查看候选位点。
                      </span>
                      <button
                        type="button"
                        onClick={onRestoreRegions}
                        className="mt-1 inline-flex items-center rounded-control border border-brand-200 bg-brand-50 px-3 py-1.5 text-xs font-semibold text-brand-700 transition-colors hover:bg-brand-100"
                      >
                        一键恢复全选 (外显子 + 启动子)
                      </button>
                    </div>
                  ) : (
                    '未找到符合当前过滤条件的候选 gRNA 靶点，请尝试降低最低效率分限制或关闭着丝粒过滤项。'
                  )}
                </Td>
              </Tr>
            ) : (
              items.map((cand, idx) => {
                const globalIdx = (page - 1) * pageSize + idx + 1
                const eff = cand.efficiency_score ?? 0
                const effColor =
                  eff >= 70
                    ? 'bg-brand-50 text-brand-700 ring-brand-600/20'
                    : eff >= 40
                    ? 'bg-amber-50 text-amber-700 ring-amber-600/20'
                    : 'bg-slate-100 text-slate-700 ring-slate-400/20'

                // 高亮显示 30nt：前4nt(灰) + 20nt Guide(加黑) + 3nt PAM(绿色粗体) + 3nt(灰)
                const flank5 = cand.seq30.slice(0, 4)
                const guide = cand.seq20
                const pam = cand.pam
                const flank3 = cand.seq30.slice(27, 30)

                const isSelected = selectedGuideId === cand.guide_id

                return (
                  <Tr
                    key={cand.id}
                    tabIndex={0}
                    onClick={() => onSelectGuide(isSelected ? null : cand.guide_id)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        onSelectGuide(isSelected ? null : cand.guide_id)
                      }
                    }}
                    className={
                      isSelected
                        ? 'cursor-pointer bg-sky-50/70 font-medium ring-1 ring-inset ring-sky-300'
                        : 'cursor-pointer bg-white/15'
                    }
                  >
                    <Td align="center" sticky={STICKY[0]} width={STICKY[0].width} onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        aria-label={`选择靶点 ${cand.guide_id}`}
                        checked={selectedIds.has(cand.id)}
                        onChange={() => onToggleOne(cand.id)}
                        className="h-3.5 w-3.5 cursor-pointer rounded border-slate-300 accent-brand-600 text-brand-600 focus:ring-brand-500"
                      />
                    </Td>
                    <Td sticky={STICKY[1]} width={STICKY[1].width} className="font-mono text-ink-faint">
                      {globalIdx}
                    </Td>
                    <Td
                      sticky={STICKY[2]}
                      width={STICKY[2].width}
                      className="font-semibold text-ink shadow-[2px_0_4px_-2px_rgb(15_23_42_/_0.12)]"
                    >
                      {cand.guide_id}
                    </Td>

                    <Td>
                      <span
                        className={`inline-block rounded px-1.5 py-0.5 font-mono text-2xs font-bold ${
                          cand.strand === '+' ? 'bg-sky-50 text-sky-700' : 'bg-rose-50 text-rose-700'
                        }`}
                      >
                        {cand.strand}
                      </span>
                    </Td>
                    <Td numeric className="whitespace-nowrap font-mono text-ink-muted">
                      {cand.start.toLocaleString()} - {cand.end.toLocaleString()}
                    </Td>
                    <Td>
                      <span
                        className={`inline-flex items-center whitespace-nowrap rounded-full px-2 py-0.5 text-2xs font-semibold ring-1 ring-inset ${
                          cand.region_type === 'exon'
                            ? 'bg-sky-50 text-sky-700 ring-sky-600/20'
                            : 'bg-purple-50 text-purple-700 ring-purple-600/20'
                        }`}
                      >
                        {cand.region_type === 'exon' ? '外显子 (exon)' : '启动子 (promoter)'}
                      </span>
                    </Td>
                    <Td className="whitespace-nowrap font-mono text-xs">
                      <span className="text-ink-faint">{flank5}</span>
                      <span className="rounded bg-amber-50 px-1 font-semibold text-ink">{guide}</span>
                      <span className="mx-0.5 rounded bg-brand-100 px-1 font-bold text-brand-700">{pam}</span>
                      <span className="text-ink-faint">{flank3}</span>
                    </Td>
                    <Td className="font-mono font-bold text-brand-700">{cand.pam}</Td>
                    <Td numeric className="font-mono text-ink-muted">
                      {cand.gc_pct.toFixed(1)}%
                    </Td>

                    {/* 表达适配度（教师反馈 #2）：MFE + 5'G 徽章横排 */}
                    <Td title={cand.expression_fitness_note || undefined}>
                      <span className="flex items-center gap-1.5 whitespace-nowrap">
                        {cand.mfe_kcal !== undefined && cand.mfe_kcal !== null ? (
                          <span
                            className={`inline-flex items-center gap-1 whitespace-nowrap font-mono text-2xs font-semibold ${
                              cand.mfe_risk ? 'text-rose-600' : 'text-ink-muted'
                            }`}
                          >
                            {cand.mfe_kcal.toFixed(1)} kcal/mol
                            {cand.mfe_risk && (
                              <span
                                title="ΔG < -5 kcal/mol：自折叠可能抑制靶向活性"
                                className="inline-flex items-center rounded bg-rose-100 px-1 py-0.5 text-[10px] font-bold text-rose-700"
                              >
                                <AlertTriangle className="h-3 w-3" />
                              </span>
                            )}
                          </span>
                        ) : (
                          <span
                            className="whitespace-nowrap text-2xs text-ink-faint"
                            title="ViennaRNA 不可用：无法计算 spacer 自折叠 MFE"
                          >
                            — <span className="text-[10px]">ViennaRNA 不可用</span>
                          </span>
                        )}
                        <span
                          className={`inline-block whitespace-nowrap rounded border px-1.5 py-0.5 text-[10px] font-semibold ${
                            cand.five_prime_g
                              ? 'border-brand-200/70 bg-brand-50 text-brand-700'
                              : 'border-line bg-surface-sunken text-ink-faint'
                          }`}
                        >
                          G-start
                        </span>
                      </span>
                    </Td>
                    <Td numeric className="font-mono text-ink-muted" title="DeepSpCas9 模型预测的 on-target 切割活性分（0–1）">
                      {cand.deepspcas9_score !== undefined && cand.deepspcas9_score !== null ? (
                        cand.deepspcas9_score.toFixed(3)
                      ) : (
                        <span className="text-ink-faint">—</span>
                      )}
                    </Td>
                    <Td numeric className="font-mono text-ink-muted" title="CRISPRon 模型预测的 on-target 切割活性分">
                      {cand.crispron_score !== undefined && cand.crispron_score !== null ? (
                        cand.crispron_score.toFixed(2)
                      ) : (
                        <span className="text-ink-faint">—</span>
                      )}
                    </Td>
                    <Td className="font-mono">
                      {computingIds.has(cand.id) ? (
                        <span
                          className="inline-flex items-center gap-1.5 whitespace-nowrap text-brand-600"
                          title="正在计算脱靶：全基因组扫描（Cas-OFFinder 口径，≤3 错配、PAM=NGG），约 1 分钟/条，请稍候"
                        >
                          <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" />
                          <span className="text-2xs font-semibold">计算中</span>
                        </span>
                      ) : cand.offtarget_count_mis3 === null || cand.offtarget_count_mis3 === undefined ? (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation()
                            onComputeConfirm(cand)
                          }}
                          title="未计算：未对该 guide 做全基因组脱靶扫描，不能读作'已验证无脱靶'；点击可计算脱靶并查看位点明细"
                          className="whitespace-nowrap text-ink-faint underline decoration-dotted underline-offset-2 transition-colors hover:decoration-solid hover:text-brand-700"
                        >
                          未计算
                        </button>
                      ) : (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation()
                            onOpenOfftarget(cand)
                          }}
                          title="点击查看脱靶位点明细（坐标/错配位置/CFD/MIT 评分/区域）"
                          className={`whitespace-nowrap font-semibold underline decoration-dotted underline-offset-2 transition-colors hover:decoration-solid hover:text-brand-700 ${
                            cand.offtarget_count_mis3 > 0 ? 'text-amber-600' : 'text-brand-600'
                          }`}
                        >
                          {cand.offtarget_count_mis3}
                        </button>
                      )}
                    </Td>

                    {/* 组织优先指数 (方案3) */}
                    <Td align="right">
                      {cand.priority_score !== undefined && cand.priority_score !== null ? (
                        <span className="inline-flex items-center rounded-md bg-brand-50 px-2 py-0.5 font-mono tabular-nums text-2xs font-bold text-brand-800 ring-1 ring-inset ring-brand-600/20">
                          {cand.priority_score.toFixed(3)}
                        </span>
                      ) : (
                        <span className="font-mono text-2xs text-ink-faint">—</span>
                      )}
                    </Td>

                    {/* 功能性脱靶危害 (方案5) */}
                    <Td align="right">
                      {cand.hazard_score !== undefined && cand.hazard_score !== null ? (
                        <span
                          className={`inline-flex items-center rounded-md px-1.5 py-0.5 font-mono text-2xs font-semibold ${
                            cand.hazard_score > 0
                              ? 'bg-rose-50 text-rose-700 ring-1 ring-inset ring-rose-600/20'
                              : 'text-ink-muted'
                          }`}
                        >
                          {cand.hazard_score.toFixed(3)}
                        </span>
                      ) : (
                        <span className="font-mono text-2xs text-ink-faint">—</span>
                      )}
                    </Td>

                    {/* 表达证据状态 */}
                    <Td align="center">
                      {cand.expression_status_display ? (
                        <span
                          title={cand.expression_evidence_note}
                          className={`inline-block whitespace-nowrap rounded border px-2 py-0.5 text-[10px] font-medium ${
                            cand.expression_status === 'mapped'
                              ? 'border-brand-200/60 bg-brand-50 text-brand-700'
                              : cand.expression_status === 'mapped_cluster'
                              ? 'border-indigo-200/60 bg-indigo-50 text-indigo-700'
                              : cand.expression_status === 'mapped_scaffold'
                              ? 'border-cyan-200/60 bg-cyan-50 text-cyan-700'
                              : cand.expression_status === 'unassessed'
                              ? 'border-line bg-surface-sunken text-ink-muted'
                              : 'border-amber-200/60 bg-amber-50 text-amber-700'
                          }`}
                        >
                          {cand.expression_status_display}
                        </span>
                      ) : (
                        <span className="text-[10px] text-ink-faint">—</span>
                      )}
                    </Td>

                    <Td>
                      {cand.is_centromere ? (
                        <span className="inline-flex items-center rounded bg-rose-50 px-1.5 py-0.5 text-[10px] font-medium text-rose-600">
                          着丝粒
                        </span>
                      ) : (
                        <span className="text-[10px] text-ink-faint">否</span>
                      )}
                    </Td>
                    <Td align="right">
                      <span
                        className={`inline-flex items-center rounded-control px-2.5 py-1 font-mono tabular-nums text-xs font-bold ring-1 ring-inset ${effColor}`}
                        title={`on-target 效率分（Stacking 元模型 v2.1，0–100）\n成分：DeepSpCas9 ${
                          cand.deepspcas9_score !== undefined && cand.deepspcas9_score !== null
                            ? cand.deepspcas9_score.toFixed(3)
                            : '—'
                        } · CRISPRon ${
                          cand.crispron_score !== undefined && cand.crispron_score !== null
                            ? cand.crispron_score.toFixed(2)
                            : '—'
                        }\n预测的是在靶切割活性，与脱靶数互相独立，需两者综合评价`}
                      >
                        {eff > 0 ? eff.toFixed(2) : '-'}
                      </span>
                    </Td>
                  </Tr>
                )
              })
            )}
          </Tbody>
        </Table>
      </div>

      {/* 分页控制栏 */}
      {data && data.total_pages > 1 && (
        <div className="border-t border-line bg-white/25 px-6 py-3.5">
          <Pagination
            page={page}
            pageSize={pageSize}
            total={data.total}
            totalPages={data.total_pages}
            onPrev={() => onPage(Math.max(1, page - 1))}
            onNext={() => onPage(Math.min(data.total_pages, page + 1))}
          />
        </div>
      )}
    </div>
  )
}

export const CandidateTable = React.memo(CandidateTableInner)
