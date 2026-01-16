import React from 'react'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'

const CustomTooltip = ({ active, payload }) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload
    return (
      <div className="bg-white dark:bg-slate-800 p-3 rounded-xl shadow-lg border border-slate-200 dark:border-slate-700">
        <p className="font-semibold text-slate-800 dark:text-white">{data.name}</p>
        <p className="text-sm text-slate-600 dark:text-slate-400">
          {data.count?.toLocaleString() || 0} transactions ({data.value}%)
        </p>
      </div>
    )
  }
  return null
}

function TrafficSourcesChart({ data = [] }) {
  // Default colors if not provided
  const defaultColors = ['#3B82F6', '#10B981', '#F59E0B', '#8B5CF6', '#EF4444']

  const chartData = data.map((item, index) => ({
    ...item,
    color: item.color || defaultColors[index % defaultColors.length]
  }))

  if (!data || data.length === 0) {
    return (
      <div className='bg-white/90 dark:bg-slate-800/90 backdrop-blur-xl rounded-2xl p-6 border border-slate-200/50 dark:border-slate-700/50'>
        <h3 className='text-xl font-bold text-slate-800 dark:text-white mb-6'>Transaction Types</h3>
        <div className="flex items-center justify-center h-[200px] text-slate-500 dark:text-slate-400">
          No data available
        </div>
      </div>
    )
  }

  return (
    <div className='bg-white/90 dark:bg-slate-800/90 backdrop-blur-xl rounded-2xl p-6 border border-slate-200/50 dark:border-slate-700/50 hover:shadow-2xl transition-all duration-300'>
      <h3 className='text-xl font-bold text-slate-800 dark:text-white mb-6'>Transaction Types</h3>
      <ResponsiveContainer width="100%" height={200}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            innerRadius={40}
            outerRadius={80}
            paddingAngle={5}
            dataKey="value"
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
        </PieChart>
      </ResponsiveContainer>
      <div className='space-y-3 mt-4 max-h-[150px] overflow-y-auto'>
        {chartData.map((item) => (
          <div key={item.name} className='flex items-center justify-between'>
            <div className='flex items-center space-x-3 flex-1 min-w-0'>
              <div className='w-3 h-3 rounded-full flex-shrink-0' style={{ backgroundColor: item.color }}></div>
              <span className='text-sm text-slate-600 dark:text-slate-400 truncate' title={item.name}>
                {item.name}
              </span>
            </div>
            <span className='font-medium text-slate-800 dark:text-white ml-2'>{item.value}%</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default TrafficSourcesChart