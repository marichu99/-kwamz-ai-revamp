// src/config/menuConfig.js
import {
    LayoutDashboard,
    Users,
    Package,
    Wallet,
    Wrench,
    ShoppingCart,
    Settings,
    Shield,
    TrendingUp,
    FileText,
    Clock,
    Mail
} from 'lucide-react';

export const adminMenuItems = [
    {
        id: "dashboard",
        icon: LayoutDashboard,
        label: "Dashboard",
        badge: "New"
    },
    {
        id: "users",
        icon: Users,
        label: "Users",
        count: "12",
        submenu: [
            // { id: "user-list", label: "Agents" },           
            { id: "system-user-list", label: "System Users" },           
            { id: "company-hierarchy", label: "Company Hierarchy" }          
        ]
    },
    {
        id: "setup",
        icon: Wrench,
        label: "Setup",
        submenu: [
            { id: "bank-list", label: "Bank Details" },
            { id: "configs", label: "System Configs" },
            { id: "report-schedules", label: "Report Schedules" },
        ]
    },
    
    {
        id: "transactions",
        icon: Wallet,
        label: "Transactions",
    },
];

export const agentMenuItems = [
    {
        id: "dashboard",
        icon: LayoutDashboard,
        label: "Dashboard",
    },
    {
        id: "products",
        icon: Package,
        label: "Products",
        submenu: [
            { id: "agent-companies", label: "Companies" },
            { id: "inventory", label: "Inventory" },
        ]
    },
    {
        id: "transactions",
        icon: Wallet,
        label: "My Transactions",
    },
];


const userMenuItems = [
    {
        id: "dashboard",
        icon: LayoutDashboard,
        label: "Dashboard",
        badge: "New"
    },
    {
        id: "users",
        icon: Users,
        label: "Users",
        count: "12",
        submenu: [
            { id: "user-list", label: "Agents" },           
            { id: "agent-list", label: "Tills" },           
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
            { id: "transactions-list", label: "Transactions" },
            { id: "checkout", label: "Pricing" },
            { id: "pesapal", label: "PesaPal" }
        ]
    },
    {
        id: "transactions",
        icon: Wallet,
        label: "Transactions",
    },
    {
        id: "reports",
        icon: Clock,
        label: "Reports",
        submenu: [
            { id: "report-schedules", label: "Report Schedules" },
        ]
    },
];

export const getMenuItems = (role) => {
    switch(role?.toLowerCase()) {
        case 'admin':
        case 'administrator':
            return adminMenuItems;
        case 'agent':
            return agentMenuItems;
        case 'user':
        case 'customer':
            return userMenuItems;
        default:
            return userMenuItems;
    }
};

export const getRoleDisplayName = (role) => {
    switch(role?.toLowerCase()) {
        case 'admin':
        case 'administrator':
            return 'Admin Panel';
        case 'agent':
            return 'Agent Panel';
        case 'user':
        case 'customer':
            return 'User Panel';
        default:
            return 'Panel';
    }
};  