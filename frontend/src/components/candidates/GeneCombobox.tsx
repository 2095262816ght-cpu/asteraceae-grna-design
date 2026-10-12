import React, { useEffect, useRef, useState } from 'react'
import { Check, ChevronDown, Search, X } from 'lucide-react'
import { DnaHelix } from '../icons/DnaHelix'
import type { GeneInfo } from '../../lib/types'

interface GeneComboboxProps {
  genes: GeneInfo[] | undefined
  genesLoading: boolean
  activeGeneId: string
  onSelectGene: (geneId: string) => void
}

// 基因即输即搜 Combobox（点击外部收起；Enter 选首项；Esc 收起）
export const GeneCombobox: React.FC<GeneComboboxProps> = ({
  genes,
  genesLoading,
  activeGeneId,
  onSelectGene,
}) => {
  const [isGeneDropdownOpen, setIsGeneDropdownOpen] = useState<boolean>(false)
  const [geneSearchInput, setGeneSearchInput] = useState<string>('')
  const geneComboboxRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (geneComboboxRef.current && !geneComboboxRef.current.contains(event.target as Node)) {
        setIsGeneDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const filteredGenes = (() => {
    if (!genes) return []
    if (!geneSearchInput.trim()) return genes
    const q = geneSearchInput.toLowerCase().trim()
    return genes.filter(
      (g) =>
        g.gene_id.toLowerCase().includes(q) ||
        g.chrom.toLowerCase().includes(q) ||
        (g.nlr_type && g.nlr_type.toLowerCase().includes(q))
    )
  })()

  const handleSelectGene = (geneId: string) => {
    onSelectGene(geneId)
    setGeneSearchInput('')
    setIsGeneDropdownOpen(false)
  }

  return (
    <div className="relative flex flex-1 items-start space-x-3.5 sm:items-center" ref={geneComboboxRef}>
      <div className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-card border border-brand-100/60 bg-brand-50 text-brand-700 shadow-sm sm:mt-0">
        <DnaHelix className="h-5 w-5" />
      </div>
      <div className="relative max-w-lg flex-1">
        <div className="mb-1 flex items-center justify-between gap-2">
          <label className="block text-2xs font-semibold tracking-wide text-ink-muted">
            选择靶基因 (即输即搜 · 莴苣全基因组 + 49 NLR)
          </label>
          {activeGeneId && (
            <span className="shrink-0 rounded bg-brand-50 px-1.5 py-0.5 font-mono text-2xs font-semibold text-brand-600">
              当前: {activeGeneId}
            </span>
          )}
        </div>

        {genesLoading ? (
          <div className="h-10 w-full animate-pulse rounded-card bg-slate-100"></div>
        ) : (
          <div className="relative">
            {/* 输入搜索框 */}
            <div className="relative flex items-center">
              <Search className="pointer-events-none absolute left-3 h-4 w-4 text-ink-faint" />
              <input
                type="text"
                role="combobox"
                aria-expanded={isGeneDropdownOpen}
                aria-controls="gene-options-list"
                aria-label="选择靶基因"
                value={isGeneDropdownOpen ? geneSearchInput : geneSearchInput || activeGeneId}
                placeholder="输入基因号或关键字 (如 019420, Chr06, CC)..."
                onFocus={() => {
                  setIsGeneDropdownOpen(true)
                }}
                onChange={(e) => {
                  setGeneSearchInput(e.target.value)
                  setIsGeneDropdownOpen(true)
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    if (filteredGenes.length > 0) {
                      handleSelectGene(filteredGenes[0].gene_id)
                    }
                  } else if (e.key === 'Escape') {
                    setIsGeneDropdownOpen(false)
                  }
                }}
                className="block w-full rounded-card border border-line bg-surface py-2 pl-9 pr-16 text-sm font-medium text-ink shadow-sm transition-all focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
              />
              <div className="absolute right-2 flex items-center space-x-1">
                {geneSearchInput && (
                  <button
                    type="button"
                    onClick={() => setGeneSearchInput('')}
                    className="rounded p-1 text-ink-faint hover:bg-slate-100 hover:text-ink-muted"
                    title="清空输入"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => setIsGeneDropdownOpen((prev) => !prev)}
                  className="rounded p-1 text-ink-faint hover:bg-slate-100 hover:text-ink-muted"
                  title={isGeneDropdownOpen ? '收起下拉' : '展开下拉'}
                >
                  <ChevronDown
                    className={`h-4 w-4 transition-transform duration-200 ${isGeneDropdownOpen ? 'rotate-180' : ''}`}
                  />
                </button>
              </div>
            </div>

            {/* 悬浮下拉选项列表 */}
            {isGeneDropdownOpen && (
              <div
                id="gene-options-list"
                className="glass-pop absolute left-0 right-0 top-full z-40 mt-1.5 max-h-72 overflow-y-auto rounded-card p-1.5"
              >
                <div className="flex items-center justify-between border-b border-line px-2.5 py-1.5 text-2xs font-medium text-ink-faint">
                  <span>
                    {geneSearchInput ? `匹配结果 (${filteredGenes.length})` : `莴苣全基因组 + 49 NLR`}
                  </span>
                  <span className="text-[10px] text-ink-faint">按回车快速选中首项</span>
                </div>

                {filteredGenes.length === 0 ? (
                  <div className="py-6 text-center text-xs text-ink-faint">
                    未找到匹配的基因 (关键字: "{geneSearchInput}")
                  </div>
                ) : (
                  <div className="divide-y divide-slate-50">
                    {filteredGenes.slice(0, 200).map((g) => {
                      const isSelected = g.gene_id === activeGeneId
                      return (
                        <button
                          key={g.gene_id}
                          type="button"
                          onClick={() => handleSelectGene(g.gene_id)}
                          className={`flex w-full items-center justify-between rounded-control px-3 py-2 text-left text-xs transition-colors ${
                            isSelected
                              ? 'bg-brand-50 font-semibold text-brand-900'
                              : 'text-ink-muted hover:bg-surface-sunken'
                          }`}
                        >
                          <div className="flex flex-col">
                            <span className="flex items-center gap-1.5 font-mono text-sm tracking-tight">
                              {g.gene_id}
                              {isSelected && <span className="h-1.5 w-1.5 rounded-full bg-brand-500"></span>}
                            </span>
                            <span className="text-2xs font-normal text-ink-faint">
                              {g.chrom} · {g.gene_id.startsWith('Lsa') ? 'NLR 专项注释' : '全基因组注释'}
                              {g.nlr_type ? ` · ${g.nlr_type}` : ''} · {g.candidate_count} 候选位点
                            </span>
                          </div>
                          {isSelected && <Check className="ml-2 h-4 w-4 shrink-0 text-brand-600" />}
                        </button>
                      )
                    })}
                    {filteredGenes.length > 200 && (
                      <div className="px-3 py-2 text-center text-2xs text-ink-faint">
                        仅显示前 200 条（共 {filteredGenes.length} 条），请输入关键字缩小范围
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
