import { Activity, Clock, ArrowDownLeft, ArrowUpRight, Receipt } from 'lucide-react'
import React from 'react'

function ActivityItem({ activity, index }) {
  const getTypeStyles = (type) => {
    switch (type) {
      case 'deposit':
        return {
          dotColor: 'bg-emerald-500',
          icon: ArrowDownLeft,
          iconColor: 'text-emerald-500'
        }
      case 'withdrawal':
        return {
          dotColor: 'bg-red-500',
          icon: ArrowUpRight,
          iconColor: 'text-red-500'
        }
      default:
        return {
          dotColor: 'bg-blue-500',
          icon: Receipt,
          iconColor: 'text-blue-500'
        }
    }
  }

  const styles = getTypeStyles(activity.type)
  const IconComponent = styles.icon

  return (
    <div
      className='flex items-start space-x-3 p-3 rounded-xl hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-all duration-200 transform hover:scale-[1.02] animate-fade-in'
      style={{ animationDelay: `${index * 100}ms`, animationFillMode: 'forwards' }}
    >
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center bg-slate-100 dark:bg-slate-700`}>
        <IconComponent className={`w-4 h-4 ${styles.iconColor}`} />
      </div>
      <div className='flex-1 min-w-0'>
        <p className='text-sm text-slate-800 dark:text-white font-medium truncate' title={activity.action}>
          {activity.action}
        </p>
        <div className='flex items-center space-x-2 mt-1'>
          <Clock className='w-3 h-3 text-slate-400 flex-shrink-0' />
          <p className='text-xs text-slate-500 dark:text-slate-400'>{activity.time}</p>
          {activity.receipt_no && (
            <>
              <span className='text-slate-300 dark:text-slate-600'>•</span>
              <p className='text-xs text-slate-400 dark:text-slate-500 truncate' title={activity.receipt_no}>
                {activity.receipt_no}
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

function RecentActivity({ transactions = [] }) {
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
          <h3 className='text-xl font-bold text-slate-800 dark:text-white'>Recent Transactions</h3>
          <Activity className='w-5 h-5 text-blue-500' />
        </div>

        {transactions.length === 0 ? (
          <div className="flex items-center justify-center h-[200px] text-slate-500 dark:text-slate-400">
            No recent transactions
          </div>
        ) : (
          <div className='space-y-2 max-h-[300px] overflow-y-auto'>
            {transactions.map((transaction, index) => (
              <ActivityItem
                key={transaction.id || index}
                activity={transaction}
                index={index}
              />
            ))}
          </div>
        )}
      </div>
    </>
  )
}

export default RecentActivity