import React from 'react'

function DashboardHeader({ activeTab, setActiveTab }) {
  return (
    <div className='flex flex-col md:flex-row md:items-center justify-between mb-8'>
      <div>
        <h1 className='text-4xl font-bold bg-gradient-to-r from-slate-800 via-blue-600 to-purple-600 dark:from-white dark:via-blue-400 dark:to-purple-400 bg-clip-text text-transparent mb-2'>
          Analytics Dashboard
        </h1>
        <p className='text-slate-600 dark:text-slate-400'>Welcome back! Here's what's happening with your business today.</p>
      </div>
      <div className='flex space-x-2 mt-4 md:mt-0'>
        <button 
          onClick={() => setActiveTab('overview')}
          className={`px-4 py-2 rounded-xl font-medium transition-all duration-200 ${
            activeTab === 'overview' 
              ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/30' 
              : 'bg-white/80 dark:bg-slate-800/80 text-slate-600 dark:text-slate-300 hover:bg-blue-50 dark:hover:bg-slate-700'
          }`}
        >
          Overview
        </button>
        <button 
          onClick={() => setActiveTab('analytics')}
          className={`px-4 py-2 rounded-xl font-medium transition-all duration-200 ${
            activeTab === 'analytics' 
              ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/30' 
              : 'bg-white/80 dark:bg-slate-800/80 text-slate-600 dark:text-slate-300 hover:bg-blue-50 dark:hover:bg-slate-700'
          }`}
        >
          Analytics
        </button>
      </div>
    </div>
  )
}

export default DashboardHeader