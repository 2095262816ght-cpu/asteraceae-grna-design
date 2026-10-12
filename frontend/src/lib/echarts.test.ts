import { describe, expect, it, vi } from 'vitest'
import { echarts } from './echarts'
import { SVGRenderer } from 'echarts/renderers'

// 按需注册完整性回归：图例/组件缺注册时 echarts 在 setOption 报 "used but not imported"。
// 这里用 SVG 渲染器在 jsdom 中跑真实 option（与 GenomicTargetMap / BatchUploadCard 用到的
// 图表类型、组件一一对应），防止后续改动悄悄漏注册。

echarts.use([SVGRenderer])

function renderOption(name: string, option: Record<string, unknown>) {
  const errors: string[] = []
  const spy = vi.spyOn(console, 'error').mockImplementation((...args: unknown[]) => {
    errors.push(args.map(String).join(' '))
  })
  const el = document.createElement('div')
  el.style.width = '800px'
  el.style.height = '400px'
  document.body.appendChild(el)
  try {
    const chart = echarts.init(el, undefined, { renderer: 'svg' })
    chart.setOption(option)
    chart.dispose()
  } finally {
    spy.mockRestore()
    el.remove()
  }
  expect(errors.filter((e) => /not imported|is used but/i.test(e)), `${name} 存在未注册的 echarts 模块`).toEqual([])
}

describe('echarts 按需注册', () => {
  it('覆盖基因组图谱用到的 series/组件', () => {
    renderOption('GenomicTargetMap', {
      grid: { top: 40, bottom: 70, left: 90, right: 40 },
      tooltip: { trigger: 'item' },
      xAxis: { type: 'value', min: 0, max: 100 },
      yAxis: { type: 'value', min: -3, max: 2, interval: 1 },
      dataZoom: [{ type: 'slider' }, { type: 'inside' }],
      series: [
        {
          type: 'line',
          markLine: {
            silent: true,
            symbol: ['none', 'arrow'],
            data: [[{ coord: [10, 0] }, { coord: [90, 0] }]],
          },
          data: [],
        },
        { type: 'scatter', data: [[20, 1]] },
        {
          type: 'custom',
          coordinateSystem: 'cartesian2d',
          renderItem: (_params: unknown, api: { coord: (v: number[]) => number[] }) => ({
            type: 'rect',
            shape: { x: api.coord([10, 0])[0], y: 0, width: 20, height: 10 },
          }),
          data: [[10, 90, 0]],
        },
      ],
    })
  })

  it('覆盖批量打分看板用到的 series/组件', () => {
    renderOption('BatchUploadCard', {
      grid: { left: 40, right: 12, top: 20, bottom: 40 },
      xAxis: { type: 'category', data: ['0-10', '10-20'] },
      yAxis: { type: 'value', name: '条目数', minInterval: 1 },
      tooltip: { trigger: 'axis' },
      series: [{ type: 'bar', data: [2, 5] }],
    })
    renderOption('BatchUploadCard 散点', {
      grid: { left: 45, right: 12, top: 20, bottom: 35 },
      xAxis: { type: 'value' },
      yAxis: { type: 'value' },
      tooltip: { trigger: 'item' },
      series: [{ type: 'scatter', data: [[1, 2]] }],
    })
  })
})
