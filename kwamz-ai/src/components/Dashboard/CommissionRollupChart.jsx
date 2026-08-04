import { TrendingUp, TrendingDown, Landmark } from 'lucide-react'
import React from 'react'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

const formatCurrency = (value) => {
  if (value >= 1000000) {
    return `${(value / 1000000).toFixed(1)}M`
  } else if (value >= 1000) {
    return `${(value / 1000).toFixed(0)}K`
  }
  return value.toFixed(0)
}

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white dark:bg-slate-800 p-4 rounded-xl shadow-lg border border-slate-200 dark:border-slate-700">
        <p className="font-semibold text-slate-800 dark:text-white mb-2">{label}</p>
        {payload.map((entry, index) => (
          <p key={index} className="text-sm" style={{ color: entry.color }}>
            {entry.name}: KES {formatCurrency(entry.value)}
          </p>
        ))}
      </div>
    )
  }
  return null
}

function CommissionRollupChart({ data = [], growth = 0, isOnboarding = false }) {
  const isPositiveGrowth = growth >= 0

  const chartData = data.map(item => ({
    name: item.name,
    amount: item.amount || 0
  }))

  if (!data || data.length === 0) {
    return (
      <div className='bg-white/90 dark:bg-slate-800/90 backdrop-blur-xl rounded-2xl p-6 border border-slate-200/50 dark:border-slate-700/50'>
        <div className='flex items-center justify-between mb-6'>
          <h3 className='text-xl font-bold text-slate-800 dark:text-white'>Commission Rollup to Head Office</h3>
        </div>
        <div className="flex flex-col items-center justify-center h-[300px] gap-3 text-center px-6">
          {isOnboarding ? (
            <>
              <Landmark className="w-10 h-10 text-slate-300 dark:text-slate-600" />
              <p className="text-sm font-medium text-slate-500 dark:text-slate-400">
                Commission rollup to head office will appear here once your company information has been onboarded to the system.
              </p>
            </>
          ) : (
            <p className="text-slate-500 dark:text-slate-400">No data available</p>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className='bg-white/90 dark:bg-slate-800/90 backdrop-blur-xl rounded-2xl p-6 border border-slate-200/50 dark:border-slate-700/50 hover:shadow-2xl transition-all duration-300'>
      <div className='flex items-center justify-between mb-6'>
        <h3 className='text-xl font-bold text-slate-800 dark:text-white'>Commission Rollup to Head Office</h3>
        <div className='flex items-center space-x-2'>
          {isPositiveGrowth ? (
            <TrendingUp className='w-5 h-5 text-emerald-500' />
          ) : (
            <TrendingDown className='w-5 h-5 text-red-500' />
          )}
          <span className={`text-sm font-medium ${isPositiveGrowth ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
            {isPositiveGrowth ? '+' : ''}{growth.toFixed(1)}% vs last month
          </span>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={chartData}>
          <defs>
            <linearGradient id="colorCommissionRollup" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#F59E0B" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="#F59E0B" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" className="dark:stroke-slate-700" />
          <XAxis dataKey="name" stroke="#64748B" fontSize={12} />
          <YAxis stroke="#64748B" fontSize={12} tickFormatter={formatCurrency} />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey="amount"
            name="Commission Rollup"
            stroke="#F59E0B"
            strokeWidth={3}
            fillOpacity={1}
            fill="url(#colorCommissionRollup)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

export default CommissionRollupChart
