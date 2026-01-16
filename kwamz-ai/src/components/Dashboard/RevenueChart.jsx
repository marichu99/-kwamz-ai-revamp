import { TrendingUp, TrendingDown } from 'lucide-react'
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

function RevenueChart({ data = [], healthMetrics }) {
  const weeklyGrowth = healthMetrics?.weekly_growth || 0
  const isPositiveGrowth = weeklyGrowth >= 0

  // Transform data to show volume (deposits + withdrawals)
  const chartData = data.map(item => ({
    name: item.name,
    volume: item.volume || 0,
    deposits: item.deposits || 0,
    withdrawals: item.withdrawals || 0
  }))

  if (!data || data.length === 0) {
    return (
      <div className='xl:col-span-2 bg-white/90 dark:bg-slate-800/90 backdrop-blur-xl rounded-2xl p-6 border border-slate-200/50 dark:border-slate-700/50'>
        <div className='flex items-center justify-between mb-6'>
          <h3 className='text-xl font-bold text-slate-800 dark:text-white'>Transaction Volume</h3>
        </div>
        <div className="flex items-center justify-center h-[300px] text-slate-500 dark:text-slate-400">
          No data available
        </div>
      </div>
    )
  }

  return (
    <div className='xl:col-span-2 bg-white/90 dark:bg-slate-800/90 backdrop-blur-xl rounded-2xl p-6 border border-slate-200/50 dark:border-slate-700/50 hover:shadow-2xl transition-all duration-300'>
      <div className='flex items-center justify-between mb-6'>
        <h3 className='text-xl font-bold text-slate-800 dark:text-white'>Transaction Volume</h3>
        <div className='flex items-center space-x-2'>
          {isPositiveGrowth ? (
            <TrendingUp className='w-5 h-5 text-emerald-500' />
          ) : (
            <TrendingDown className='w-5 h-5 text-red-500' />
          )}
          <span className={`text-sm font-medium ${isPositiveGrowth ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
            {isPositiveGrowth ? '+' : ''}{weeklyGrowth.toFixed(1)}% this week
          </span>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={chartData}>
          <defs>
            <linearGradient id="colorVolume" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="#3B82F6" stopOpacity={0}/>
            </linearGradient>
            <linearGradient id="colorDeposits" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#10B981" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="#10B981" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" className="dark:stroke-slate-700" />
          <XAxis dataKey="name" stroke="#64748B" fontSize={12} />
          <YAxis stroke="#64748B" fontSize={12} tickFormatter={formatCurrency} />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey="volume"
            name="Total Volume"
            stroke="#3B82F6"
            strokeWidth={3}
            fillOpacity={1}
            fill="url(#colorVolume)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

export default RevenueChart