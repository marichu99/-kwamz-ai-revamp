import React from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

const chartData = [
  { name: 'Jan', revenue: 4000, users: 2400, orders: 240 },
  { name: 'Feb', revenue: 3000, users: 1398, orders: 221 },
  { name: 'Mar', revenue: 2000, users: 9800, orders: 229 },
  { name: 'Apr', revenue: 2780, users: 3908, orders: 200 },
  { name: 'May', revenue: 1890, users: 4800, orders: 218 },
  { name: 'Jun', revenue: 2390, users: 3800, orders: 250 },
  { name: 'Jul', revenue: 3490, users: 4300, orders: 210 }
]

function OrdersChart() {
  return (
    <div className='bg-white/90 dark:bg-slate-800/90 backdrop-blur-xl rounded-2xl p-6 border border-slate-200/50 dark:border-slate-700/50 hover:shadow-2xl transition-all duration-300'>
      <h3 className='text-xl font-bold text-slate-800 dark:text-white mb-6'>Monthly Orders</h3>
      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={chartData}>
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
          <Bar dataKey="orders" fill="#8B5CF6" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export default OrdersChart