import React from 'react'
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { Badge } from './Badge'
import { Button } from './Button'
import { Dialog } from './Dialog'
import { Drawer } from './Drawer'
import { InfoHint } from './InfoHint'
import { Pagination } from './Pagination'
import { Tabs, TabPanel } from './Tabs'

describe('ui primitives', () => {
  it('Badge keeps native title attribute for honest annotations', () => {
    render(<Badge tone="warning" title="点击查看脱靶位点明细（坐标/错配位置/CFD/MIT 评分/区域）">未计算</Badge>)
    expect(
      screen.getByTitle('点击查看脱靶位点明细（坐标/错配位置/CFD/MIT 评分/区域）')
    ).toBeInTheDocument()
    expect(screen.getByText('未计算')).toBeInTheDocument()
  })

  it('InfoHint renders native title attribute', () => {
    render(<InfoHint title="表达适配测试说明" />)
    expect(screen.getByTitle('表达适配测试说明')).toBeInTheDocument()
  })

  it('Button exposes loading and disabled states', () => {
    const onClick = vi.fn()
    render(
      <Button loading onClick={onClick}>
        生成中
      </Button>
    )
    const btn = screen.getByRole('button', { name: /生成中/ })
    expect(btn).toBeDisabled()
    fireEvent.click(btn)
    expect(onClick).not.toHaveBeenCalled()
  })

  it('Dialog renders title with close button titled 关闭 and traps Escape', () => {
    const onClose = vi.fn()
    render(
      <Dialog open onClose={onClose} title="排序方式说明 · 各指标详细排名方法">
        <p>正文</p>
      </Dialog>
    )
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByText('排序方式说明 · 各指标详细排名方法')).toBeInTheDocument()
    expect(screen.getByTitle('关闭')).toBeInTheDocument()
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('Esc closes the highest-priority overlay first (confirm > drawer > dialog)', () => {
    const onConfirm = vi.fn()
    const onDrawer = vi.fn()
    const onDialog = vi.fn()
    const Harness: React.FC = () => {
      const [open, setOpen] = React.useState({ confirm: true, drawer: true, dialog: true })
      return (
        <>
          <Dialog
            open={open.dialog}
            onClose={() => {
              onDialog()
              setOpen((s) => ({ ...s, dialog: false }))
            }}
            title="排序方式说明"
          >
            <p>弹窗</p>
          </Dialog>
          <Drawer
            open={open.drawer}
            onClose={() => {
              onDrawer()
              setOpen((s) => ({ ...s, drawer: false }))
            }}
            title="脱靶位点明细（全基因组 ≤3 错配扫描）"
          >
            <p>抽屉</p>
          </Drawer>
          <Dialog
            open={open.confirm}
            onClose={() => {
              onConfirm()
              setOpen((s) => ({ ...s, confirm: false }))
            }}
            title="要计算脱靶吗？"
            closePriority={3}
            align="center"
          >
            <p>确认</p>
          </Dialog>
        </>
      )
    }
    render(<Harness />)
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onConfirm).toHaveBeenCalledTimes(1)
    expect(onDrawer).not.toHaveBeenCalled()
    expect(onDialog).not.toHaveBeenCalled()
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onDrawer).toHaveBeenCalledTimes(1)
    expect(onDialog).not.toHaveBeenCalled()
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onDialog).toHaveBeenCalledTimes(1)
  })

  it('Tabs support keyboard navigation and panels mount on first activation then stay mounted', () => {
    const onChange = vi.fn()
    const view = (
      <Tabs
        items={[
          { id: 'candidates', label: '候选靶点检索' },
          { id: 'scoring', label: '实时与批量打分' },
        ]}
        value="candidates"
        onChange={onChange}
        aria-label="功能导航"
      />
    )
    const panels = (activeTabId: string) => (
      <>
        <TabPanel tabId="candidates" activeTabId={activeTabId}>
          <p>候选面板</p>
        </TabPanel>
        <TabPanel tabId="scoring" activeTabId={activeTabId}>
          <p>打分面板</p>
        </TabPanel>
      </>
    )
    const { rerender } = render(
      <>
        {view}
        {panels('candidates')}
      </>
    )
    const tab = screen.getByRole('tab', { name: /候选靶点检索/ })
    expect(tab).toHaveAttribute('aria-selected', 'true')
    fireEvent.keyDown(screen.getByRole('tablist'), { key: 'ArrowRight' })
    expect(onChange).toHaveBeenCalledWith('scoring')
    // 未访问面板不挂载（不为未访问页签付出首屏渲染成本）
    expect(screen.queryByText('打分面板')).not.toBeInTheDocument()
    // 首次激活后挂载
    rerender(
      <>
        {view}
        {panels('scoring')}
      </>
    )
    expect(screen.getByText('打分面板')).toBeInTheDocument()
    // 切走后仅 hidden、保持挂载（hidden 语义），切页不丢本地状态
    rerender(
      <>
        {view}
        {panels('candidates')}
      </>
    )
    expect(screen.getByText('打分面板')).toBeInTheDocument()
    expect(screen.getByText('打分面板').closest('.hidden')).not.toBeNull()
  })

  it('Pagination renders frozen copy and boundary-disabled buttons', () => {
    render(<Pagination page={1} pageSize={100} total={82} onPrev={() => {}} onNext={() => {}} />)
    expect(screen.getByText('显示第 1 - 82 条，共 82 条')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /上一页/ })).toBeDisabled()
    expect(screen.getByRole('button', { name: /下一页/ })).toBeDisabled()
  })
})
