import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { CheckCircle2, AlertTriangle, RefreshCw, Database, Server } from 'lucide-react'

interface HealthData {
  status: string
  version: string
  database: string
  timestamp: string
}

async function fetchHealth(): Promise<HealthData> {
  const res = await fetch('/api/v1/health')
  if (!res.ok) {
    throw new Error(`HTTP error! status: ${res.status}`)
  }
  return res.json()
}

export const SystemHealthCard: React.FC = () => {
  const { data, error, isLoading, refetch, isFetching } = useQuery<HealthData>({
    queryKey: ['system-health'],
    queryFn: fetchHealth,
    refetchInterval: 30000,
  })

  if (isLoading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center space-x-3 text-slate-500">
          <RefreshCw className="h-5 w-5 animate-spin text-emerald-600" />
          <span className="text-sm font-medium">正在检测系统服务...</span>
        </div>
      </div>
    )
  }

  if (error || !data || data.status !== 'ok') {
    return (
      <div className="rounded-xl border border-rose-200 bg-rose-50/50 p-6 shadow-sm">
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-rose-100 text-rose-600">
              <AlertTriangle className="h-6 w-6" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-rose-900">服务连接异常</h3>
              <p className="text-sm text-rose-700">
                {error instanceof Error ? error.message : '无法连通后端 API 或数据库服务'}
              </p>
            </div>
          </div>
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="inline-flex items-center rounded-lg bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-sm ring-1 ring-slate-200 hover:bg-slate-50"
          >
            <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${isFetching ? 'animate-spin' : ''}`} />
            重试
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-100 pb-4">
        <div className="flex items-center space-x-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-50 text-emerald-600">
            <CheckCircle2 className="h-6 w-6" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-base font-semibold text-slate-900">服务运行正常</h3>
              <span className="inline-flex items-center rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700 ring-1 ring-inset ring-emerald-600/20">
                v{data.version}
              </span>
            </div>
            <p className="text-xs text-slate-500">
              全栈服务就绪 · 检查时间: {new Date(data.timestamp).toLocaleTimeString()}
            </p>
          </div>
        </div>

        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="inline-flex items-center rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-sm hover:bg-slate-50"
        >
          <RefreshCw className={`mr-1.5 h-3.5 w-3.5 text-slate-500 ${isFetching ? 'animate-spin' : ''}`} />
          刷新
        </button>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-4">
        <div className="flex items-center space-x-3 rounded-lg bg-slate-50 p-3">
          <Server className="h-5 w-5 text-slate-600" />
          <div>
            <div className="text-xs text-slate-500">FastAPI 后端引擎</div>
            <div className="text-sm font-semibold text-slate-800">在线活跃 (Active)</div>
          </div>
        </div>

        <div className="flex items-center space-x-3 rounded-lg bg-slate-50 p-3">
          <Database className="h-5 w-5 text-slate-600" />
          <div>
            <div className="text-xs text-slate-500">数据库持久层</div>
            <div className="flex items-center space-x-1.5 text-sm font-semibold text-emerald-600">
              <span className="h-2 w-2 rounded-full bg-emerald-500"></span>
              <span>数据库连接正常</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
