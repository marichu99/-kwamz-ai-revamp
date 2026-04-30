// src/config/menuConfig.js
import {
    LayoutDashboard,
    Users,
    Package,
    Wallet,
    Wrench,
    Clock,
    Shield,
    Repeat,
    Download,
    CreditCard,
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
            { id: "fraud-alerts", label: "Fraud Alerts" },
        ]
    },
    
    {
        id: "transactions",
        icon: Wallet,
        label: "Transactions",
    },
    {
        id: "admin-billing",
        icon: CreditCard,
        label: "Billing",
    },
    {
        id: "agent-download",
        icon: Download,
        label: "Download Agent",
    },
];

export const agentMenuItems = [
    {
        id: "dashboard",
        icon: LayoutDashboard,
        label: "Dashboard",
    },
    {
        id: "agent-companies",
        icon: Package,
        label: "Companies",
    },
    {
        id: "transactions",
        icon: Wallet,
        label: "My Transactions",
    },
    {
        id: "agent-download",
        icon: Download,
        label: "Download Agent",
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
            { id: "user-list", label: "Sub-Agents" },
            { id: "agent-list", label: "Tills" },
            { id: "company-list", label: "Companies" },
        ]
    },
    {
        id: "operations",
        icon: Repeat,
        label: "Operations",
        submenu: [
            { id: "swap-history", label: "Swap History" },
            { id: "clawbacks", label: "Commission Clawbacks" },
        ]
    },
    {
        id: "transactions-list",
        icon: Wallet,
        label: "Transaction List",
    },
    {
        id: "fraud-detection",
        icon: Shield,
        label: "Fraud Detection",
        submenu: [
            { id: "fraud-alerts", label: "Fraud Alerts" },
            { id: "configs", label: "Detection Config" },
        ]
    },
    {
        id: "reports",
        icon: Clock,
        label: "Reports",
        submenu: [
            { id: "report-schedules", label: "Report Schedules" },
        ]
    },
    {
        id: "agent-download",
        icon: Download,
        label: "Download Agent",
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