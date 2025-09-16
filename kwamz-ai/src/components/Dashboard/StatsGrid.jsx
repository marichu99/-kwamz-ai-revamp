import { Users, DollarSign, ShoppingCart, Target } from 'lucide-react'
import React from 'react'
import StatsCard from './StatsCard'

const statsData = [
  {
    title: 'Total Revenue',
    value: '$124,563',
    change: '+12.5%',
    trend: 'up',
    icon: DollarSign,
    color: 'emerald',
    bgGradient: 'from-emerald-500/20 to-green-500/20'
  },
  {
    title: 'Active Agencies',
    value: '23,459',
    change: '+8.2%',
    trend: 'up',
    icon: Users,
    color: 'blue',
    bgGradient: 'from-blue-500/20 to-cyan-500/20'
  },
  {
    title: 'Commissions',
    value: '1,847',
    change: '-3.1%',
    trend: 'down',
    icon: ShoppingCart,
    color: 'purple',
    bgGradient: 'from-purple-500/20 to-pink-500/20'
  },
  {
    title: 'Daily Annualized Rate',
    value: '3.24%',
    change: '+0.8%',
    trend: 'up',
    icon: Target,
    color: 'orange',
    bgGradient: 'from-orange-500/20 to-red-500/20'
  }
]

function StatsGrid() {
  return (
    <div className='grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 relative overflow-visible'>
      {statsData.map((stat, index) => (
        <StatsCard key={stat.title} stat={stat} index={index} isLast={index === statsData.length - 1} />
      ))}
    </div>

  )
}

export default StatsGrid