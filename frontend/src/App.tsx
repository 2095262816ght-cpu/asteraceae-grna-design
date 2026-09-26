import React, { useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { SystemHealthCard } from './components/SystemHealthCard'
import { Dna, Search, Calculator, History, Sparkles, ShieldCheck } from 'lucide-react'

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

          {/* 选项卡内容区 */}
          {activeTab === 'candidates' && (
            <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600 mb-4">
                <Search className="h-7 w-7" />
              </div>
              <h2 className="text-xl font-bold text-slate-900">49 个 NLR 代表基因候选靶点多维检索</h2>
              <p className="mx-auto mt-2 max-w-xl text-sm text-slate-500">
                Ticket 01 全栈脚手架已打通连通性。将在 Ticket 02 接入 49 基因候选数据自动灌库，提供外显子区域、着丝粒回避、组织表达量动态赋权及虚拟滚动大表。
              </p>
              <div className="mt-6 flex justify-center space-x-4">
                <div className="inline-flex items-center space-x-1.5 text-xs text-slate-500 bg-slate-50 px-3 py-1.5 rounded-full border border-slate-200">
                  <ShieldCheck className="h-4 w-4 text-emerald-600" />
                  <span>noB879 纯A级金标准已对齐</span>
                </div>
                <div className="inline-flex items-center space-x-1.5 text-xs text-slate-500 bg-slate-50 px-3 py-1.5 rounded-full border border-slate-200">
                  <Sparkles className="h-4 w-4 text-amber-500" />
                  <span>支持橡胶草产胶时相 (S1-S9) 决策</span>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'scoring' && (
            <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600 mb-4">
                <Calculator className="h-7 w-7" />
              </div>
              <h2 className="text-xl font-bold text-slate-900">单序列实时打分与高通量批量作业流水线</h2>
              <p className="mx-auto mt-2 max-w-xl text-sm text-slate-500">
                即将于 Ticket 04 & 05 交付：集成 DeepSpCas9 + CRISPRon 双模型推理桥接、异步非阻塞任务状态机与平滑进度条轮询。
              </p>
            </div>
          )}

          {activeTab === 'history' && (
            <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600 mb-4">
                <History className="h-7 w-7" />
              </div>
              <h2 className="text-xl font-bold text-slate-900">实验设计导出批次与历史任务追踪</h2>
              <p className="mx-auto mt-2 max-w-xl text-sm text-slate-500">
                将在 Ticket 06 交付：持久化存储每次筛选出的靶位点组合，支持符合实验下单标准的 CSV/Excel 一键导出与历史任务回放。
              </p>
            </div>
          )}
        </main>
      </div>
    </QueryClientProvider>
  )
}

export default App
