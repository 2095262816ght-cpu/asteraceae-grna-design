import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import '@testing-library/jest-dom/vitest'
import { App } from './App'

describe('App 页面切换状态保持', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(typeof input === 'string' ? input : (input as Request).url)
      const json = (body: unknown) => ({ ok: true, json: async () => body }) as Response
      if (url.includes('/api/v1/health'))
        return json({
          status: 'ok',
          version: '2.1.0',
          database: 'connected',
          timestamp: '2026-10-01T12:00:00Z',
        })
      if (url.includes('/api/v1/exports')) return json([])
      if (url.includes('/api/v1/scoring/jobs')) return json([])
      if (url.includes('/api/v1/sequence/bundles')) return json([])
      if (url.includes('/api/v1/sequence/annotate'))
        return json({
          state: 'custom',
          seq30: 'TTTGTGGATTCCGGTAGAATCTGATGGAAT',
          species: 'lettuce',
          bundle_id: 'lettuce',
          bundle_name: '莴苣 (LsT2T)',
          annotation_note: '该序列未精确匹配测试基因组：多组学指标不适用，不硬算。',
        })
      if (url.includes('/api/v1/scoring/single'))
        return json({
          job_id: 'job-keep-123456',
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
          created_at: '2026-10-01T12:00:00Z',
        })
      return json([])
    })
  })

  it('切到其他页面再回来，单序列打分结果仍在', async () => {
    render(<App />)

    await userEvent.click(screen.getByText('实时与批量打分'))
    await userEvent.click(screen.getByText(/填入示例 1/i))
    await userEvent.click(screen.getByRole('button', { name: /开始实时打分/i }))

    await waitFor(() => {
      expect(screen.getByText('76.6')).toBeInTheDocument()
    })

    // 切到顶层其他页面再回来（切走时仅 CSS 隐藏，不销毁组件）
    await userEvent.click(screen.getByText('候选靶点检索'))
    expect(screen.getByText('76.6').closest('.hidden')).not.toBeNull()
    await userEvent.click(screen.getByText('实时与批量打分'))

    expect(screen.getByText('76.6')).toBeInTheDocument()
    expect(screen.getByText('76.6').closest('.hidden')).toBeNull()
    expect(screen.getByDisplayValue('TTTGTGGATTCCGGTAGAATCTGATGGAAT')).toBeInTheDocument()

    // 切到批量上传二级页再回来
    await userEvent.click(screen.getByText(/批量文件上传分析/i))
    await userEvent.click(screen.getByText(/单序列实时打分与结构解构/i))

    expect(screen.getByText('76.6')).toBeInTheDocument()
  })
})
