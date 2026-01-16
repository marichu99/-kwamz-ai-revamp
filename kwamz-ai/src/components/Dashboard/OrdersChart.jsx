import React from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'

const formatNumber = (value) => {
  if (value >= 1000000) {
    return `${(value / 1000000).toFixed(1)}M`
  } else if (value >= 1000) {
    return `${(value / 1000).toFixed(0)}K`
  }
  return value
}

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white dark:bg-slate-800 p-4 rounded-xl shadow-lg border border-slate-200 dark:border-slate-700">
        <p className="font-semibold text-slate-800 dark:text-white mb-2">{label}</p>
        {payload.map((entry, index) => (
          <p key={index} className="text-sm" style={{ color: entry.color }}>
            {entry.name}: {formatNumber(entry.value)}
          </p>
        ))}
      </div>
    )
  }
  return null
}

function OrdersChart({ data = [] }) {
  // Transform data to show transaction counts
  const chartData = data.map(item => ({
    name: item.name,
    transactions: item.transactions || 0
  }))

  if (!data || data.length === 0) {
    return (
      <div className='bg-white/90 dark:bg-slate-800/90 backdrop-blur-xl rounded-2xl p-6 border border-slate-200/50 dark:border-slate-700/50'>
        <h3 className='text-xl font-bold text-slate-800 dark:text-white mb-6'>Monthly Transactions</h3>
        <div className="flex items-center justify-center h-[250px] text-slate-500 dark:text-slate-400">
          No data available
        </div>
      </div>
    )
  }

  return (
    <div className='bg-white/90 dark:bg-slate-800/90 backdrop-blur-xl rounded-2xl p-6 border border-slate-200/50 dark:border-slate-700/50 hover:shadow-2xl transition-all duration-300'>
      <h3 className='text-xl font-bold text-slate-800 dark:text-white mb-6'>Monthly Transactions</h3>
      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" className="dark:stroke-slate-700" />
          <XAxis dataKey="name" stroke="#64748B" fontSize={12} />
          <YAxis stroke="#64748B" fontSize={12} tickFormatter={formatNumber} />
          <Tooltip content={<CustomTooltip />} />
          <Bar
            dataKey="transactions"
            name="Transactions"
            fill="#8B5CF6"
            radius={[4, 4, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export default OrdersChart