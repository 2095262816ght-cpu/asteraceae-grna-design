import React, { Suspense, lazy, useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { SystemHealthCard } from './components/SystemHealthCard'
import { CandidateSearchPanel } from './components/CandidateSearchPanel'
import { HistoryDrawer } from './components/HistoryDrawer'
import { Button, Spinner, TabPanel, Tabs } from './components/ui'
import { BackgroundMotion } from './components/BackgroundMotion'
import { DnaHelix } from './components/icons/DnaHelix'
import { GeneratedIcon } from './components/icons/GeneratedIcon'
import { useUrlSynced } from './lib/urlState'
import { Search, History, Sparkles, FileSpreadsheet } from 'lucide-react'

// 打分/历史面板按需加载：首屏只解析候选检索页所需代码（含 echarts 等大依赖随面板懒加载）
const SingleScoringCard = lazy(() =>
  import('./components/SingleScoringCard').then((m) => ({ default: m.SingleScoringCard }))
)
const BatchUploadCard = lazy(() =>
  import('./components/BatchUploadCard').then((m) => ({ default: m.BatchUploadCard }))
)
const ExportHistoryPanel = lazy(() =>
  import('./components/ExportHistoryPanel').then((m) => ({ default: m.ExportHistoryPanel }))
)

const PanelFallback: React.FC = () => (
  <div className="flex items-center justify-center py-16">
    <Spinner label="加载面板中…" />
  </div>
)

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 10,
      retry: 1,
    },
  },
})

export const App: React.FC = () => {
  // Tab 状态进 URL（F5/分享不丢）；面板首次访问后保持挂载，仅切可见性
  const [activeTab, setActiveTab] = useUrlSynced<'candidates' | 'scoring' | 'history'>({
    key: 'tab',
    defaultValue: 'candidates',
    parse: (raw) => (raw === 'candidates' || raw === 'scoring' || raw === 'history' ? raw : null),
    serialize: (v) => (v === 'candidates' ? null : v),
    mode: 'push',
  })
  const [scoringSubTab, setScoringSubTab] = useUrlSynced<'single' | 'batch'>({
    key: 'sub',
    defaultValue: 'single',
    parse: (raw) => (raw === 'single' || raw === 'batch' ? raw : null),
    serialize: (v) => (v === 'single' ? null : v),
  })
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false)

  return (
    <QueryClientProvider client={queryClient}>
      <div className="flex min-h-screen flex-col text-ink lg:flex-row">
        {/* 背景动效层：毛玻璃背后的运动内容（双螺旋/光晕/微粒） */}
        <BackgroundMotion />
        {/* 深松绿侧边栏：品牌 / 工作台导航（窄屏转为顶部栏） */}
        <aside className="glass-panel z-40 flex flex-col lg:fixed lg:inset-y-0 lg:left-0 lg:w-64">
          <div className="flex items-start gap-3 px-5 pb-4 pt-5 lg:block lg:pb-5 lg:pt-6">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-card bg-brand-300 text-pine-900 shadow-lg shadow-brand-500/20">
              <DnaHelix variant="brand" className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-[13px] font-bold leading-snug tracking-tight text-ink lg:mt-3">
                AI 驱动的 gRNA 编辑效率预测与脱靶评估平台——面向橡胶草与莴苣
              </h1>
              <p className="mt-1.5 text-[10px] leading-relaxed text-ink-muted lg:mt-3">
                莴苣 / 橡胶草 · 分层选择性 Beta-Binomial GLMM (v2.1 / noB879) · 生产级全栈工作台
              </p>
            </div>
          </div>

          <div className="mx-5 h-px bg-line" />

          {/* 功能导航 */}
          <nav className="flex-1 px-3 py-3 lg:overflow-y-auto lg:py-4">
            <Tabs
              variant="nav"
              orientation="vertical"
              className="flex-row flex-wrap gap-1 lg:flex-col lg:flex-nowrap"
              aria-label="功能导航"
              value={activeTab}
              onChange={(id) => setActiveTab(id as 'candidates' | 'scoring' | 'history')}
              items={[
                { id: 'candidates', icon: <Search className="h-4 w-4" />, label: '候选靶点检索' },
                {
                  id: 'scoring',
                  icon: <GeneratedIcon name="calculator" className="h-4 w-4" />,
                  label: '实时与批量打分',
                },
                { id: 'history', icon: <History className="h-4 w-4" />, label: '历史与导出批次' },
              ]}
            />
          </nav>
        </aside>

        {/* 工作区 */}
        <main className="flex-1 lg:ml-64">
          <div className="mx-auto max-w-[1560px] px-4 py-6 sm:px-8">
            {/* 服务状态条 */}
            <SystemHealthCard />

            {/* 选项卡内容区：保持挂载、仅切换可见性，避免切页丢失已打分结果等本地状态 */}
            <div className="rise mt-6">
              <TabPanel tabId="candidates" activeTabId={activeTab}>
                <CandidateSearchPanel />
              </TabPanel>

              <TabPanel tabId="scoring" activeTabId={activeTab} className="space-y-6">
                {/* 打分模式二级切换器 */}
                <div className="flex items-center gap-4 border-b border-line">
                  <Tabs
                    variant="underline"
                    className="flex-1 border-b-0"
                    aria-label="打分模式"
                    value={scoringSubTab}
                    onChange={(id) => setScoringSubTab(id as 'single' | 'batch')}
                    items={[
                      {
                        id: 'single',
                        icon: <Sparkles className="h-4 w-4" />,
                        label: '单序列实时打分与结构解构',
                      },
                      {
                        id: 'batch',
                        icon: <FileSpreadsheet className="h-4 w-4" />,
                        label: '批量文件上传分析 (CSV / Excel)',
                      },
                    ]}
                  />

                  <Button onClick={() => setIsDrawerOpen(true)} className="ml-auto">
                    <History className="h-3.5 w-3.5 text-brand-600" />
                    <span>历史打分抽屉</span>
                  </Button>
                </div>

                <TabPanel tabId="single" activeTabId={scoringSubTab}>
                  <Suspense fallback={<PanelFallback />}>
                    <SingleScoringCard />
                  </Suspense>
                </TabPanel>
                <TabPanel tabId="batch" activeTabId={scoringSubTab}>
                  <Suspense fallback={<PanelFallback />}>
                    <BatchUploadCard />
                  </Suspense>
                </TabPanel>
              </TabPanel>

              <TabPanel tabId="history" activeTabId={activeTab}>
                <Suspense fallback={<PanelFallback />}>
                  <ExportHistoryPanel />
                </Suspense>
              </TabPanel>
            </div>
          </div>
        </main>

        {/* 历史任务滑出式抽屉 */}
        <HistoryDrawer isOpen={isDrawerOpen} onClose={() => setIsDrawerOpen(false)} />
      </div>
    </QueryClientProvider>
  )
}

export default App
