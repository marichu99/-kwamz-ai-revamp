import { TrendingUp } from 'lucide-react'
import React from 'react'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

const chartData = [
  { name: 'Jan', revenue: 4000, users: 2400, orders: 240 },
  { name: 'Feb', revenue: 3000, users: 1398, orders: 221 },
  { name: 'Mar', revenue: 2000, users: 9800, orders: 229 },
  { name: 'Apr', revenue: 2780, users: 3908, orders: 200 },
  { name: 'May', revenue: 1890, users: 4800, orders: 218 },
  { name: 'Jun', revenue: 2390, users: 3800, orders: 250 },
  { name: 'Jul', revenue: 3490, users: 4300, orders: 210 }
]

function RevenueChart() {
  return (
    <div className='xl:col-span-2 bg-white/90 dark:bg-slate-800/90 backdrop-blur-xl rounded-2xl p-6 border border-slate-200/50 dark:border-slate-700/50 hover:shadow-2xl transition-all duration-300'>
      <div className='flex items-center justify-between mb-6'>
        <h3 className='text-xl font-bold text-slate-800 dark:text-white'>Revenue Overview</h3>
        <div className='flex items-center space-x-2'>
          <TrendingUp className='w-5 h-5 text-emerald-500' />
          <span className='text-sm font-medium text-emerald-600 dark:text-emerald-400'>+15.3% this month</span>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={chartData}>
          <defs>
            <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="#3B82F6" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
          <XAxis dataKey="name" stroke="#64748B" />
          <YAxis stroke="#64748B" />
          <Tooltip 
            contentStyle={{ 
              backgroundColor: '#F8FAFC', 
              border: '1px solid #E2E8F0', 
              borderRadius: '12px',
              boxShadow: '0 10px 25px rgba(0,0,0,0.1)'
            }} 
          />
          <Area type="monotone" dataKey="revenue" stroke="#3B82F6" strokeWidth={3} fillOpacity={1} fill="url(#colorRevenue)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

export default RevenueChart