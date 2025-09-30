import {
    LayoutDashboard,
    BarChart3,
    Users,
    Package,
    ShoppingCart,
    Settings,
    ChevronDown,
    ChevronRight,
    Zap,
    Wallet,
    LogOut
} from 'lucide-react';
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import UserSettingsModal from '../Pages/UserSettingsModal';

const menuItems = [
    {
        id: "dashboard",
        icon: LayoutDashboard,
        label: "Dashboard",
        badge: "New"
    },
    // {
    //     id: "analytics",
    //     icon: BarChart3,
    //     label: "Analytics",
    //     submenu: [
    //         { id: "overview", label: "Overview" },
    //         { id: "reports", label: "Reports" },
    //         { id: "insights", label: "Insights" },
    //         { id: "metrics", label: "Key Metrics" },
    //         { id: "performance", label: "Performance" }
    //     ]
    // },
    {
        id: "users",
        icon: Users,
        label: "Users",
        count: "12",
        submenu: [
            { id: "user-list", label: "Agents" },           
            { id: "agent-list", label: "Agencies" },           
            { id: "company-list", label: "Companies" },           
        ]
    },
    {
        id: "products",
        icon: Package,
        label: "Products",
        submenu: [
            { id: "catalog", label: "Product Catalog" },
            { id: "inventory", label: "Inventory" },
            { id: "categories", label: "Categories" },
            { id: "pricing", label: "Pricing" }
        ]
    },
    {
        id: "transactions",
        icon: Wallet,
        label: "Transactions",
    },
    // {
    //     id: "orders",
    //     icon: ShoppingCart,
    //     label: "Orders",
    //     badge: "3",
    //     submenu: [
    //         { id: "all-orders", label: "All Orders" },
    //         { id: "pending", label: "Pending Orders" },
    //         { id: "processing", label: "Processing" },
    //         { id: "shipped", label: "Shipped" }
    //     ]
    // },
];

