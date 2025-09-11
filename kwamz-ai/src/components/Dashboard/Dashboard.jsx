import React, { useState } from 'react'
import StatsGrid from './StatsGrid'
import DashboardHeader from './DashboardHeader'
import RevenueChart from './RevenueChart'
import TrafficSourcesChart from './TrafficSourcesChart'
import OrdersChart from './OrdersChart'
import RecentActivity from './RecentActivity'

function Dashboard() {
  const [activeTab, setActiveTab] = useState('overview')

  return (
    <div className='min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50 dark:from-slate-900 dark:via-slate-800 dark:to-slate-900 p-6'>
      <div className='max-w-7xl mx-auto space-y-8'>
        
        {/* Header with navigation */}
        <DashboardHeader activeTab={activeTab} setActiveTab={setActiveTab} />

        {/* Stats Grid */}
        <StatsGrid />

        {/* Charts Section */}
        <div className='grid grid-cols-1 xl:grid-cols-3 gap-6'>
          <RevenueChart />
          <TrafficSourcesChart />
        </div>

        {/* Bottom Section */}
        <div className='grid grid-cols-1 xl:grid-cols-2 gap-6'>
          <OrdersChart />
          <RecentActivity />
        </div>
        
      </div>
    </div>
  )
}

export default Dashboard