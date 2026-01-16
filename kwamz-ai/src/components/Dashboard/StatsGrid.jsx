import { Users, DollarSign, TrendingUp, ArrowUpDown } from 'lucide-react'
import React from 'react'
import StatsCard from './StatsCard'

const formatCurrency = (value) => {
  if (value >= 1000000) {
    return `KES ${(value / 1000000).toFixed(2)}M`
  } else if (value >= 1000) {
    return `KES ${(value / 1000).toFixed(1)}K`
  }
  return `KES ${value.toFixed(2)}`
}

const formatNumber = (value) => {
  if (value >= 1000000) {
    return `${(value / 1000000).toFixed(2)}M`
  } else if (value >= 1000) {
    return `${(value / 1000).toFixed(1)}K`
  }
  return value.toLocaleString()
}

function StatsGrid({ kpis, isLoading }) {
  // Build stats data from KPIs
  const statsData = kpis ? [
    {
      title: 'Total Volume',
      value: formatCurrency(kpis.total_volume?.value || 0),
      change: `${kpis.total_volume?.change >= 0 ? '+' : ''}${kpis.total_volume?.change || 0}%`,
      trend: kpis.total_volume?.trend || 'up',
      icon: DollarSign,
      color: 'emerald',
      bgGradient: 'from-emerald-500/20 to-green-500/20'
    },
    {
      title: 'Transactions',
      value: formatNumber(kpis.total_transactions?.value || 0),
      change: `${kpis.total_transactions?.change >= 0 ? '+' : ''}${kpis.total_transactions?.change || 0}%`,
      trend: kpis.total_transactions?.trend || 'up',
      icon: ArrowUpDown,
      color: 'blue',
      bgGradient: 'from-blue-500/20 to-cyan-500/20'
    },
    {
      title: 'Commissions',
      value: formatCurrency(kpis.total_commissions?.value || 0),
      change: `${kpis.total_commissions?.change >= 0 ? '+' : ''}${kpis.total_commissions?.change || 0}%`,
      trend: kpis.total_commissions?.trend || 'up',
      icon: TrendingUp,
      color: 'purple',
      bgGradient: 'from-purple-500/20 to-pink-500/20'
    },
    {
      title: 'Active Agents',
      value: formatNumber(kpis.active_agents?.value || 0),
      change: `${kpis.active_agents?.change >= 0 ? '+' : ''}${kpis.active_agents?.change || 0}%`,
      trend: kpis.active_agents?.trend || 'up',
      icon: Users,
      color: 'orange',
      bgGradient: 'from-orange-500/20 to-red-500/20'
    }
  ] : []

  if (isLoading || !kpis) {
    return (
      <div className='grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 relative overflow-visible'>
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="bg-white/90 dark:bg-slate-800/90 backdrop-blur-xl rounded-2xl p-6 border border-slate-200/50 dark:border-slate-700/50 animate-pulse">
            <div className="flex items-center justify-between">
              <div className="space-y-3 flex-1">
                <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-24"></div>
                <div className="h-8 bg-slate-200 dark:bg-slate-700 rounded w-32"></div>
                <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded w-16"></div>
              </div>
              <div className="w-12 h-12 bg-slate-200 dark:bg-slate-700 rounded-xl"></div>
            </div>
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className='grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 relative overflow-visible'>
      {statsData.map((stat, index) => (
        <StatsCard key={stat.title} stat={stat} index={index} isLast={index === statsData.length - 1} />
      ))}
    </div>
  )
}

export default StatsGrid