import React, { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { FolderUp, Plus, Trash2, Upload, PackagePlus } from 'lucide-react'

interface TissueRow {
  label: string
  column: string
}

export interface BundleSummary {
  id: string
  display_name: string
  kind: 'preset' | 'imported'
  fasta_available: boolean
  gff_available: boolean
  expression_available: boolean
  expression_layout: string
  expression_id_rule: string
  gene_source: string
  tissue_columns: Record<string, string>
  notes?: string | null
}

async function uploadFile(file: File): Promise<string> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch('/api/v1/sequence/bundles/upload', { method: 'POST', body: form })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '上传失败' }))
    throw new Error(err.detail || '上传失败')
  }
  const data = await res.json()
  return data.path as string
}

async function registerBundle(payload: Record<string, unknown>): Promise<BundleSummary> {
  const res = await fetch('/api/v1/sequence/bundles', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '注册失败' }))
    throw new Error(typeof err.detail === 'string' ? err.detail : '参考包注册失败')
  }
  return res.json()
}

const inputCls =
  'w-full rounded-lg border border-slate-200 px-3 py-1.5 text-xs text-slate-700 shadow-sm focus:border-emerald-500 focus:outline-none'

export const ReferenceBundleImporter: React.FC<{
  onRegistered: (bundleId: string) => void
}> = ({ onRegistered }) => {
  const [bundleId, setBundleId] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [fastaPath, setFastaPath] = useState('')
  const [gffPath, setGffPath] = useState('')
  const [exprPath, setExprPath] = useState('')
  const [tissueRows, setTissueRows] = useState<TissueRow[]>([{ label: '叶', column: '' }])
  const [idRule, setIdRule] = useState<'same' | 'evm_tu_to_model'>('same')
  const [notes, setNotes] = useState('')
  const [allowOverwrite, setAllowOverwrite] = useState(false)
  const [uploadTarget, setUploadTarget] = useState<'fasta' | 'gff' | 'expr' | null>(null)

  const uploadMutation = useMutation<string, Error, { file: File; target: 'fasta' | 'gff' | 'expr' }>({
    mutationFn: ({ file }) => uploadFile(file),
    onSuccess: (path, vars) => {
      if (vars.target === 'fasta') setFastaPath(path)
      else if (vars.target === 'gff') setGffPath(path)
      else setExprPath(path)
      setUploadTarget(null)
    },
  })

  const registerMutation = useMutation<BundleSummary, Error, void>({
    mutationFn: () =>
      registerBundle({
        bundle_id: bundleId.trim(),
        display_name: displayName.trim() || bundleId.trim(),
        fasta_path: fastaPath.trim(),
        gff_path: gffPath.trim() || null,
        expression_path: exprPath.trim() || null,
        tissue_columns: Object.fromEntries(
          tissueRows.filter((r) => r.label.trim() && r.column.trim()).map((r) => [r.label.trim(), r.column.trim()])
        ),
        expression_id_rule: idRule,
        notes: notes.trim() || null,
        allow_overwrite: allowOverwrite,
      }),
    onSuccess: (data) => onRegistered(data.id),
  })

  const handleUpload = (target: 'fasta' | 'gff' | 'expr') => (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    if (file.size > 50 * 1024 * 1024) {
      alert('直传仅支持 ≤50MB 小文件。大基因组请放到服务端 cs_pipeline/data/reference_genomes/ 后直接填路径。')
      return
    }
    setUploadTarget(target)
    uploadMutation.mutate({ file, target })
  }

  const canSubmit = bundleId.trim() !== '' && fastaPath.trim() !== '' && !registerMutation.isPending

  return (
    <div className="rounded-xl border border-emerald-200 bg-emerald-50/40 p-4 space-y-3">
      <div className="flex items-center space-x-2">
        <PackagePlus className="h-4 w-4 text-emerald-600" />
        <h4 className="text-xs font-bold text-slate-700">导入参考包（参考基因组 + 可选 GFF + 可选表达矩阵）</h4>
      </div>
      <p className="text-[11px] text-slate-500">
        两条路：① 把文件放到服务端 <code className="font-mono">cs_pipeline/data/reference_genomes/</code> 后直接填路径（大基因组推荐）；
        ② ≤50MB 小文件点「上传」直传后自动填路径。注册成功后即可在「回贴基因组」中选用，多组学按需计算。
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className="text-[11px] font-semibold text-slate-600">参考包 ID（小写/数字/下划线）</label>
          <input className={inputCls} value={bundleId} onChange={(e) => setBundleId(e.target.value)} placeholder="如 rubber_dandelion_v2" />
        </div>
        <div>
          <label className="text-[11px] font-semibold text-slate-600">展示名</label>
          <input className={inputCls} value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="如 橡胶草自定义参考 v2" />
        </div>
      </div>

      {(
        [
          ['fasta', '参考基因组 FASTA *', fastaPath, setFastaPath, '如 2-1_TKS.genome.fasta（.fai 缺失自动构建）'],
          ['gff', '基因注释 GFF3（可选）', gffPath, setGffPath, '提供后可做基因定位，缺省则基因不可定位（如实标注）'],
          ['expr', '表达矩阵 CSV/XLSX（可选）', exprPath, setExprPath, '首列为基因 ID，其余列为组织表达量'],
        ] as const
      ).map(([target, label, value, setter, ph]) => (
        <div key={target}>
          <div className="flex items-center justify-between mb-1">
            <label className="text-[11px] font-semibold text-slate-600">{label}</label>
            <label className="inline-flex cursor-pointer items-center rounded-lg border border-slate-200 bg-white px-2 py-0.5 text-[11px] text-slate-600 hover:bg-slate-50">
              <Upload className="mr-1 h-3 w-3" />
              {uploadMutation.isPending && uploadTarget === target ? '上传中…' : '上传 (≤50MB)'}
              <input type="file" className="hidden" onChange={handleUpload(target)} />
            </label>
          </div>
          <input className={inputCls} value={value} onChange={(e) => setter(e.target.value)} placeholder={ph} />
        </div>
      ))}

      {uploadMutation.isError && (
        <p className="text-[11px] text-rose-600">上传失败：{uploadMutation.error.message}</p>
      )}

      <div>
        <div className="flex items-center justify-between mb-1">
          <label className="text-[11px] font-semibold text-slate-600">
            组织列映射（表达矩阵列名 → 组织标签；影响优先指数表达项）
          </label>
          <button
            type="button"
            onClick={() => setTissueRows([...tissueRows, { label: '', column: '' }])}
            className="inline-flex items-center rounded-lg border border-slate-200 bg-white px-2 py-0.5 text-[11px] text-slate-600 hover:bg-slate-50"
          >
            <Plus className="mr-1 h-3 w-3" />
            加一行
          </button>
        </div>
        {tissueRows.length === 0 && <p className="text-[11px] text-slate-400">未映射任何组织：优先指数表达项将按 0 并如实标注。</p>}
        {tissueRows.map((row, i) => (
          <div key={i} className="flex items-center gap-2 mb-1.5">
            <input
              className={`${inputCls} max-w-[8rem]`}
              value={row.label}
              onChange={(e) => setTissueRows(tissueRows.map((r, j) => (j === i ? { ...r, label: e.target.value } : r)))}
              placeholder="组织名 如 叶"
            />
            <input
              className={inputCls}
              value={row.column}
              onChange={(e) => setTissueRows(tissueRows.map((r, j) => (j === i ? { ...r, column: e.target.value } : r)))}
              placeholder="表达矩阵列名 如 Leaf_tpm"
            />
            <button
              type="button"
              onClick={() => setTissueRows(tissueRows.filter((_, j) => j !== i))}
              className="rounded-lg border border-slate-200 bg-white p-1.5 text-slate-400 hover:text-rose-500"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className="text-[11px] font-semibold text-slate-600">基因 ID 匹配规则</label>
          <select className={inputCls} value={idRule} onChange={(e) => setIdRule(e.target.value as 'same' | 'evm_tu_to_model')}>
            <option value="same">same（GFF/矩阵基因 ID 直接一致）</option>
            <option value="evm_tu_to_model">evm_tu_to_model（evm.TU.X ↔ evm.model.X 规则映射）</option>
          </select>
        </div>
        <div>
          <label className="text-[11px] font-semibold text-slate-600">备注（口径/来源）</label>
          <input className={inputCls} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="如 表达量为 TPM，3 重复均值" />
        </div>
      </div>

      <div className="flex items-center justify-between pt-1">
        <label className="inline-flex items-center space-x-1.5 text-[11px] text-slate-600">
          <input type="checkbox" checked={allowOverwrite} onChange={(e) => setAllowOverwrite(e.target.checked)} />
          <span>同 ID 已存在时覆盖</span>
        </label>
        <button
          type="button"
          disabled={!canSubmit}
          onClick={() => registerMutation.mutate()}
          className="inline-flex items-center rounded-xl bg-emerald-600 px-4 py-2 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <FolderUp className="mr-1.5 h-3.5 w-3.5" />
          {registerMutation.isPending ? '校验并注册中…' : '注册参考包'}
        </button>
      </div>

      {registerMutation.isError && (
        <p className="text-[11px] text-rose-600">注册失败：{registerMutation.error.message}</p>
      )}
      {registerMutation.isSuccess && (
        <p className="text-[11px] text-emerald-700">
          已注册参考包 {registerMutation.data.id}（{registerMutation.data.display_name}），已自动切换选用。
        </p>
      )}
    </div>
  )
}
