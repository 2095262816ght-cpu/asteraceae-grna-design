import '@testing-library/jest-dom/vitest'
import React from 'react'
import { beforeEach, vi } from 'vitest'

// URL 状态持久化：每个用例恢复干净 URL，避免用例间参数泄漏
beforeEach(() => {
  window.history.replaceState(null, '', window.location.pathname)
})

// 全局 Mock echarts-for-react 核心绑定以支持 jsdom 测试环境
vi.mock('echarts-for-react/lib/core', () => ({
  default: ({ onEvents }: { onEvents?: Record<string, (e: unknown) => void> }) =>
    React.createElement(
      'div',
      { 'data-testid': 'echarts-container' },
      React.createElement(
        'button',
        {
          'data-testid': 'mock-chart-click',
          onClick: () =>
            onEvents?.click?.({
              data: {
                guide_id: 'Lsat_675191',
              },
            }),
        },
        'Mock Click Target'
      )
    ),
}))
