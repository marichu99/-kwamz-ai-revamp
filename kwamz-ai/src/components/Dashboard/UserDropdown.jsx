import { ChevronDown, User, Settings, HelpCircle, LogOut, Shield } from 'lucide-react'
import React, { useState, useRef, useEffect } from 'react'

function UserDropdown({ user, onLogout }) {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef(null)

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [])

  const toggleDropdown = () => {
    setIsOpen(!isOpen)
  }

  const handleLogout = () => {
    setIsOpen(false)
    onLogout()
  }

  const menuItems = [
    {
      icon: User,
      label: 'Profile',
      action: () => {
        setIsOpen(false)
        // Handle profile navigation
        console.log('Navigate to profile')
      }
    },
    {
      icon: Settings,
      label: 'Settings',
      action: () => {
        setIsOpen(false)
        // Handle settings navigation
        console.log('Navigate to settings')
      }
    },
    {
      icon: Shield,
      label: 'Privacy',
      action: () => {
        setIsOpen(false)
        // Handle privacy navigation
        console.log('Navigate to privacy')
      }
    },
    {
      icon: HelpCircle,
      label: 'Help & Support',
      action: () => {
        setIsOpen(false)
        // Handle help navigation
        console.log('Navigate to help')
      }
    }
  ]

  return (
    <div className='relative z-[9999]' ref={dropdownRef}>
      {/* User Profile Trigger */}
      <div
        className='flex items-center space-x-3 pl-3 border-l border-slate-200 dark:border-slate-700 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/50 rounded-lg p-2 transition-colors duration-200'
        onClick={toggleDropdown}
      >
        <img
          src={user?.avatar || 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=100&h=100&fit=crop&crop=face'}
          alt='User'
          className='w-8 h-8 rounded-full ring-2 ring-blue-500 object-cover'
        />
        <div className='hidden md:block'>
          <p className='text-sm font-medium text-slate-700 dark:text-slate-300'>{user?.name || 'Martin Mabera'}</p>
          <p className='text-xs text-slate-500 dark:text-slate-400'>{user?.role || 'Admin'}</p>
        </div>
        <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
      </div>

      {/* Dropdown Menu */}
      {isOpen && (
        <div
          className='absolute right-0 top-full mt-2 w-64 bg-white/95 dark:bg-slate-800/95 backdrop-blur-xl 
      rounded-2xl border border-slate-200/50 dark:border-slate-700/50 shadow-2xl 
      shadow-slate-200/20 dark:shadow-slate-900/20 py-2 z-[99999] animate-fadeIn'
        >
          {/* User Info Header */}
          <div className='px-4 py-3 border-b border-slate-100 dark:border-slate-700'>
            <div className='flex items-center space-x-3'>
              <img
                src={user?.avatar || 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=100&h=100&fit=crop&crop=face'}
                alt='User'
                className='w-10 h-10 rounded-full ring-2 ring-blue-500 object-cover'
              />
              <div>
                <p className='font-medium text-slate-800 dark:text-white'>{user?.name || 'Martin Mabera'}</p>
                <p className='text-sm text-slate-500 dark:text-slate-400'>{user?.email || 'martin@example.com'}</p>
              </div>
            </div>
          </div>

          {/* Menu Items */}
          <div className='py-2'>
            {menuItems.map((item, index) => {
              const Icon = item.icon
              return (
                <button
                  key={index}
                  onClick={item.action}
                  className='w-full flex items-center space-x-3 px-4 py-3 text-left hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors duration-200 group'
                >
                  <Icon className='w-4 h-4 text-slate-500 dark:text-slate-400 group-hover:text-slate-600 dark:group-hover:text-slate-300' />
                  <span className='text-sm text-slate-700 dark:text-slate-300 group-hover:text-slate-800 dark:group-hover:text-white'>
                    {item.label}
                  </span>
                </button>
              )
            })}
          </div>

          {/* Divider */}
          <div className='border-t border-slate-100 dark:border-slate-700 my-1'></div>

          {/* Logout Button */}
          <button
            onClick={handleLogout}
            className='w-full flex items-center space-x-3 px-4 py-3 text-left hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors duration-200 group'
          >
            <LogOut className='w-4 h-4 text-slate-500 dark:text-slate-400 group-hover:text-red-600 dark:group-hover:text-red-400' />
            <span className='text-sm text-slate-700 dark:text-slate-300 group-hover:text-red-600 dark:group-hover:text-red-400'>
              Sign Out
            </span>
          </button>
        </div>
      )}

      <style jsx>{`
    @keyframes fadeIn {
      from {
        opacity: 0;
        transform: translateY(-10px) scale(0.95);
      }
      to {
        opacity: 1;
        transform: translateY(0) scale(1);
      }
    }
    .animate-fadeIn {
      animation: fadeIn 0.2s ease-out;
    }
  `}</style>
    </div>

  )
}

export default UserDropdown