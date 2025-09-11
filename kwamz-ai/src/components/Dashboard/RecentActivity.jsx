import { Activity, Clock } from 'lucide-react'
import React from 'react'

const recentActivity = [
  { id: 1, action: 'New user registered', time: '2 min ago', type: 'user' },
  { id: 2, action: 'Order #1247 completed', time: '5 min ago', type: 'order' },
  { id: 3, action: 'Payment processed', time: '12 min ago', type: 'payment' },
  { id: 4, action: 'New review received', time: '18 min ago', type: 'review' },
  { id: 5, action: 'Product updated', time: '25 min ago', type: 'product' }
]

function ActivityItem({ activity, index }) {
  return (
    <div 
      className={`flex items-start space-x-3 p-3 rounded-xl hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-all duration-200 transform hover:scale-[1.02] opacity-0 animate-fade-in`}
      style={{ animationDelay: `${index * 100}ms`, animationFillMode: 'forwards' }}
    >
      <div className={`w-2 h-2 rounded-full mt-2 ${
        activity.type === 'user' ? 'bg-blue-500' :
        activity.type === 'order' ? 'bg-green-500' :
        activity.type === 'payment' ? 'bg-purple-500' :
        activity.type === 'review' ? 'bg-yellow-500' :
        'bg-gray-500'
      }`}></div>
      <div className='flex-1'>
        <p className='text-sm text-slate-800 dark:text-white font-medium'>{activity.action}</p>
        <div className='flex items-center space-x-1 mt-1'>
          <Clock className='w-3 h-3 text-slate-400' />
          <p className='text-xs text-slate-500 dark:text-slate-400'>{activity.time}</p>
        </div>
      </div>
    </div>
  )
}

function RecentActivity() {
  return (
    <>
      <style jsx>{`
        @keyframes fade-in {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        
        .animate-fade-in {
          animation: fade-in 0.5s ease-out;
        }
      `}</style>
      
      <div className='bg-white/90 dark:bg-slate-800/90 backdrop-blur-xl rounded-2xl p-6 border border-slate-200/50 dark:border-slate-700/50 hover:shadow-2xl transition-all duration-300'>
        <div className='flex items-center justify-between mb-6'>
          <h3 className='text-xl font-bold text-slate-800 dark:text-white'>Recent Activity</h3>
          <Activity className='w-5 h-5 text-blue-500' />
        </div>
        <div className='space-y-4'>
          {recentActivity.map((activity, index) => (
            <ActivityItem key={activity.id} activity={activity} index={index} />
          ))}
        </div>
        <button className='w-full mt-4 py-2 text-sm font-medium text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-xl transition-colors duration-200'>
          View all activity
        </button>
      </div>
    </>
  )
}

export default RecentActivity