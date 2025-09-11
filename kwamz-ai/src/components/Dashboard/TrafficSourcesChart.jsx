import React from 'react'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'

const pieData = [
  { name: 'Desktop', value: 65, color: '#3B82F6' },
  { name: 'Mobile', value: 25, color: '#10B981' },
  { name: 'Tablet', value: 10, color: '#F59E0B' }
]

function TrafficSourcesChart() {
  return (
    <div className='bg-white/90 dark:bg-slate-800/90 backdrop-blur-xl rounded-2xl p-6 border border-slate-200/50 dark:border-slate-700/50 hover:shadow-2xl transition-all duration-300'>
      <h3 className='text-xl font-bold text-slate-800 dark:text-white mb-6'>Traffic Sources</h3>
      <ResponsiveContainer width="100%" height={200}>
        <PieChart>
          <Pie
            data={pieData}
            cx="50%"
            cy="50%"
            innerRadius={40}
            outerRadius={80}
            paddingAngle={5}
            dataKey="value"
          >
            {pieData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip />
        </PieChart>
      </ResponsiveContainer>
      <div className='space-y-3 mt-4'>
        {pieData.map((item) => (
          <div key={item.name} className='flex items-center justify-between'>
            <div className='flex items-center space-x-3'>
              <div className={`w-3 h-3 rounded-full`} style={{ backgroundColor: item.color }}></div>
              <span className='text-sm text-slate-600 dark:text-slate-400'>{item.name}</span>
            </div>
            <span className='font-medium text-slate-800 dark:text-white'>{item.value}%</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default TrafficSourcesChart