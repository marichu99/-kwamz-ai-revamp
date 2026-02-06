import { Bell, ChevronDown, Clock, CheckCircle, Filter, Menu, Plus, Search, Settings, Sun } from 'lucide-react';
import React from 'react';
import UserDropdown from '../Dashboard/UserDropdown';
import { useNavigate } from 'react-router-dom';

function Header({ sideBarCollapsed, onToggleSideBar, currentPage, setCurrentPage, billingStatus }) {
    const navigate = useNavigate();
    const user = JSON.parse(localStorage.getItem("user"));

    return (
        <div className='bg-white/80 dark:bg-slate-900/80 backdrop-blur-xl border-b border-slate-200/50 dark:border-slate-700/50 px-3 py-3 sm:px-6 sm:py-4'>
            <div className='flex items-center justify-between'>
                {/* Left section */}
                <div className='flex items-center space-x-4'>
                    <button
                        className='p-2 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors'
                        onClick={onToggleSideBar}
                    >
                        <Menu />
                    </button>

                    <div className="hidden md:block">
                        <h1 className="text-2xl font-black text-slate-800 dark:text-white">
                            {currentPage === 'transactions' ? 'Transactions' : 'Dashboard'}
                        </h1>
                        <p className="text-gray-600 dark:text-gray-300">
                            Welcome back {user?.username || "Guest"}, here's what's happening today
                        </p>
                    </div>
                </div>


                {/* Right */}
                <div className='flex items-center space-x-3'>
                    {/* Billing status badge */}
                    {billingStatus?.status === 'TRIAL' && (
                        <button
                            onClick={() => navigate('/checkout')}
                            className='hidden sm:flex items-center space-x-1.5 py-1.5 px-3 bg-amber-50 border border-amber-200 text-amber-700 rounded-lg hover:bg-amber-100 transition-all'
                        >
                            <Clock className='w-3.5 h-3.5' />
                            <span className='text-xs font-medium'>Trial: {billingStatus.trial_days_remaining}d left</span>
                        </button>
                    )}
                    {billingStatus?.status === 'PAID' && (
                        <div className='hidden sm:flex items-center space-x-1.5 py-1.5 px-3 bg-green-50 border border-green-200 text-green-700 rounded-lg'>
                            <CheckCircle className='w-3.5 h-3.5' />
                            <span className='text-xs font-medium'>Active</span>
                        </div>
                    )}
                    <button className='hidden lg:flex items-center space-x-2 py-2 px-4 bg-gradient-to-r
                from-blue-500 to-purple-600 text-white rounded-xl hover:shadow transition-all'>
                        <Plus className='w-4 h-4' />
                        <span className='text-sm font-medium'>New</span>
                    </button>
                    <button className='p-2.5 rounded-xl text-slate-600 dark:text-slate-300 
                hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors'>
                        <Sun className='w-5 h-5' />
                    </button>
                    <button className='relative p-2.5 rounded-xl text-slate-600 
                dark:text-slate-300 hover:bg-slate-100 
                dark:hover:bg-slate-800 transition-colors'>
                        <Bell className='w-5 h-5' />
                        <span className='absolute -top-1 w-5 h-5 bg-red-500 
                    text-white text-xs rounded-full flex items-center justify-center'>3</span>
                    </button>
                    <button className='relative p-2.5 rounded-xl text-slate-600 
                dark:text-slate-300 hover:bg-slate-100 
                dark:hover:bg-slate-800 transition-colors'>
                        <Settings className='w-5 h-5' />
                    </button>
                    <UserDropdown
                        user={{
                            name: user.username,
                            email: user.email,
                            role: 'Admin',
                            avatar: user.image_log || ''
                        }}
                        onLogout={() => {
                            navigate("/logout");
                            console.log('User logged out');
                        }}
                    />
                </div>
            </div>
        </div>
    );
}

export default Header;