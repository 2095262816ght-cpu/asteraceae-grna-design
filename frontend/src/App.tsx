import React, { useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { SystemHealthCard } from './components/SystemHealthCard'
import { CandidateSearchPanel } from './components/CandidateSearchPanel'
import { SingleScoringCard } from './components/SingleScoringCard'
import { BatchUploadCard } from './components/BatchUploadCard'
import { ExportHistoryPanel } from './components/ExportHistoryPanel'
import { HistoryDrawer } from './components/HistoryDrawer'
import { Dna, Search, Calculator, History, Sparkles, FileSpreadsheet } from 'lucide-react'




const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 10,
      retry: 1,
    },
  },
})

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'candidates' | 'scoring' | 'history'>('candidates')
  const [scoringSubTab, setScoringSubTab] = useState<'single' | 'batch'>('single')
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false)

  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen bg-slate-50 text-slate-900">
        {/* 顶部专业生信导航栏 */}
        <header className="sticky top-0 z-50 border-b border-slate-200 bg-white/80 backdrop-blur-md">
          <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3.5 sm:px-6 lg:px-8">
            <div className="flex items-center space-x-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-600 text-white shadow-sm shadow-emerald-500/20">
                <Dna className="h-6 w-6" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-slate-900 tracking-tight">
                  菊科 CRISPR/Cas9 基因编辑与多组学决策系统
                </h1>
                <p className="text-xs text-slate-500">
                  莴苣 / 橡胶草 · 分层选择性 Beta-Binomial GLMM (v2.1 / noB879) · 生产级全栈工作台
                </p>
              </div>
            </div>

            {/* 功能导航选项卡 */}
            <nav className="flex space-x-1 rounded-xl bg-slate-100 p-1">
              <button
                onClick={() => setActiveTab('candidates')}
                className={`flex items-center space-x-2 rounded-lg px-3 py-1.5 text-xs font-medium transition-all ${
                  activeTab === 'candidates'
                    ? 'bg-white text-emerald-700 shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Search className="h-4 w-4" />
                <span>候选靶点检索</span>
              </button>

              <button
                onClick={() => setActiveTab('scoring')}
                className={`flex items-center space-x-2 rounded-lg px-3 py-1.5 text-xs font-medium transition-all ${
                  activeTab === 'scoring'
                    ? 'bg-white text-emerald-700 shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Calculator className="h-4 w-4" />
                <span>实时与批量打分</span>
              </button>

              <button
                onClick={() => setActiveTab('history')}
                className={`flex items-center space-x-2 rounded-lg px-3 py-1.5 text-xs font-medium transition-all ${
                  activeTab === 'history'
                    ? 'bg-white text-emerald-700 shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <History className="h-4 w-4" />
                <span>历史与导出批次</span>
              </button>
            </nav>
          </div>
        </header>

        {/* 主体工作区 */}
        <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          {/* 系统健康状况与服务连通卡片 (Ticket 01 交付) */}
          <div className="mb-8">
            <SystemHealthCard />
          </div>

          {/* 选项卡内容区：保持挂载、仅切换可见性，避免切页丢失已打分结果等本地状态 */}
          <div className={activeTab === 'candidates' ? '' : 'hidden'}>
            <CandidateSearchPanel />
          </div>


          <div className={`space-y-6 ${activeTab === 'scoring' ? '' : 'hidden'}`}>
              {/* 打分模式二级切换器 */}
              <div className="flex border-b border-slate-200">
                <button
                  onClick={() => setScoringSubTab('single')}
                  className={`inline-flex items-center gap-2 border-b-2 px-4 py-2.5 text-xs font-semibold transition-all ${
                    scoringSubTab === 'single'
                      ? 'border-emerald-600 text-emerald-700'
                      : 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-800'
                  }`}
                >
                  <Sparkles className="h-4 w-4" />
                  <span>单序列实时打分与结构解构</span>
                </button>

                <button
                  onClick={() => setScoringSubTab('batch')}
                  className={`inline-flex items-center gap-2 border-b-2 px-4 py-2.5 text-xs font-semibold transition-all ${
                    scoringSubTab === 'batch'
                      ? 'border-emerald-600 text-emerald-700'
                      : 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-800'
                  }`}
                >
                  <FileSpreadsheet className="h-4 w-4" />
                  <span>批量文件上传分析 (CSV / Excel)</span>
                </button>

                <button
                  onClick={() => setIsDrawerOpen(true)}
                  className="ml-auto inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 shadow-sm transition-colors"
                >
                  <History className="h-3.5 w-3.5 text-emerald-600" />
                  <span>历史打分抽屉</span>
                </button>
              </div>

              <div className={scoringSubTab === 'single' ? '' : 'hidden'}>
                <SingleScoringCard />
              </div>
              <div className={scoringSubTab === 'batch' ? '' : 'hidden'}>
                <BatchUploadCard />
              </div>
          </div>


          <div className={activeTab === 'history' ? '' : 'hidden'}>
            <ExportHistoryPanel />
          </div>
        </main>

        {/* 历史任务滑出式抽屉 */}
        <HistoryDrawer isOpen={isDrawerOpen} onClose={() => setIsDrawerOpen(false)} />
      </div>
    </QueryClientProvider>
  )
}

export default App
