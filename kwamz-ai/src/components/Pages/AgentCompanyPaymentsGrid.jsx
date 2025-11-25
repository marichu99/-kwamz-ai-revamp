import React, { useState, useEffect } from 'react';
import { ChevronRight, ChevronDown, Building2, User, DollarSign, Calendar, Hash, MapPin, Phone, Mail, CreditCard, Filter, CheckCircle, XCircle, Clock, AlertCircle } from 'lucide-react';
import config from '../../Config';
import { useToast } from './ToastProvider';

function AgentCompanyPaymentsGrid() {
    const [paymentData, setPaymentData] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [expandedAgents, setExpandedAgents] = useState(new Set());
    const [expandedCompanies, setExpandedCompanies] = useState(new Set());
    const [filter, setFilter] = useState('all');
    const { showToast } = useToast();

    useEffect(() => {
        fetchPaymentData();
    }, []);

    const fetchPaymentData = async () => {
        setIsLoading(true);
        try {
            const token = localStorage.getItem('token');
            const response = await fetch(`${config.API_URL}/company/agent-payments`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) throw new Error('Failed to fetch payment data');

            const data = await response.json();
            setPaymentData(data.data || []);
        } catch (error) {
            showToast('Error fetching payment data', 'error');
            console.error('Error fetching payment data:', error);
        } finally {
            setIsLoading(false);
        }
    };

    const toggleAgent = (agentUserId) => {
        setExpandedAgents(prev => {
            const newSet = new Set(prev);
            if (newSet.has(agentUserId)) {
                newSet.delete(agentUserId);
            } else {
                newSet.add(agentUserId);
            }
            return newSet;
        });
    };

    const toggleCompany = (companyId) => {
        setExpandedCompanies(prev => {
            const newSet = new Set(prev);
            if (newSet.has(companyId)) {
                newSet.delete(companyId);
            } else {
                newSet.add(companyId);
            }
            return newSet;
        });
    };

    // Calculate totals
    const calculateTotals = () => {
        let totalAgents = paymentData.length;
        let totalCompanies = 0;
        let totalPayments = 0;
        let totalAmount = 0;
        let completedAmount = 0;
        let pendingAmount = 0;
        let failedAmount = 0;

        paymentData.forEach(agent => {
            totalCompanies += agent.companies.length;
            agent.companies.forEach(company => {
                company.payments.forEach(payment => {
                    totalPayments++;
                    totalAmount += parseFloat(payment.amount);
                    
                    if (payment.payment_status === 'COMPLETED') {
                        completedAmount += parseFloat(payment.amount);
                    } else if (payment.payment_status === 'PENDING') {
                        pendingAmount += parseFloat(payment.amount);
                    } else if (payment.payment_status === 'FAILED') {
                        failedAmount += parseFloat(payment.amount);
                    }
                });
            });
        });

        return { 
            totalAgents, 
            totalCompanies, 
            totalPayments, 
            totalAmount,
            completedAmount,
            pendingAmount,
            failedAmount
        };
    };

    const { 
        totalAgents, 
        totalCompanies, 
        totalPayments, 
        totalAmount,
        completedAmount,
        pendingAmount,
        failedAmount
    } = calculateTotals();

    const formatCurrency = (amount) => {
        return new Intl.NumberFormat('en-KE', {
            style: 'currency',
            currency: 'KES'
        }).format(amount);
    };

    const formatDate = (dateString) => {
        return new Date(dateString).toLocaleDateString('en-KE', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    const getStatusIcon = (status) => {
        switch (status) {
            case 'COMPLETED':
                return <CheckCircle className="w-4 h-4 text-green-500" />;
            case 'PENDING':
                return <Clock className="w-4 h-4 text-yellow-500" />;
            case 'FAILED':
                return <XCircle className="w-4 h-4 text-red-500" />;
            default:
                return <AlertCircle className="w-4 h-4 text-gray-500" />;
        }
    };

    const getStatusColor = (status) => {
        switch (status) {
            case 'COMPLETED':
                return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400';
            case 'PENDING':
                return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400';
            case 'FAILED':
                return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400';
            default:
                return 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400';
        }
    };

    // Filter payments based on status
    const filteredPaymentData = paymentData.map(agent => ({
        ...agent,
        companies: agent.companies.map(company => ({
            ...company,
            payments: company.payments.filter(payment => {
                if (filter === 'all') return true;
                return payment.payment_status === filter.toUpperCase();
            })
        })).filter(company => company.payments.length > 0)
    })).filter(agent => agent.companies.length > 0);

    if (isLoading) {
        return (
            <div className="bg-white dark:bg-slate-800 rounded-xl shadow-lg p-6 flex items-center justify-center min-h-[400px]">
                <div className="text-center">
                    <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                    <p className="text-slate-600 dark:text-slate-400">Loading payment data...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="bg-white dark:bg-slate-800 rounded-xl shadow-lg p-6">
            {/* Header with Totals */}
            <div className="mb-6">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-4">
                    <div>
                        <h2 className="text-2xl font-bold text-slate-800 dark:text-white mb-2">Agent Company Payments</h2>
                        <p className="text-sm text-slate-600 dark:text-slate-400">
                            Tracking Pesapal payments initiated by agents for their companies
                        </p>
                    </div>
                    <div className="flex items-center space-x-2 mt-4 sm:mt-0">
                        <Filter className="w-4 h-4 text-slate-400" />
                        <select
                            value={filter}
                            onChange={(e) => setFilter(e.target.value)}
                            className="px-3 py-2 border border-slate-200 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800 text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                            <option value="all">All Payments</option>
                            <option value="completed">Completed</option>
                            <option value="pending">Pending</option>
                            <option value="failed">Failed</option>
                        </select>
                    </div>
                </div>

                {/* Summary Cards */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                    <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg border border-blue-200 dark:border-blue-800">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm font-medium text-blue-800 dark:text-blue-300">Total Agents</p>
                                <p className="text-2xl font-bold text-blue-900 dark:text-blue-100">{totalAgents}</p>
                            </div>
                            <User className="w-8 h-8 text-blue-600 dark:text-blue-400" />
                        </div>
                    </div>
                    <div className="bg-green-50 dark:bg-green-900/20 p-4 rounded-lg border border-green-200 dark:border-green-800">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm font-medium text-green-800 dark:text-green-300">Total Companies</p>
                                <p className="text-2xl font-bold text-green-900 dark:text-green-100">{totalCompanies}</p>
                            </div>
                            <Building2 className="w-8 h-8 text-green-600 dark:text-green-400" />
                        </div>
                    </div>
                    <div className="bg-purple-50 dark:bg-purple-900/20 p-4 rounded-lg border border-purple-200 dark:border-purple-800">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm font-medium text-purple-800 dark:text-purple-300">Total Payments</p>
                                <p className="text-2xl font-bold text-purple-900 dark:text-purple-100">{totalPayments}</p>
                            </div>
                            <CreditCard className="w-8 h-8 text-purple-600 dark:text-purple-400" />
                        </div>
                    </div>
                    <div className="bg-orange-50 dark:bg-orange-900/20 p-4 rounded-lg border border-orange-200 dark:border-orange-800">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm font-medium text-orange-800 dark:text-orange-300">Total Amount</p>
                                <p className="text-2xl font-bold text-orange-900 dark:text-orange-100">
                                    {formatCurrency(totalAmount)}
                                </p>
                            </div>
                            <DollarSign className="w-8 h-8 text-orange-600 dark:text-orange-400" />
                        </div>
                    </div>
                </div>

                {/* Status Breakdown */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                    <div className="bg-green-50 dark:bg-green-900/20 p-3 rounded-lg border border-green-200 dark:border-green-800">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm font-medium text-green-800 dark:text-green-300">Completed</p>
                                <p className="text-lg font-bold text-green-900 dark:text-green-100">
                                    {formatCurrency(completedAmount)}
                                </p>
                            </div>
                            <CheckCircle className="w-6 h-6 text-green-600 dark:text-green-400" />
                        </div>
                    </div>
                    <div className="bg-yellow-50 dark:bg-yellow-900/20 p-3 rounded-lg border border-yellow-200 dark:border-yellow-800">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm font-medium text-yellow-800 dark:text-yellow-300">Pending</p>
                                <p className="text-lg font-bold text-yellow-900 dark:text-yellow-100">
                                    {formatCurrency(pendingAmount)}
                                </p>
                            </div>
                            <Clock className="w-6 h-6 text-yellow-600 dark:text-yellow-400" />
                        </div>
                    </div>
                    <div className="bg-red-50 dark:bg-red-900/20 p-3 rounded-lg border border-red-200 dark:border-red-800">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm font-medium text-red-800 dark:text-red-300">Failed</p>
                                <p className="text-lg font-bold text-red-900 dark:text-red-100">
                                    {formatCurrency(failedAmount)}
                                </p>
                            </div>
                            <XCircle className="w-6 h-6 text-red-600 dark:text-red-400" />
                        </div>
                    </div>
                </div>
            </div>

            {/* Agents Grid */}
            <div className="space-y-4">
                {filteredPaymentData.map((agent) => (
                    <div key={agent.agent_user_id} className="border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden">
                        {/* Agent Level */}
                        <div
                            className="bg-gradient-to-r from-slate-50 to-gray-50 dark:from-slate-700 dark:to-slate-800 p-4 cursor-pointer hover:from-slate-100 hover:to-gray-100 dark:hover:from-slate-600 dark:hover:to-slate-700 transition-colors"
                            onClick={() => toggleAgent(agent.agent_user_id)}
                        >
                            <div className="flex items-center justify-between">
                                <div className="flex items-center space-x-3 flex-1">
                                    <button className="text-blue-600 dark:text-blue-400">
                                        {expandedAgents.has(agent.agent_user_id) ? (
                                            <ChevronDown className="w-5 h-5" />
                                        ) : (
                                            <ChevronRight className="w-5 h-5" />
                                        )}
                                    </button>
                                    <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center">
                                        <User className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                                    </div>
                                    <div className="flex-1">
                                        <h3 className="font-bold text-slate-800 dark:text-white">
                                            {agent.agent_name || `Agent #${agent.agent_user_id}`}
                                        </h3>
                                        <div className="flex flex-wrap items-center gap-4 text-sm text-slate-600 dark:text-slate-400 mt-1">
                                            {agent.agent_email && (
                                                <span className="flex items-center space-x-1">
                                                    <Mail className="w-4 h-4" />
                                                    <span>{agent.agent_email}</span>
                                                </span>
                                            )}
                                            {agent.agent_phone && (
                                                <span className="flex items-center space-x-1">
                                                    <Phone className="w-4 h-4" />
                                                    <span>{agent.agent_phone}</span>
                                                </span>
                                            )}
                                            <span className="flex items-center space-x-1">
                                                <Building2 className="w-4 h-4" />
                                                <span>{agent.companies.length} Companies</span>
                                            </span>
                                        </div>
                                    </div>
                                </div>
                                <div className="text-right">
                                    <p className="text-lg font-semibold text-slate-800 dark:text-white">
                                        {formatCurrency(agent.total_payments_amount)}
                                    </p>
                                    <p className="text-sm text-slate-600 dark:text-slate-400">
                                        {agent.total_payments_count} Payments
                                    </p>
                                </div>
                            </div>
                        </div>

                        {/* Companies Level */}
                        {expandedAgents.has(agent.agent_user_id) && (
                            <div className="bg-slate-50 dark:bg-slate-900/50">
                                {agent.companies.length === 0 ? (
                                    <div className="p-4 text-center text-slate-500 dark:text-slate-400">
                                        No companies found for this agent
                                    </div>
                                ) : (
                                    agent.companies.map((company) => (
                                        <div key={company.id} className="border-t border-slate-200 dark:border-slate-700">
                                            <div
                                                className="p-4 pl-12 cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                                                onClick={() => toggleCompany(company.id)}
                                            >
                                                <div className="flex items-center justify-between">
                                                    <div className="flex items-center space-x-3 flex-1">
                                                        <button className="text-indigo-600 dark:text-indigo-400">
                                                            {expandedCompanies.has(company.id) ? (
                                                                <ChevronDown className="w-4 h-4" />
                                                            ) : (
                                                                <ChevronRight className="w-4 h-4" />
                                                            )}
                                                        </button>
                                                        <Building2 className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
                                                        <div className="flex-1">
                                                            <h4 className="font-semibold text-slate-800 dark:text-white">
                                                                {company.company_name}
                                                            </h4>
                                                            <div className="flex flex-wrap items-center gap-4 text-sm text-slate-600 dark:text-slate-400 mt-1">
                                                                <span className="flex items-center space-x-1">
                                                                    <Hash className="w-4 h-4" />
                                                                    <span>{company.registration_number}</span>
                                                                </span>
                                                                {company.address && (
                                                                    <span className="flex items-center space-x-1">
                                                                        <MapPin className="w-4 h-4" />
                                                                        <span>{company.address}</span>
                                                                    </span>
                                                                )}
                                                                <span className="flex items-center space-x-1">
                                                                    <DollarSign className="w-4 h-4" />
                                                                    <span>{company.payments.length} Payments</span>
                                                                </span>
                                                            </div>
                                                        </div>
                                                    </div>
                                                    <div className="text-right">
                                                        <p className="text-md font-semibold text-slate-800 dark:text-white">
                                                            {formatCurrency(company.total_payments_amount)}
                                                        </p>
                                                        <p className="text-sm text-slate-600 dark:text-slate-400">
                                                            Total Paid
                                                        </p>
                                                    </div>
                                                </div>
                                            </div>

                                            {/* Payments Level */}
                                            {expandedCompanies.has(company.id) && (
                                                <div className="bg-white dark:bg-slate-800">
                                                    {company.payments.length === 0 ? (
                                                        <div className="p-4 pl-20 text-center text-slate-500 dark:text-slate-400">
                                                            No payments found for this company
                                                        </div>
                                                    ) : (
                                                        <div className="p-4 pl-20">
                                                            <div className="grid gap-3">
                                                                {company.payments.map((payment) => (
                                                                    <div
                                                                        key={payment.id}
                                                                        className="p-4 border border-slate-200 dark:border-slate-700 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors"
                                                                    >
                                                                        <div className="flex items-center justify-between mb-3">
                                                                            <div className="flex items-center space-x-3">
                                                                                {getStatusIcon(payment.payment_status)}
                                                                                <div>
                                                                                    <p className="font-semibold text-slate-800 dark:text-white">
                                                                                        {payment.merchant_reference}
                                                                                    </p>
                                                                                    <p className="text-sm text-slate-600 dark:text-slate-400">
                                                                                        {payment.order_tracking_id && `Tracking: ${payment.order_tracking_id}`}
                                                                                    </p>
                                                                                </div>
                                                                            </div>
                                                                            <div className="text-right">
                                                                                <p className="text-xl font-bold text-slate-800 dark:text-white">
                                                                                    {formatCurrency(payment.amount)}
                                                                                </p>
                                                                                <p className="text-sm text-slate-500 dark:text-slate-400">
                                                                                    {payment.currency}
                                                                                </p>
                                                                            </div>
                                                                        </div>
                                                                        
                                                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                                                                            <div>
                                                                                <p className="text-slate-600 dark:text-slate-400 mb-2">
                                                                                    <strong>Description:</strong> {payment.description || 'N/A'}
                                                                                </p>
                                                                                <p className="text-slate-600 dark:text-slate-400">
                                                                                    <strong>Payment Method:</strong> {payment.payment_method || 'N/A'}
                                                                                </p>
                                                                            </div>
                                                                            <div>
                                                                                <p className="text-slate-600 dark:text-slate-400 mb-2">
                                                                                    <strong>Status:</strong> 
                                                                                    <span className={`ml-2 px-2 py-1 rounded-full text-xs ${getStatusColor(payment.payment_status)}`}>
                                                                                        {payment.payment_status}
                                                                                    </span>
                                                                                </p>
                                                                                <p className="text-slate-600 dark:text-slate-400">
                                                                                    <strong>Date:</strong> {formatDate(payment.created_at)}
                                                                                </p>
                                                                            </div>
                                                                        </div>

                                                                        {payment.confirmation_code && (
                                                                            <div className="mt-3 p-2 bg-blue-50 dark:bg-blue-900/20 rounded">
                                                                                <p className="text-sm text-blue-700 dark:text-blue-300">
                                                                                    <strong>Confirmation:</strong> {payment.confirmation_code}
                                                                                </p>
                                                                            </div>
                                                                        )}

                                                                        {payment.error_message && (
                                                                            <div className="mt-3 p-2 bg-red-50 dark:bg-red-900/20 rounded">
                                                                                <p className="text-sm text-red-700 dark:text-red-300">
                                                                                    <strong>Error:</strong> {payment.error_message}
                                                                                </p>
                                                                            </div>
                                                                        )}
                                                                    </div>
                                                                ))}
                                                            </div>
                                                        </div>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    ))
                                )}
                            </div>
                        )}
                    </div>
                ))}
            </div>

            {filteredPaymentData.length === 0 && (
                <div className="text-center py-12 text-slate-500 dark:text-slate-400">
                    <CreditCard className="w-16 h-16 mx-auto mb-4 text-slate-300" />
                    <h3 className="text-lg font-medium mb-2">No Payment Data Found</h3>
                    <p>No payments match the current filter criteria.</p>
                </div>
            )}
        </div>
    );
}

export default AgentCompanyPaymentsGrid;