function Sidebar({ collapsed, onToggle, currentPage, onPageChange }) {
    const [openSubmenus, setOpenSubmenus] = useState({ analytics: true });
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);
    const user = JSON.parse(localStorage.getItem("user"));
    const navigate = useNavigate();

    const toggleSubmenu = (itemId) => {
        setOpenSubmenus(prev => ({
            ...prev,
            [itemId]: !prev[itemId]
        }));
    };

    const handleItemClick = (itemId) => {
        if (menuItems.find(item => item.id === itemId)?.submenu) {
            toggleSubmenu(itemId);
        } else {
            onPageChange(itemId);
        }
    };

    const handleLogout = () => {
        navigate("/logout");
    };

    if (collapsed) {
        return (
            <div className='w-20 transition-all duration-300 ease-in-out bg-white/80 dark:bg-slate-900/80 backdrop-blur-xl border-r 
            border-slate-200/50 dark:border-slate-700/50 flex flex-col relative z-10'>
                {/* Logo */}
                <div className='p-4 border-b border-slate-200/50 dark:border-slate-700/50 flex justify-center'>
                    <div className='w-10 h-10 bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl flex items-center justify-center shadow-lg'>
                        <Zap className='w-6 h-6 text-white' />
                    </div>
                </div>

                {/* Navigation */}
                <nav className='flex-1 p-2 space-y-2 overflow-y-auto'>
                    {menuItems.map((item) => (
                        <button
                            key={item.id}
                            className={`w-full flex items-center justify-center p-3 rounded-xl transition-all duration-200 ${currentPage === item.id
                                ? 'bg-gradient-to-r from-blue-500 to-purple-600 text-white shadow-lg shadow-blue-500/25'
                                : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/50'
                            }`}
                            onClick={() => handleItemClick(item.id)}
                            title={item.label}
                        >
                            <item.icon className='w-5 h-5' />
                        </button>
                    ))}
                </nav>

                {/* User profile and Logout */}
                <div className='p-2 border-t border-slate-200/50 dark:border-slate-700/50 space-y-2'>
                    <div className='flex justify-center'>
                        <div className='w-10 h-10 rounded-full bg-gray-300 ring-2 ring-blue-500'></div>
                    </div>
                    <button
                        className='w-full flex items-center justify-center p-3 rounded-xl text-slate-600 dark:text-slate-300 hover:bg-red-50 dark:hover:bg-red-900/20 hover:text-red-600 dark:hover:text-red-400 transition-colors duration-200'
                        onClick={handleLogout}
                        title="Logout"
                    >
                        <LogOut className='w-5 h-5' />
                    </button>
                </div>
            </div>
        );
    }

    return (
        <>
            <div className='w-72 transition-all duration-300 ease-in-out bg-white/80 dark:bg-slate-900/80 backdrop-blur-xl border-r 
              border-slate-200/50 dark:border-slate-700/50 flex flex-col relative z-10'>
                {/* Logo */}
                <div className='p-6 border-b border-slate-200/50 dark:border-slate-700/50'>
                    <div className='flex items-center space-x-3'>
                        <div className='w-10 h-10 bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl flex items-center justify-center shadow-lg'>
                            <Zap className='w-6 h-6 text-white' />
                        </div>
                        <div>
                            <h1 className='text-xl font-bold text-slate-800 dark:text-white'>Kwamz-AI</h1>
                            <p className='text-xs text-slate-500 dark:text-slate-400'>Admin Panel</p>
                        </div>
                    </div>
                </div>

                {/* Navigation */}
                <nav className='flex-1 p-4 space-y-2 overflow-y-auto'>
                    {menuItems.map((item) => {
                        const isOpen = openSubmenus[item.id];
                        const hasSubmenu = item.submenu && item.submenu.length > 0;
                        const isActive = currentPage === item.id;

                        return (
                            <div key={item.id}>
                                <button
                                    className={`w-full flex items-center justify-between p-3 rounded-xl transition-all duration-200 ${isActive
                                        ? 'bg-gradient-to-r from-blue-500 to-purple-600 text-white shadow-lg shadow-blue-500/25'
                                        : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/50'
                                    }`}
                                    onClick={() => handleItemClick(item.id)}
                                >
                                    <div className='flex items-center space-x-3'>
                                        <item.icon className='w-5 h-5' />
                                        <span className='font-medium'>{item.label}</span>

                                        {/* Badges */}
                                        {item.badge && (
                                            <span className='px-2 py-1 text-xs bg-red-500 text-white rounded-full'>
                                                {item.badge}
                                            </span>
                                        )}
                                        {item.count && (
                                            <span className='px-2 py-1 text-xs bg-gray-200 text-gray-600 rounded-full dark:bg-slate-700 dark:text-slate-300'>
                                                {item.count}
                                            </span>
                                        )}
                                    </div>

                                    {/* Chevron icon for submenu */}
                                    {hasSubmenu && (
                                        <div className={`transition-transform duration-200 ${isOpen ? 'rotate-0' : ''}`}>
                                            {isOpen ? (
                                                <ChevronDown className='w-4 h-4' />
                                            ) : (
                                                <ChevronRight className='w-4 h-4' />
                                            )}
                                        </div>
                                    )}
                                </button>

                                {/* Submenu */}
                                {hasSubmenu && isOpen && (
                                    <div className='ml-8 mt-2 space-y-1'>
                                        {item.submenu.map((subItem) => (
                                            <button
                                                key={subItem.id}
                                                className={`w-full text-left p-2 rounded-lg text-sm transition-colors duration-150 ${currentPage === subItem.id
                                                    ? 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20'
                                                    : 'text-gray-600 dark:text-slate-400 hover:bg-gray-100 dark:hover:bg-slate-800/50 hover:text-gray-900 dark:hover:text-white'
                                                }`}
                                                onClick={() => onPageChange(subItem.id)}
                                            >
                                                {subItem.label}
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </nav>

                {/* User profile and Logout */}
                <div className='p-4 border-t border-slate-200/50 dark:border-slate-700/50 space-y-4'>
                    <div className='flex items-center space-x-3 p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50' onClick={() => setIsSettingsOpen(true)}>
                        <div className='w-10 h-10 rounded-full bg-gray-300 ring-2 ring-blue-500'></div>
                        <div className='flex-1 min-w-0'>
                            <p className='text-sm font-medium text-slate-800 dark:text-white truncate'>{user.username}</p>
                            <p className='text-xs text-slate-500 dark:text-slate-400 truncate'>Administrator</p>
                        </div>
                    </div>

                    <button
                        className='w-full flex items-center space-x-3 p-3 rounded-xl text-slate-600 dark:text-slate-300 hover:bg-red-50 dark:hover:bg-red-900/20 hover:text-red-600 dark:hover:text-red-400 transition-colors duration-200 group'
                        onClick={handleLogout}
                    >
                        <LogOut className='w-5 h-5 group-hover:scale-110 transition-transform' />
                        <span className='font-medium'>Logout</span>
                    </button>
                </div>
            </div>
            <UserSettingsModal
                key="user-settings-modal"
                isOpen={isSettingsOpen}
                onClose={() => setIsSettingsOpen(false)}
                userData={{
                    username: user.username,
                    email: user.email,
                    profileImage: user.image_loc
                }}
                onUpdateUser={(section, data) => console.log('Updating user:', section, data)}
            />
        </>
    );
}

export default Sidebar;