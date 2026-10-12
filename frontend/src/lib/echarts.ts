// 按需注册的 ECharts 实例：只装入实际用到的图表与组件，避免全量 echarts（约 1MB）进入主包
import * as echarts from 'echarts/core'
import { BarChart, CustomChart, LineChart, ScatterChart } from 'echarts/charts'
import {
  AxisPointerComponent,
  DataZoomComponent,
  GridComponent,
  MarkLineComponent,
  TooltipComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([
  BarChart,
  CustomChart,
  LineChart,
  ScatterChart,
  AxisPointerComponent,
  DataZoomComponent,
  GridComponent,
  MarkLineComponent,
  TooltipComponent,
  CanvasRenderer,
])

export { echarts }

// echarts-for-react 是 CJS（导出 { default: 组件 }）；Vite 依赖预打包/产物里
// 默认导入拿到的是模块对象本身而非 .default，直接当组件用触发 React #130 整树白屏。
// 统一在此做互操作兜底，调用方一律从本模块取组件。
import ReactEChartsCoreImport from 'echarts-for-react/lib/core'
const _interop = ReactEChartsCoreImport as unknown as { default?: typeof ReactEChartsCoreImport }
export const ReactEChartsCore = _interop.default ?? ReactEChartsCoreImport
