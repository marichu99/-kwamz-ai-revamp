import { ArrowUp, ArrowDown } from 'lucide-react'
import React, { useState, useEffect } from 'react'

function StatsCard({ stat, index }) {
  const [isVisible, setIsVisible] = useState(false)
  const Icon = stat.icon
  
  useEffect(() => {
    const timer = setTimeout(() => setIsVisible(true), index * 100)
    return () => clearTimeout(timer)
  }, [index])
  
  return (
    <div className={`transform transition-all duration-500 ${isVisible ? 'translate-y-0 opacity-100' : 'translate-y-4 opacity-0'}`}>
      <div className='bg-white/90 dark:bg-slate-800/90 backdrop-blur-xl rounded-2xl p-6 border 
        border-slate-200/50 dark:border-slate-700/50 hover:shadow-2xl hover:shadow-slate-200/30 dark:hover:shadow-slate-900/30 
        transition-all duration-300 group hover:-translate-y-1'>
        <div className='flex items-start justify-between mb-4'>
          <div className='flex-1'>
            <p className='text-sm font-medium text-slate-600 dark:text-slate-400 mb-2'>
              {stat.title}
            </p>
            <p className='text-3xl font-bold text-slate-800 dark:text-white mb-3'>
              {stat.value}
            </p>
            <div className='flex items-center space-x-2'>
              {stat.trend === 'up' ? (
                <ArrowUp className='w-4 h-4 text-emerald-500' />
              ) : (
                <ArrowDown className='w-4 h-4 text-red-500' />
              )}
              <span className={`font-medium ${stat.trend === 'up' ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
                {stat.change}
              </span>
              <span className='text-sm text-slate-500 dark:text-slate-400'>vs last month</span>
            </div>
          </div>
          <div className={`p-3 rounded-xl bg-gradient-to-br ${stat.bgGradient} group-hover:scale-110 transition-transform duration-300`}>
            <Icon className={`w-6 h-6 text-${stat.color}-600`} />
          </div>
        </div>
      </div>
    </div>
  )
}

export default StatsCard