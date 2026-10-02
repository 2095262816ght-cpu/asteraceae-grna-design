import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, RefreshCw, Database, Server } from 'lucide-react'
import { Badge, Button, Card, Spinner } from './ui'
import { GeneratedIcon } from './icons/GeneratedIcon'

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
      <Card padding="sm">
        <Spinner label="正在检测系统服务..." />
      </Card>
    )
  }

  if (error || !data || data.status !== 'ok') {
    return (
      <Card padding="sm" className="border-rose-200 bg-rose-50/50">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-control bg-rose-100 text-rose-600">
              <AlertTriangle className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-rose-900">服务连接异常</h3>
              <p className="text-xs text-rose-700">
                {error instanceof Error ? error.message : '无法连通后端 API 或数据库服务'}
              </p>
            </div>
          </div>
          <Button onClick={() => refetch()} disabled={isFetching}>
            <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? 'animate-spin' : ''}`} />
            重试
          </Button>
        </div>
      </Card>
    )
  }

  return (
    <Card padding="sm">
      <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-control bg-brand-50 text-brand-600">
            <GeneratedIcon name="checkCircle" className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-ink">服务运行正常</h3>
              <Badge tone="brand">v{data.version}</Badge>
            </div>
            <p className="mt-0.5 text-[11px] text-ink-muted">
              全栈服务就绪 · 检查时间: {new Date(data.timestamp).toLocaleTimeString()}
            </p>
          </div>
        </div>

        <div className="hidden h-8 w-px bg-line sm:block" />

        <div className="flex items-center gap-2.5">
          <Server className="h-5 w-5 text-ink-faint" />
          <div>
            <div className="text-[11px] text-ink-muted">FastAPI 后端引擎</div>
            <div className="text-xs font-semibold text-ink">在线活跃 (Active)</div>
          </div>
        </div>

        <div className="hidden h-8 w-px bg-line sm:block" />

        <div className="flex items-center gap-2.5">
          <Database className="h-5 w-5 text-ink-faint" />
          <div>
            <div className="text-[11px] text-ink-muted">数据库持久层</div>
            <div className="flex items-center space-x-1.5 text-xs font-semibold text-brand-600">
              <span className="h-1.5 w-1.5 rounded-full bg-brand-500"></span>
              <span>数据库连接正常</span>
            </div>
          </div>
        </div>

        <Button onClick={() => refetch()} disabled={isFetching} className="ml-auto">
          <RefreshCw
            className={`h-3.5 w-3.5 text-ink-muted transition-transform ${isFetching ? 'animate-spin' : ''}`}
          />
          刷新
        </Button>
      </div>
    </Card>
  )
}
