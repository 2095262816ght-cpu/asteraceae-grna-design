import React from 'react'
import { Button, Dialog } from '../ui'
import { DnaHelix } from '../icons/DnaHelix'
import type { CandidateItem } from '../../lib/candidateQuery'

interface ComputeConfirmDialogProps {
  cand: CandidateItem
  onCancel: () => void
  onConfirm: () => void
}

// 计算脱靶确认框：点击"未计算"格弹出，确认后按需全基因组扫描并回填
export const ComputeConfirmDialog: React.FC<ComputeConfirmDialogProps> = ({ cand, onCancel, onConfirm }) => (
  <Dialog
    open
    onClose={onCancel}
    size="sm"
    align="center"
    closePriority={3}
    title="要计算脱靶吗？"
  >
    <div>
      <p className="px-5 pb-1 pt-4 text-2xs leading-relaxed text-ink-muted">
        将对 <span className="font-mono font-semibold text-ink">{cand.guide_id}</span> （
        <span className="font-mono text-ink-muted">{cand.seq20}</span>）做 Cas-OFFinder
        口径全基因组脱靶扫描（≤3 错配、PAM=NGG、正负链分行计数），单条约 1 分钟。完成后本行显示脱靶数，并自动打开脱靶位点明细抽屉。
      </p>
      <div className="flex justify-end gap-2 px-5 py-4">
        <Button onClick={onCancel}>取消</Button>
        <Button variant="primary" onClick={onConfirm}>
          <DnaHelix className="h-3.5 w-3.5" />
          计算脱靶
        </Button>
      </div>
    </div>
  </Dialog>
)
