import '@testing-library/jest-dom/vitest'
import React from 'react'
import { vi } from 'vitest'

// 全局 Mock echarts-for-react 以支持 jsdom 测试环境
vi.mock('echarts-for-react', () => ({
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
