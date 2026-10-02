import React from 'react'
import { AlertTriangle } from 'lucide-react'
import { Dialog, Spinner } from '../ui'
import type { MethodsInfo } from '../../lib/types'

interface MethodsDialogProps {
  open: boolean
  onClose: () => void
  data: MethodsInfo | null
  loading: boolean
  error: string | null
}

// 方法与版本弹窗（教师反馈 #4/#5）：算法、版本、参数与参考基因组口径
export const MethodsDialog: React.FC<MethodsDialogProps> = ({ open, onClose, data, loading, error }) => (
  <Dialog
    open={open}
    onClose={onClose}
    size="lg"
    className="max-w-3xl"
    closePriority={1}
    title="方法与版本 · 算法口径与参考基因组说明"
    subtitle="效率模型、脱靶检测、表达适配度与基因结构注释的方法、参数与版本（透明性声明）"
  >
    <div className="space-y-3 px-5 py-4">
      {loading && (
        <div className="glass-inner flex items-center justify-center rounded-card py-10">
          <Spinner label="正在加载方法与版本说明…" />
        </div>
      )}

      {error && (
        <div className="flex items-start space-x-2 rounded-card border border-rose-200 bg-rose-50/80 p-3.5 text-xs text-rose-800">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" />
          <div>
            <span className="font-bold">方法与版本信息获取失败：</span>
            <span>{error}</span>
          </div>
        </div>
      )}

      {data && (
        <div className="space-y-3">
          {/* 效率分模型 */}
          <section className="glass-inner rounded-card p-4">
            <h4 className="mb-2 border-b border-line pb-1.5 text-xs font-bold text-ink">
              效率分模型（on-target 效率分）
            </h4>
            <div className="space-y-1.5 text-2xs leading-relaxed text-ink-muted">
              <p>
                <span className="font-semibold text-ink">名称：</span>
                {data.efficiency_model.name}
              </p>
              <p>
                <span className="font-semibold text-ink">类型：</span>
                {data.efficiency_model.kind}
              </p>
              <div>
                <span className="font-semibold text-ink">组成成分：</span>
                <ul className="mt-1 list-inside list-disc space-y-0.5 pl-1">
                  {(data.efficiency_model.components || []).map((c, i) => (
                    <li key={i}>{c}</li>
                  ))}
                </ul>
              </div>
              <p>
                <span className="font-semibold text-ink">验证：</span>
                {data.efficiency_model.validation}
              </p>
              <p>
                <span className="font-semibold text-ink">模型卡：</span>
                <span className="font-mono text-ink-muted">{data.efficiency_model.model_card}</span>
              </p>
              <p>
                <span className="font-semibold text-ink">模型谱系：</span>
                {data.efficiency_model.lineage_note}
              </p>
            </div>
          </section>

          {/* 脱靶检测 */}
          <section className="glass-inner rounded-card p-4">
            <h4 className="mb-2 border-b border-line pb-1.5 text-xs font-bold text-ink">
              脱靶检测（全基因组扫描与位点评分）
            </h4>
            <div className="space-y-1.5 text-2xs leading-relaxed text-ink-muted">
              <p>
                <span className="font-semibold text-ink">搜索方法：</span>
                {data.offtarget.search}
              </p>
              <div>
                <span className="font-semibold text-ink">参数：</span>
                <ul className="mt-1 list-inside list-disc space-y-0.5 pl-1">
                  <li>PAM：{data.offtarget.params?.pam}</li>
                  <li>gRNA 长度：{data.offtarget.params?.gRNA_length}</li>
                  <li>最大错配数：{data.offtarget.params?.max_mismatches}</li>
                  <li>链处理：{data.offtarget.params?.strands}</li>
                </ul>
              </div>
              <div>
                <span className="font-semibold text-ink">位点评分：</span>
                <ul className="mt-1 list-inside list-disc space-y-0.5 pl-1">
                  {(data.offtarget.site_scores || []).map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              </div>
              <p>
                <span className="font-semibold text-ink">guide 级特异性：</span>
                {data.offtarget.guide_specificity}
              </p>
              <p>
                <span className="font-semibold text-ink">风险分档：</span>
                {data.offtarget.risk_note}
              </p>
            </div>
          </section>

          {/* 表达适配度 */}
          <section className="glass-inner rounded-card p-4">
            <h4 className="mb-2 border-b border-line pb-1.5 text-xs font-bold text-ink">
              表达适配度（poly-T / 5'G / MFE / GC）
            </h4>
            <div className="space-y-1.5 text-2xs leading-relaxed text-ink-muted">
              <p>
                <span className="font-semibold text-ink">poly-T：</span>
                {data.expression_fitness.poly_t}
              </p>
              <p>
                <span className="font-semibold text-ink">5' 端 G：</span>
                {data.expression_fitness.five_prime_g}
              </p>
              <p>
                <span className="font-semibold text-ink">MFE 自折叠：</span>
                {data.expression_fitness.mfe}
              </p>
              <p>
                <span className="font-semibold text-ink">GC 含量：</span>
                {data.expression_fitness.gc}
              </p>
            </div>
          </section>

          {/* 基因结构注释 */}
          <section className="glass-inner rounded-card p-4">
            <h4 className="mb-2 border-b border-line pb-1.5 text-xs font-bold text-ink">基因结构注释</h4>
            <div className="space-y-1.5 text-2xs leading-relaxed text-ink-muted">
              <p>
                <span className="font-semibold text-ink">结构来源：</span>
                {data.gene_structure.source}
              </p>
              <p>
                <span className="font-semibold text-ink">蛋白功能域：</span>
                {data.gene_structure.protein_domains}
              </p>
            </div>
          </section>

          {/* 参考基因组 */}
          <section className="glass-inner rounded-card p-4">
            <h4 className="mb-2 border-b border-line pb-1.5 text-xs font-bold text-ink">
              参考基因组（{(data.reference_genomes || []).length} 个参考包）
            </h4>
            <ul className="space-y-1.5">
              {(data.reference_genomes || []).map((g) => (
                <li
                  key={g.id}
                  className="flex flex-wrap items-center gap-2 rounded-control border border-line bg-surface-sunken/70 px-2.5 py-1.5 text-2xs"
                >
                  <span className="font-mono font-semibold text-ink">{g.id}</span>
                  <span className="text-ink-muted">{g.display_name}</span>
                  <span
                    className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${
                      g.fasta_available
                        ? 'bg-brand-50 text-brand-700 border border-brand-200/70'
                        : 'bg-slate-100 text-ink-faint border border-line'
                    }`}
                  >
                    FASTA {g.fasta_available ? '可用' : '缺失'}
                  </span>
                  <span
                    className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${
                      g.gff_available
                        ? 'bg-brand-50 text-brand-700 border border-brand-200/70'
                        : 'bg-slate-100 text-ink-faint border border-line'
                    }`}
                  >
                    GFF {g.gff_available ? '可用' : '缺失'}
                  </span>
                </li>
              ))}
            </ul>
          </section>

          {/* 免责声明 */}
          <div className="rounded-card border border-amber-200 bg-amber-50/80 p-3 text-2xs leading-relaxed text-amber-900">
            <span className="font-bold">免责声明：</span>
            {data.disclaimer}
          </div>
        </div>
      )}
    </div>
  </Dialog>
)
