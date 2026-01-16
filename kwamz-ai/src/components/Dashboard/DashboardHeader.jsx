import React from 'react'
import { RefreshCw, TrendingUp, TrendingDown, Minus, Calendar } from 'lucide-react'

function DashboardHeader({ onRefresh, selectedDays, onDaysChange, healthMetrics }) {
  const dayOptions = [
    { value: 7, label: '7 days' },
    { value: 14, label: '14 days' },
    { value: 30, label: '30 days' },
    { value: 60, label: '60 days' },
    { value: 90, label: '90 days' }
  ]

  const getMomentumBadge = () => {
    if (!healthMetrics) return null

    const momentum = healthMetrics.growth_momentum
    const successRate = healthMetrics.success_rate

    let bgColor, textColor, icon, label

    switch (momentum) {
      case 'accelerating':
        bgColor = 'bg-emerald-100 dark:bg-emerald-900/30'
        textColor = 'text-emerald-700 dark:text-emerald-400'
        icon = <TrendingUp className="w-4 h-4" />
        label = 'Growth Accelerating'
        break
      case 'declining':
        bgColor = 'bg-red-100 dark:bg-red-900/30'
        textColor = 'text-red-700 dark:text-red-400'
        icon = <TrendingDown className="w-4 h-4" />
        label = 'Declining'
        break
      default:
        bgColor = 'bg-blue-100 dark:bg-blue-900/30'
        textColor = 'text-blue-700 dark:text-blue-400'
        icon = <Minus className="w-4 h-4" />
        label = 'Stable'
    }

    return (
      <div className={`flex items-center space-x-2 px-3 py-1.5 rounded-full ${bgColor} ${textColor}`}>
        {icon}
        <span className="text-sm font-medium">{label}</span>
        <span className="text-xs opacity-75">({successRate}% success rate)</span>
      </div>
    )
  }

  return (
    <div className='flex flex-col lg:flex-row lg:items-center justify-between gap-4'>
      <div>
        <h1 className='text-3xl md:text-4xl font-bold bg-gradient-to-r from-slate-800 via-blue-600 to-purple-600 dark:from-white dark:via-blue-400 dark:to-purple-400 bg-clip-text text-transparent mb-2'>
          Business Analytics
        </h1>
        <div className="flex flex-wrap items-center gap-3">
          <p className='text-slate-600 dark:text-slate-400'>
            Transaction insights and performance metrics
          </p>
          {getMomentumBadge()}
        </div>
      </div>

      <div className='flex flex-wrap items-center gap-3'>
        {/* Date Range Selector */}
        <div className="flex items-center space-x-2 bg-white/80 dark:bg-slate-800/80 rounded-xl px-3 py-2 border border-slate-200 dark:border-slate-700">
          <Calendar className="w-4 h-4 text-slate-500" />
          <select
            value={selectedDays}
            onChange={(e) => onDaysChange(Number(e.target.value))}
            className="bg-transparent text-sm font-medium text-slate-700 dark:text-slate-300 focus:outline-none cursor-pointer"
          >
            {dayOptions.map(option => (
              <option key={option.value} value={option.value}>
                Last {option.label}
              </option>
            ))}
          </select>
        </div>

        {/* Refresh Button */}
        <button
          onClick={onRefresh}
          className="flex items-center space-x-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-medium transition-all duration-200 shadow-lg shadow-blue-600/30 hover:shadow-blue-600/40"
        >
          <RefreshCw className="w-4 h-4" />
          <span>Refresh</span>
        </button>
      </div>
    </div>
  )
}

export default DashboardHeader