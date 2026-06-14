import { useState, useEffect, useRef, useMemo } from 'react';
import {
    Search,
    MoreVertical,
    Eye,
    Download,
    RefreshCw,
    Filter,
    Calendar,
    FileText,
    BarChart3,
    Coins,
    TrendingUp,
    TrendingDown,
    DollarSign,
    ChevronRight,
    ChevronDown,
    Building,
    Store,
    ShieldAlert
} from 'lucide-react';
import axios from 'axios';
import config from '../../Config';
import { useToast } from './ToastProvider';
import TransactionDetailsModal from './TransactionDetailsModal.jsx';
import TransactionStatsModal from './TransactionStatsModal.jsx';
import CommissionsReportModal from './CommissionsReportModal.jsx';
import FraudReportModal from './FraudReportModal.jsx';
import AgentPerformanceReportModal from './AgentPerformanceReportModal.jsx';
import MonthlyCommissionReportModal from './MonthlyCommissionReportModal.jsx';

function TransactionsGrid() {
    const [transactionsResponse, setTransactionsResponse] = useState({
        data: [],
        pagination: { page: 1, per_page: 10, total: 0, pages: 0, has_next: false, has_prev: false },
        summary: {},
        filters_applied: {}
    });
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedTransactionIds, setSelectedTransactionIds] = useState([]);
    const [isTransactionModalOpen, setIsTransactionModalOpen] = useState(false);
    const [isCommissionsReportOpen, setIsCommissionsReportOpen] = useState(false);
    const [isFraudReportOpen, setIsFraudReportOpen] = useState(false);
    const [isAgentPerformanceReportOpen, setIsAgentPerformanceReportOpen] = useState(false);
    const [isMonthlyCommissionOpen, setIsMonthlyCommissionOpen] = useState(false);
    const [isStatsModalOpen, setIsStatsModalOpen] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [currentPage, setCurrentPage] = useState(1);
    const [pageSize, setPageSize] = useState(10);
    const [isDropdownOpen, setIsDropdownOpen] = useState(false);
    const [stats, setStats] = useState(null);
    const [filters, setFilters] = useState({
        startDate: '',
        endDate: '',
        reasonType: '',
        transactionStatus: ''
    });

    // Grouping states
    const [expandedCompanies, setExpandedCompanies] = useState(new Set());
    const [expandedBusinesses, setExpandedBusinesses] = useState(new Set());

    // Commission till balances (latest per till, for commission view)
    const [tillBalances, setTillBalances] = useState([]);
    const [isTillBalancesLoading, setIsTillBalancesLoading] = useState(false);
    const [tillPage, setTillPage] = useState(1);
    const [tillPageSize, setTillPageSize] = useState(10);
    const [tillPagination, setTillPagination] = useState({ total: 0, pages: 1, has_next: false, has_prev: false });
    const [tillUpdatedAfter, setTillUpdatedAfter] = useState('');
    const [tillSortDir, setTillSortDir] = useState('desc');

    // Transaction type toggle: 'float' | 'commission'
    const [transactionType, setTransactionType] = useState('float');

    const { showToast } = useToast();
    const dropdownRef = useRef(null);

    // Extract data from response
    const transactions = transactionsResponse.data || [];
    const pagination = transactionsResponse.pagination || {};
    const summary = transactionsResponse.summary || {};
    const filters_applied = transactionsResponse.filters_applied || {};

    const sortedTillBalances = useMemo(() => {
        if (!tillBalances.length) return tillBalances;
        return [...tillBalances].sort((a, b) => {
            const ta = a.last_updated ? new Date(a.last_updated).getTime() : 0;
            const tb = b.last_updated ? new Date(b.last_updated).getTime() : 0;
            return tillSortDir === 'asc' ? ta - tb : tb - ta;
        });
    }, [tillBalances, tillSortDir]);

    // Group transactions by company and business
    const groupedData = useMemo(() => {
        if (!transactions || transactions.length === 0) return [];

        const grouped = {};
        
        transactions.forEach(transaction => {
            const companyName = transaction.company_name || "Unknown Company";
            const businessName = transaction.business_name || "Unknown Business";
            const shortcode = transaction.business_shortcode || "";
            const businessKey = `${businessName}${shortcode ? ` (${shortcode})` : ''}`;
            
            // Initialize company if not exists
            if (!grouped[companyName]) {
                grouped[companyName] = {
                    company_name: companyName,
                    businesses: {},
                    total_transactions: 0,
                    summary: {
                        total_paid_in: 0,
                        total_withdrawn: 0,
                        total_commission: 0
                    }
                };
            }
            
            // Initialize business if not exists
            if (!grouped[companyName].businesses[businessKey]) {
                grouped[companyName].businesses[businessKey] = {
                    business_name: businessName,
                    shortcode: shortcode,
                    display_name: businessKey,
                    transactions: [],
                    total_transactions: 0,
                    summary: {
                        total_paid_in: 0,
                        total_withdrawn: 0,
                        total_commission: 0
                    }
                };
            }
            
            // Add transaction to business
            grouped[companyName].businesses[businessKey].transactions.push(transaction);
            grouped[companyName].businesses[businessKey].total_transactions++;
            
            // Update business totals
            const paidIn = parseFloat(transaction.paid_in || 0);
            const withdrawn = parseFloat(transaction.withdrawn || 0);
            const commission = parseFloat(transaction.commission_amount || 0);
            
            grouped[companyName].businesses[businessKey].summary.total_paid_in += paidIn;
            grouped[companyName].businesses[businessKey].summary.total_withdrawn += withdrawn;
            grouped[companyName].businesses[businessKey].summary.total_commission += commission;
            
            // Update company totals
            grouped[companyName].total_transactions++;
            grouped[companyName].summary.total_paid_in += paidIn;
            grouped[companyName].summary.total_withdrawn += withdrawn;
            grouped[companyName].summary.total_commission += commission;
        });
        
        // Convert to array format for easier rendering
        const companiesArray = Object.values(grouped).map(company => ({
            ...company,
            businesses: Object.values(company.businesses).map(business => ({
                ...business,
                summary: {
                    total_paid_in: business.summary.total_paid_in.toFixed(2),
                    total_withdrawn: Math.abs(business.summary.total_withdrawn).toFixed(2),
                    total_commission: business.summary.total_commission.toFixed(2)
                }
            })),
            summary: {
                total_paid_in: company.summary.total_paid_in.toFixed(2),
                total_withdrawn: Math.abs(company.summary.total_withdrawn).toFixed(2),
                total_commission: company.summary.total_commission.toFixed(2)
            }
        }));
        
        return companiesArray;
    }, [transactions]);

    // Handle page size change
    const handlePageSizeChange = (e) => {
        const newSize = Number(e.target.value);
        setPageSize(newSize);
        setCurrentPage(1);
        setSelectedTransactionIds([]);

        // If using server-side pagination, fetch with new page size
        if (searchTerm.trim()) {
            // Client-side filtering, no need to fetch
        } else {
            // Server-side pagination, fetch new data
            fetchTransactions();
        }
    };

    // Fetch transactions from API
    const fetchTransactions = async () => {
        setIsLoading(true);
        try {
            const token = localStorage.getItem('token');
            const params = {
                page: currentPage,
                per_page: pageSize,
                transaction_type: transactionType,
                search: searchTerm,
                ...filters
            };

            // Remove empty filters
            Object.keys(params).forEach(key => {
                if (!params[key]) delete params[key];
            });

            const response = await axios.get(`${config.API_URL}/transactions`, {
                headers: { Authorization: `Bearer ${token}` },
                params
            });

            console.log('Fetched transactions response:', response.data);

            if (response.data.success) {
                // Store the entire response object
                setTransactionsResponse({
                    data: response.data.data || [],
                    pagination: response.data.pagination || { page: 1, per_page: 10, total: 0, pages: 0 },
                    summary: response.data.summary || {},
                    filters_applied: response.data.filters_applied || {}
                });
                setSelectedTransactionIds([]);
                showToast(`${getTransactionTypeLabel()} loaded`, 'success');
            } else {
                // Handle unsuccessful response
                setTransactionsResponse({
                    data: [],
                    pagination: { page: 1, per_page: 10, total: 0, pages: 0 },
                    summary: {},
                    filters_applied: {}
                });
                showToast(response.data.error || 'Failed to fetch transactions', 'error');
            }
        } catch (error) {
            console.error('Error fetching transactions:', error.response?.data || error.message);
            showToast('Failed to fetch transactions', 'error');
            setTransactionsResponse({
                data: [],
                pagination: { page: 1, per_page: 10, total: 0, pages: 0 },
                summary: {},
                filters_applied: {}
            });
        } finally {
            setIsLoading(false);
        }
    };

    // Fetch latest commission balance per till
    const fetchTillBalances = async (page = tillPage, perPage = tillPageSize) => {
        setIsTillBalancesLoading(true);
        try {
            const token = localStorage.getItem('token');
            const params = { page, per_page: perPage };
            if (tillUpdatedAfter) params.updated_after = tillUpdatedAfter;
            const response = await axios.get(`${config.API_URL}/transactions/commission-till-balances`, {
                headers: { Authorization: `Bearer ${token}` },
                params
            });
            if (response.data.success) {
                setTillBalances(response.data.data || []);
                setTillPagination(response.data.pagination || { total: 0, pages: 1, has_next: false, has_prev: false });
            } else {
                showToast(response.data.error || 'Failed to load till balances', 'error');
            }
        } catch (error) {
            console.error('Error fetching till balances:', error.response?.data || error.message);
            showToast('Failed to fetch commission till balances', 'error');
        } finally {
            setIsTillBalancesLoading(false);
        }
    };

    // Fetch statistics
    const fetchStats = async () => {
        try {
            const token = localStorage.getItem('token');
            const params = {
                transaction_type: transactionType,
                ...filters
            };

            // Remove empty filters
            Object.keys(params).forEach(key => {
                if (!params[key]) delete params[key];
            });

            const response = await axios.get(`${config.API_URL}/transactions/stats`, {
                headers: { Authorization: `Bearer ${token}` },
                params
            });

            if (response.data.success) {
                setStats(response.data.stats);
            }
        } catch (error) {
            console.error('Error fetching stats:', error.response?.data || error.message);
        }
    };

    useEffect(() => {
        if (transactionType === 'commission') {
            fetchTillBalances(tillPage, tillPageSize);
        } else {
            fetchTransactions();
            fetchStats();
        }
    }, [currentPage, pageSize, filters, transactionType, tillPage, tillPageSize, tillUpdatedAfter]);

    useEffect(() => {
        if (searchTerm !== '') {
            setCurrentPage(1);
            // Optional: debounce the search
            const timer = setTimeout(() => {
                fetchTransactions();
            }, 500); // 500ms debounce

            return () => clearTimeout(timer);
        }
    }, [searchTerm]);

    // Close dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setIsDropdownOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    // Group toggle functions
    const toggleCompany = (companyName) => {
        const newExpanded = new Set(expandedCompanies);
        if (newExpanded.has(companyName)) {
            newExpanded.delete(companyName);
            // Also collapse all businesses in this company
            const newBusinessExpanded = new Set(expandedBusinesses);
            groupedData
                .find(c => c.company_name === companyName)
                ?.businesses.forEach(b => {
                    newBusinessExpanded.delete(b.display_name);
                });
            setExpandedBusinesses(newBusinessExpanded);
        } else {
            newExpanded.add(companyName);
        }
        setExpandedCompanies(newExpanded);
    };

    const toggleBusiness = (businessKey) => {
        const newExpanded = new Set(expandedBusinesses);
        if (newExpanded.has(businessKey)) {
            newExpanded.delete(businessKey);
        } else {
            newExpanded.add(businessKey);
        }
        setExpandedBusinesses(newExpanded);
    };

    const toggleExpandAll = () => {
        if (expandedCompanies.size === groupedData.length) {
            // Collapse all
            setExpandedCompanies(new Set());
            setExpandedBusinesses(new Set());
        } else {
            // Expand all
            const allCompanies = new Set(groupedData.map(c => c.company_name));
            const allBusinesses = new Set();
            groupedData.forEach(c => {
                c.businesses.forEach(b => allBusinesses.add(b.display_name));
            });
            setExpandedCompanies(allCompanies);
            setExpandedBusinesses(allBusinesses);
        }
    };

    // Handle checkbox selection
    const handleSelectTransaction = (transactionId) => {
        setSelectedTransactionIds((prev) =>
            prev.includes(transactionId)
                ? prev.filter((id) => id !== transactionId)
                : [...prev, transactionId]
        );
    };

    // Handle select all checkboxes for visible transactions
    const handleSelectAll = () => {
        // Get all visible transaction IDs
        const allVisibleTransactionIds = [];
        groupedData.forEach(company => {
            company.businesses.forEach(business => {
                if (expandedCompanies.has(company.company_name) && 
                    expandedBusinesses.has(business.display_name)) {
                    business.transactions.forEach(t => {
                        allVisibleTransactionIds.push(t.id);
                    });
                }
            });
        });

        if (selectedTransactionIds.length === allVisibleTransactionIds.length) {
            setSelectedTransactionIds([]);
        } else {
            setSelectedTransactionIds(allVisibleTransactionIds);
        }
    };

    // Handle view transaction details
    const handleViewDetails = () => {
        if (selectedTransactionIds.length === 0) {
            showToast('Please select a transaction to view', 'error');
            return;
        }
        if (selectedTransactionIds.length > 1) {
            showToast('Please select only one transaction to view', 'error');
            return;
        }
        setIsTransactionModalOpen(true);
        setIsDropdownOpen(false);
    };

    // Export commission till balances to Excel
    const handleExportCommissionTillsExcel = async () => {
        setIsDropdownOpen(false);
        try {
            const token = localStorage.getItem('token');
            const params = {};
            if (tillUpdatedAfter) params.updated_after = tillUpdatedAfter;

            const response = await axios.get(`${config.API_URL}/transactions/export-commission-tills`, {
                headers: { Authorization: `Bearer ${token}` },
                params,
                responseType: 'blob',
            });

            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `commission_till_balances_${new Date().toISOString().slice(0, 10)}.xlsx`);
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);
            showToast('Commission balances exported to Excel', 'success');
        } catch (error) {
            console.error('Error exporting commission tills:', error.response?.data || error.message);
            showToast('Failed to export commission tills', 'error');
        }
    };

    // Handle export transactions
    const handleExportTransactions = async () => {
        try {
            const token = localStorage.getItem('token');
            const params = {
                transaction_type: transactionType,
                ...filters
            };

            // Remove empty filters
            Object.keys(params).forEach(key => {
                if (!params[key]) delete params[key];
            });

            const response = await axios.get(`${config.API_URL}/transactions/export`, {
                headers: { Authorization: `Bearer ${token}` },
                params,
                responseType: 'blob'
            });

            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `${transactionType}_transactions_export.csv`);
            document.body.appendChild(link);
            link.click();
            link.remove();

            showToast(`${getTransactionTypeLabel()} exported successfully`, 'success');
        } catch (error) {
            console.error('Error exporting transactions:', error.response?.data || error.message);
            showToast('Failed to export transactions', 'error');
        }
    };

    // Handle filter change
    const handleFilterChange = (field, value) => {
        setFilters(prev => ({ ...prev, [field]: value }));
        setCurrentPage(1);
        setSelectedTransactionIds([]);
        setExpandedCompanies(new Set());
        setExpandedBusinesses(new Set());
    };

    // Handle reset filters
    const handleResetFilters = () => {
        setFilters({
            startDate: '',
            endDate: '',
            reasonType: '',
            transactionStatus: ''
        });
        setSearchTerm('');
        setCurrentPage(1);
        setSelectedTransactionIds([]);
        setExpandedCompanies(new Set());
        setExpandedBusinesses(new Set());
        fetchTransactions();
    };

    // Toggle transaction type
    const toggleTransactionType = () => {
        const newType = transactionType === 'float' ? 'commission' : 'float';
        setTransactionType(newType);
        setCurrentPage(1);
        setSelectedTransactionIds([]);
        setFilters({ startDate: '', endDate: '', reasonType: '', transactionStatus: '' });
        setSearchTerm('');
        setExpandedCompanies(new Set());
        setExpandedBusinesses(new Set());
    };

    // Format currency
    const formatCurrency = (amount) => {
        if (!amount) return 'KES 0.00';
        const num = parseFloat(amount);
        return `KES ${num.toLocaleString('en-KE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    };

    // Format date
    const formatDate = (dateString) => {
        if (!dateString) return '';
        const date = new Date(dateString);
        return date.toLocaleString('en-KE', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    // Get transaction type label
    const getTransactionTypeLabel = () => {
        return transactionType === 'float' ? 'Float Transactions' : 'Commission Transactions';
    };

    return (
        <div className="bg-white dark:bg-slate-800 rounded-xl shadow-lg p-6">
            {/* Header with toggle */}
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h1 className="text-2xl font-bold text-slate-800 dark:text-white">
                        {getTransactionTypeLabel()}
                    </h1>
                    <p className="text-slate-600 dark:text-slate-400 mt-1">
                        View and manage {transactionType === 'float' ? 'float' : 'commission'} transactions
                    </p>
                </div>

                <button
                    onClick={toggleTransactionType}
                    className={`flex items-center space-x-2 py-2 px-4 rounded-xl transition-colors ${transactionType === 'float'
                        ? 'bg-blue-500 hover:bg-blue-600 text-white'
                        : 'bg-amber-500 hover:bg-amber-600 text-white'
                        }`}
                >
                    {transactionType === 'float' ? (
                        <>
                            <Coins className="w-4 h-4" />
                            <span>Switch to Commissions</span>
                        </>
                    ) : (
                        <>
                            <DollarSign className="w-4 h-4" />
                            <span>Switch to Float</span>
                        </>
                    )}
                </button>
            </div>

            {/* Stats Summary */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                <div className={`rounded-xl p-4 ${transactionType === 'float' ? 'bg-blue-50 dark:bg-slate-700' : 'bg-amber-50 dark:bg-slate-700'
                    }`}>
                    <div className={`text-sm font-medium ${transactionType === 'float' ? 'text-blue-600 dark:text-blue-400' : 'text-amber-600 dark:text-amber-400'
                        }`}>
                        {transactionType === 'float' ? 'Total Items' : 'Active Tills'}
                    </div>
                    <div className="text-2xl font-bold text-slate-800 dark:text-white">
                        {transactionType === 'float' ? (pagination.total || 0) : (tillPagination.total || tillBalances.length)}
                    </div>
                </div>

                {transactionType === 'float' ? (
                    <>
                        <div className="bg-green-50 dark:bg-slate-700 rounded-xl p-4">
                            <div className="text-sm text-green-600 dark:text-green-400 font-medium">Total Deposits</div>
                            <div className="text-2xl font-bold text-slate-800 dark:text-white">
                                {formatCurrency(summary.total_paid_in || '0.00')}
                            </div>
                        </div>
                        <div className="bg-red-50 dark:bg-slate-700 rounded-xl p-4">
                            <div className="text-sm text-red-600 dark:text-red-400 font-medium">Total Withdrawals</div>
                            <div className="text-2xl font-bold text-slate-800 dark:text-white">
                                {formatCurrency(summary.total_withdrawn || '0.00')}
                            </div>
                        </div>
                        <div className={`rounded-xl p-4 ${parseFloat(summary.net_flow || '0') >= 0
                            ? 'bg-green-50 dark:bg-slate-700'
                            : 'bg-red-50 dark:bg-slate-700'
                            }`}>
                            <div className="flex items-center text-sm font-medium">
                                {parseFloat(summary.net_flow || '0') >= 0 ? (
                                    <TrendingUp className="w-4 h-4 mr-1 text-green-600 dark:text-green-400" />
                                ) : (
                                    <TrendingDown className="w-4 h-4 mr-1 text-red-600 dark:text-red-400" />
                                )}
                                <span className={
                                    parseFloat(summary.net_flow || '0') >= 0
                                        ? 'text-green-600 dark:text-green-400'
                                        : 'text-red-600 dark:text-red-400'
                                }>
                                    Net Flow
                                </span>
                            </div>
                            <div className="text-2xl font-bold text-slate-800 dark:text-white">
                                {formatCurrency(summary.net_flow || '0.00')}
                            </div>
                        </div>
                    </>
                ) : (
                    <>
                        <div className="bg-green-50 dark:bg-slate-700 rounded-xl p-4">
                            <div className="text-sm text-green-600 dark:text-green-400 font-medium">Total Available Balance</div>
                            <div className="text-2xl font-bold text-slate-800 dark:text-white">
                                {formatCurrency(
                                    tillBalances.reduce((sum, t) => sum + parseFloat(t.available_balance || 0), 0).toFixed(2)
                                )}
                            </div>
                        </div>
                        <div className="bg-blue-50 dark:bg-slate-700 rounded-xl p-4">
                            <div className="text-sm text-blue-600 dark:text-blue-400 font-medium">Total Current Balance</div>
                            <div className="text-2xl font-bold text-slate-800 dark:text-white">
                                {formatCurrency(
                                    tillBalances.reduce((sum, t) => sum + parseFloat(t.current_balance || 0), 0).toFixed(2)
                                )}
                            </div>
                        </div>
                        <div className="bg-amber-50 dark:bg-slate-700 rounded-xl p-4">
                            <div className="text-sm text-amber-600 dark:text-amber-400 font-medium">Highest Balance Till</div>
                            <div className="text-lg font-bold text-slate-800 dark:text-white truncate">
                                {tillBalances.length > 0
                                    ? (() => {
                                        const top = tillBalances.reduce((max, t) =>
                                            parseFloat(t.available_balance) > parseFloat(max.available_balance) ? t : max
                                        , tillBalances[0]);
                                        return `${top.shortcode} — ${formatCurrency(top.available_balance)}`;
                                    })()
                                    : '—'
                                }
                            </div>
                        </div>
                    </>
                )}
            </div>

            <div className="sticky top-0 z-20 bg-white dark:bg-slate-800">
            {/* Action Buttons */}
            <div className="flex justify-between mb-4">
                {/* Filter Buttons */}
                <div className="flex space-x-2">
                    <button
                        onClick={() => setIsStatsModalOpen(true)}
                        className="flex items-center space-x-2 py-2 px-4 bg-purple-500 text-white rounded-xl hover:bg-purple-600 transition-colors"
                    >
                        <BarChart3 className="w-4 h-4" />
                        <span>Statistics</span>
                    </button>
                    {transactionType === 'float' && groupedData.length > 0 && (
                        <button
                            onClick={toggleExpandAll}
                            className="flex items-center space-x-2 py-2 px-4 bg-slate-500 text-white rounded-xl hover:bg-slate-600 transition-colors"
                        >
                            {expandedCompanies.size === groupedData.length ? (
                                <>
                                    <ChevronDown className="w-4 h-4" />
                                    <span>Collapse All</span>
                                </>
                            ) : (
                                <>
                                    <ChevronRight className="w-4 h-4" />
                                    <span>Expand All</span>
                                </>
                            )}
                        </button>
                    )}
                </div>

                {/* Action Buttons */}
                <div className="flex space-x-4">
                    <button
                        onClick={() => transactionType === 'commission' ? fetchTillBalances() : fetchTransactions()}
                        disabled={isLoading || isTillBalancesLoading}
                        className="flex items-center space-x-2 py-2 px-4 bg-green-500 text-white rounded-xl hover:bg-green-600 transition-colors disabled:bg-green-300 disabled:cursor-not-allowed"
                    >
                        <RefreshCw className={`w-4 h-4 ${(isLoading || isTillBalancesLoading) ? 'animate-spin' : ''}`} />
                        <span>Reload</span>
                    </button>
                    <div className="relative" ref={dropdownRef}>
                        <button
                            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                            className={`flex items-center space-x-2 py-2 px-4 rounded-xl transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 dark:focus:ring-offset-slate-800 ${transactionType === 'float'
                                ? 'bg-blue-500 hover:bg-blue-600 text-white focus:ring-blue-500'
                                : 'bg-amber-500 hover:bg-amber-600 text-white focus:ring-amber-500'
                                }`}
                            aria-haspopup="true"
                            aria-expanded={isDropdownOpen}
                        >
                            <MoreVertical className="w-4 h-4" />
                            <span>Actions</span>
                        </button>
                        {isDropdownOpen && (
                            <div
                                className="absolute right-0 mt-2 w-56 bg-white dark:bg-slate-700 rounded-xl shadow-lg z-10 border border-slate-200 dark:border-slate-600"
                                role="menu"
                            >
                                <div className="py-2">
                                    <button
                                        onClick={handleViewDetails}
                                        disabled={selectedTransactionIds.length !== 1}
                                        className="w-full flex items-center px-4 py-2 text-sm text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                        role="menuitem"
                                    >
                                        <Eye className="w-4 h-4 mr-3" />
                                        View Details
                                    </button>
                                    <button
                                        onClick={handleExportTransactions}
                                        className="w-full flex items-center px-4 py-2 text-sm text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-600 transition-colors"
                                        role="menuitem"
                                    >
                                        <Download className="w-4 h-4 mr-3" />
                                        Export to CSV
                                    </button>
                                    {transactionType === 'commission' && (
                                        <button
                                            onClick={handleExportCommissionTillsExcel}
                                            className="w-full flex items-center px-4 py-2 text-sm text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-600 transition-colors"
                                            role="menuitem"
                                        >
                                            <FileText className="w-4 h-4 mr-3 text-green-600" />
                                            Export Tills to Excel
                                        </button>
                                    )}
                                    <button
                                        onClick={() => setIsCommissionsReportOpen(true)}
                                        disabled={transactionType === 'float' ? true : false}
                                        className="w-full flex items-center px-4 py-2 text-sm text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-600 transition-colors"
                                        role="menuitem"
                                    >
                                        <DollarSign className="w-4 h-4 mr-3" />
                                        Commissions Report
                                    </button>
                                    <button
                                        onClick={() => { setIsFraudReportOpen(true); setIsDropdownOpen(false); }}
                                        disabled={transactionType !== 'commission'}
                                        className="w-full flex items-center px-4 py-2 text-sm text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                        role="menuitem"
                                    >
                                        <ShieldAlert className="w-4 h-4 mr-3 text-red-500" />
                                        Fraud Report
                                    </button>
                                    <button
                                        onClick={() => { setIsAgentPerformanceReportOpen(true); setIsDropdownOpen(false); }}
                                        disabled={transactionType !== 'commission'}
                                        className="w-full flex items-center px-4 py-2 text-sm text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                        role="menuitem"
                                    >
                                        <TrendingUp className="w-4 h-4 mr-3 text-emerald-500" />
                                        Agent Performance Report
                                    </button>
                                    <button
                                        onClick={() => { setIsMonthlyCommissionOpen(true); setIsDropdownOpen(false); }}
                                        disabled={transactionType !== 'commission'}
                                        className="w-full flex items-center px-4 py-2 text-sm text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                        role="menuitem"
                                    >
                                        <BarChart3 className="w-4 h-4 mr-3 text-purple-500" />
                                        Monthly Commission Rollup
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Filters — float only */}
            {transactionType === 'float' && <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                        Start Date
                    </label>
                    <input
                        type="date"
                        value={filters.startDate}
                        onChange={(e) => handleFilterChange('startDate', e.target.value)}
                        className="w-full px-3 py-2 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                </div>
                <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                        End Date
                    </label>
                    <input
                        type="date"
                        value={filters.endDate}
                        onChange={(e) => handleFilterChange('endDate', e.target.value)}
                        className="w-full px-3 py-2 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                </div>
                <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                        {transactionType === 'float' ? 'Transaction Category' : 'Commission Category'}
                    </label>
                    <select
                        value={filters.reasonType}
                        onChange={(e) => handleFilterChange('reasonType', e.target.value)}
                        className="w-full px-3 py-2 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                        <option value="">All Types</option>
                        {transactionType === 'float' ? (
                            <>
                                <option value="Deposit at Agent Till">Deposits</option>
                                <option value="Customer Withdrawal at Agent Till">Withdrawals</option>
                                <option value="Customer Withdrawal at Agent Till with OD">Withdrawal with OD</option>
                            </>
                        ) : (
                            <>
                                <option value="Deposit at Agent Till">Deposit Commissions</option>
                                <option value="Customer Withdrawal at Agent Till">Withdrawal Commissions</option>
                            </>
                        )}
                    </select>
                </div>
                <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                        Status
                    </label>
                    <select
                        value={filters.transactionStatus}
                        onChange={(e) => handleFilterChange('transactionStatus', e.target.value)}
                        className="w-full px-3 py-2 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                        <option value="">All Status</option>
                        <option value="Completed">Completed</option>
                        <option value="Pending">Pending</option>
                        <option value="Failed">Failed</option>
                    </select>
                </div>
            </div>}

            {/* Search and Filter Controls — float only */}
            {transactionType === 'float' &&
            <div className="flex flex-col md:flex-row justify-between items-center mb-6 space-y-4 md:space-y-0">
                <div className="relative w-full md:w-auto">
                    <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
                    <input
                        type="text"
                        placeholder={
                            transactionType === 'float'
                                ? "Search receipts, details, account numbers..."
                                : "Search commission receipts, original receipts..."
                        }
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full md:w-96 pl-10 pr-4 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                    />
                </div>
                <div className="flex space-x-2">
                    <button
                        onClick={handleResetFilters}
                        className="flex items-center space-x-2 py-2 px-4 bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-xl hover:bg-slate-300 dark:hover:bg-slate-600 transition-colors"
                    >
                        <Filter className="w-4 h-4" />
                        <span>Reset Filters</span>
                    </button>
                </div>
            </div>}
            </div>

            {/* Commission Till Balances (one row per till, latest balance) */}
            {transactionType === 'commission' && (
                <div>
                <div className="flex items-center gap-3 mb-4">
                    <Calendar className="w-4 h-4 text-amber-500 shrink-0" />
                    <label className="text-sm font-medium text-slate-600 dark:text-slate-300 shrink-0">Updated after</label>
                    <input
                        type="date"
                        value={tillUpdatedAfter}
                        onChange={e => { setTillUpdatedAfter(e.target.value); setTillPage(1); }}
                        className="py-1.5 px-3 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg text-sm text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-amber-500"
                    />
                    {tillUpdatedAfter && (
                        <button
                            onClick={() => { setTillUpdatedAfter(''); setTillPage(1); }}
                            className="text-xs text-slate-500 dark:text-slate-400 hover:text-red-500 transition-colors"
                        >
                            Clear
                        </button>
                    )}
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="bg-slate-100 dark:bg-slate-700 text-left text-slate-600 dark:text-slate-300">
                                <th className="px-4 py-3 font-semibold rounded-l-xl">Till Name</th>
                                <th className="px-4 py-3 font-semibold">Shortcode</th>
                                <th className="px-4 py-3 font-semibold">Current Balance</th>
                                <th className="px-4 py-3 font-semibold">Available Balance</th>
                                <th className="px-4 py-3 font-semibold rounded-r-xl">
                                    <button
                                        onClick={() => setTillSortDir(d => d === 'asc' ? 'desc' : 'asc')}
                                        className="flex items-center gap-1 hover:text-amber-600 dark:hover:text-amber-400 transition-colors"
                                    >
                                        Last Updated
                                        <span className="flex flex-col leading-none">
                                            <span className={`text-[10px] ${tillSortDir === 'asc' ? 'text-amber-500' : 'text-slate-400'}`}>▲</span>
                                            <span className={`text-[10px] ${tillSortDir === 'desc' ? 'text-amber-500' : 'text-slate-400'}`}>▼</span>
                                        </span>
                                    </button>
                                </th>
                            </tr>
                        </thead>
                        <tbody>
                            {isTillBalancesLoading ? (
                                <tr>
                                    <td colSpan={5} className="text-center py-8">
                                        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-amber-600"></div>
                                        <div className="mt-2 text-slate-500 dark:text-slate-400">Loading commission balances...</div>
                                    </td>
                                </tr>
                            ) : tillBalances.length === 0 ? (
                                <tr>
                                    <td colSpan={5} className="text-center py-8 text-slate-500 dark:text-slate-400">
                                        No commission till balances found
                                    </td>
                                </tr>
                            ) : (
                                sortedTillBalances.map((till, index) => (
                                    <tr
                                        key={till.id}
                                        className={`border-b border-slate-200 dark:border-slate-600 ${
                                            index % 2 === 0 ? 'bg-white dark:bg-slate-800' : 'bg-slate-50 dark:bg-slate-700/50'
                                        } hover:bg-amber-50 dark:hover:bg-slate-700 transition-colors`}
                                    >
                                        <td className="px-4 py-3 font-medium text-slate-800 dark:text-white">
                                            {till.till_name}
                                        </td>
                                        <td className="px-4 py-3 font-mono text-amber-600 dark:text-amber-400">
                                            {till.shortcode}
                                        </td>
                                        <td className="px-4 py-3 font-bold text-slate-800 dark:text-white">
                                            {formatCurrency(till.current_balance)}
                                        </td>
                                        <td className="px-4 py-3 font-bold text-green-600 dark:text-green-400">
                                            {formatCurrency(till.available_balance)}
                                        </td>
                                        <td className="px-4 py-3 text-slate-500 dark:text-slate-400 text-xs">
                                            {formatDate(till.last_updated)}
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
                </div>
            )}

            {/* Float Grouped Transactions Grid */}
            {transactionType === 'float' && <div className="space-y-3">
                {groupedData.map(company => (
                    <div key={company.company_name} className="bg-slate-50 dark:bg-slate-800/50 rounded-lg overflow-hidden border border-slate-200 dark:border-slate-700">
                        {/* Company Header */}
                        <button
                            onClick={() => toggleCompany(company.company_name)}
                            className="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors border-b border-slate-200 dark:border-slate-700"
                        >
                            <div className="flex items-center">
                                {expandedCompanies.has(company.company_name) ? (
                                    <ChevronDown className="w-4 h-4 mr-3 text-slate-500" />
                                ) : (
                                    <ChevronRight className="w-4 h-4 mr-3 text-slate-500" />
                                )}
                                <Building className="w-4 h-4 mr-2 text-blue-500" />
                                <span className="font-bold text-slate-800 dark:text-white">{company.company_name}</span>
                                <span className="ml-3 text-sm bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-300 px-2 py-1 rounded-full">
                                    {company.total_transactions} transactions
                                </span>
                            </div>
                            <div className="text-sm">
                                {transactionType === 'float' ? (
                                    <>
                                        <span className="text-green-600 dark:text-green-400 mr-3">
                                            +{formatCurrency(company.summary.total_paid_in)}
                                        </span>
                                        <span className="text-red-600 dark:text-red-400">
                                            -{formatCurrency(company.summary.total_withdrawn)}
                                        </span>
                                    </>
                                ) : (
                                    <span className="text-amber-600 dark:text-amber-400">
                                        {formatCurrency(company.summary.total_commission)}
                                    </span>
                                )}
                            </div>
                        </button>
                        
                        {/* Businesses within Company */}
                        {expandedCompanies.has(company.company_name) && (
                            <div className="px-4 py-2 bg-white dark:bg-slate-900">
                                {company.businesses.map(business => (
                                    <div key={business.display_name} className="mb-2 last:mb-0">
                                        {/* Business Header */}
                                        <button
                                            onClick={() => toggleBusiness(business.display_name)}
                                            className="w-full px-3 py-2 flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-800 rounded transition-colors"
                                        >
                                            <div className="flex items-center">
                                                {expandedBusinesses.has(business.display_name) ? (
                                                    <ChevronDown className="w-4 h-4 mr-2 text-slate-500" />
                                                ) : (
                                                    <ChevronRight className="w-4 h-4 mr-2 text-slate-500" />
                                                )}
                                                <Store className="w-4 h-4 mr-2 text-green-500" />
                                                <span className="font-semibold text-slate-700 dark:text-slate-300">{business.display_name}</span>
                                                <span className="ml-2 text-xs bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-300 px-2 py-0.5 rounded-full">
                                                    {business.total_transactions} transactions
                                                </span>
                                            </div>
                                            <div className="text-xs">
                                                {transactionType === 'float' ? (
                                                    <>
                                                        <span className="text-green-600 dark:text-green-400 mr-2">
                                                            +{formatCurrency(business.summary.total_paid_in)}
                                                        </span>
                                                        <span className="text-red-600 dark:text-red-400">
                                                            -{formatCurrency(business.summary.total_withdrawn)}
                                                        </span>
                                                    </>
                                                ) : (
                                                    <span className="text-amber-600 dark:text-amber-400">
                                                        {formatCurrency(business.summary.total_commission)}
                                                    </span>
                                                )}
                                            </div>
                                        </button>
                                        
                                        {/* Transactions within Business */}
                                        {expandedBusinesses.has(business.display_name) && (
                                            <div className="mt-2 overflow-x-auto">
                                                <table className="w-full text-sm">
                                                    <thead>
                                                        <tr className="bg-slate-100 dark:bg-slate-800 text-left text-slate-600 dark:text-slate-300">
                                                            <th className="px-3 py-2 font-semibold rounded-l-xl">
                                                                <input
                                                                    type="checkbox"
                                                                    checked={
                                                                        business.transactions.length > 0 &&
                                                                        business.transactions.every(t => selectedTransactionIds.includes(t.id))
                                                                    }
                                                                    onChange={() => {
                                                                        const businessTransactionIds = business.transactions.map(t => t.id);
                                                                        const allSelected = businessTransactionIds.every(id => 
                                                                            selectedTransactionIds.includes(id)
                                                                        );
                                                                        
                                                                        if (allSelected) {
                                                                            // Deselect all in this business
                                                                            setSelectedTransactionIds(prev => 
                                                                                prev.filter(id => !businessTransactionIds.includes(id))
                                                                            );
                                                                        } else {
                                                                            // Select all in this business
                                                                            setSelectedTransactionIds(prev => 
                                                                                [...new Set([...prev, ...businessTransactionIds])]
                                                                            );
                                                                        }
                                                                    }}
                                                                    className={`w-4 h-4 border-slate-300 rounded focus:ring-2 ${transactionType === 'float'
                                                                        ? 'text-blue-600 focus:ring-blue-500'
                                                                        : 'text-amber-600 focus:ring-amber-500'
                                                                        } dark:bg-slate-700 dark:border-slate-600`}
                                                                />
                                                            </th>
                                                            <th className="px-3 py-2 font-semibold">
                                                                {transactionType === 'float' ? 'Receipt No' : 'Commission Receipt No'}
                                                            </th>
                                                            <th className="px-3 py-2 font-semibold">Completion Time</th>
                                                            <th className="px-3 py-2 font-semibold">Details</th>
                                                            <th className="px-3 py-2 font-semibold">
                                                                {transactionType === 'float' ? 'Transaction Type' : 'Commission Type'}
                                                            </th>
                                                            {transactionType === 'float' ? (
                                                                <>
                                                                    <th className="px-3 py-2 font-semibold">Amount</th>
                                                                    <th className="px-3 py-2 font-semibold">Balance</th>
                                                                </>
                                                            ) : (
                                                                <>
                                                                    <th className="px-3 py-2 font-semibold">Commission Amount</th>
                                                                    <th className="px-3 py-2 font-semibold">Balance</th>
                                                                </>
                                                            )}
                                                            <th className="px-3 py-2 font-semibold">Status</th>
                                                            {transactionType === 'float' && (
                                                                <th className="px-3 py-2 font-semibold rounded-r-xl">Other Party</th>
                                                            )}
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        {business.transactions.map((t, index) => (
                                                            <tr
                                                                key={t.id}
                                                                className={`border-b border-slate-200 dark:border-slate-600 ${index % 2 === 0 ? 'bg-white dark:bg-slate-800' : 'bg-slate-50 dark:bg-slate-700/50'
                                                                    } hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors`}
                                                            >
                                                                <td className="px-3 py-2">
                                                                    <input
                                                                        type="checkbox"
                                                                        checked={selectedTransactionIds.includes(t.id)}
                                                                        onChange={() => handleSelectTransaction(t.id)}
                                                                        className={`w-4 h-4 border-slate-300 rounded focus:ring-2 ${transactionType === 'float'
                                                                            ? 'text-blue-600 focus:ring-blue-500'
                                                                            : 'text-amber-600 focus:ring-amber-500'
                                                                            } dark:bg-slate-700 dark:border-slate-600`}
                                                                    />
                                                                </td>
                                                                <td className="px-3 py-2 font-mono text-sm font-medium">
                                                                    <span className={
                                                                        transactionType === 'float'
                                                                            ? 'text-blue-600 dark:text-blue-400'
                                                                            : 'text-amber-600 dark:text-amber-400'
                                                                    }>
                                                                        {t.receipt_no}
                                                                    </span>
                                                                </td>
                                                                <td className="px-3 py-2 text-sm">
                                                                    {formatDate(t.completion_time)}
                                                                </td>
                                                                <td className="px-3 py-2 max-w-xs">
                                                                    <div className="truncate" title={t.details}>
                                                                        {t.details}
                                                                    </div>
                                                                </td>
                                                                <td className="px-3 py-2">
                                                                    <span className={`px-2 py-1 text-xs rounded-full ${t.reason_type?.includes('Deposit')
                                                                        ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                                                                        : t.reason_type?.includes('Withdrawal')
                                                                            ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                                                                            : 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
                                                                        }`}>
                                                                        {transactionType === 'float'
                                                                            ? (t.reason_type ? t.reason_type.split(' ')[0] : '-')
                                                                            : (t.details ? t.details.split(' ')[0] : '-')
                                                                        }
                                                                    </span>
                                                                </td>
                                                                {transactionType === 'float' ? (
                                                                    <>
                                                                        <td className="px-3 py-2 font-medium">
                                                                            {t.paid_in && parseFloat(t.paid_in) > 0 ? (
                                                                                <span className="text-green-600 dark:text-green-400">
                                                                                    +{formatCurrency(t.paid_in)}
                                                                                </span>
                                                                            ) : (
                                                                                <span className="text-red-600 dark:text-red-400">
                                                                                    -{formatCurrency(t.withdrawn)}
                                                                                </span>
                                                                            )}
                                                                        </td>
                                                                        <td className="px-3 py-2 font-bold">
                                                                            {formatCurrency(t.balance)}
                                                                        </td>
                                                                    </>
                                                                ) : (
                                                                    <>
                                                                        <td className="px-3 py-2 font-bold text-amber-600 dark:text-amber-400">
                                                                            {formatCurrency(t.commission_amount || t.paid_in)}
                                                                        </td>
                                                                        <td className="px-3 py-2 font-bold">
                                                                            {formatCurrency(t.balance)}
                                                                        </td>
                                                                    </>
                                                                )}
                                                                <td className="px-3 py-2">
                                                                    <span className={`px-2 py-1 text-xs rounded-full ${t.transaction_status === 'Completed'
                                                                        ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                                                                        : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
                                                                        }`}>
                                                                        {t.transaction_status || 'Unknown'}
                                                                    </span>
                                                                </td>
                                                                {transactionType === 'float' && (
                                                                    <td className="px-3 py-2 max-w-xs">
                                                                        <div className="truncate" title={t.other_party_info}>
                                                                            {t.other_party_info || '-'}
                                                                        </div>
                                                                    </td>
                                                                )}
                                                            </tr>
                                                        ))}
                                                    </tbody>
                                                </table>
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                ))}
                
                {/* Empty State */}
                {groupedData.length === 0 && !isLoading && (
                    <div className="text-center py-8 text-slate-500 dark:text-slate-400">
                        {searchTerm.trim()
                            ? `No ${transactionType === 'float' ? 'float' : 'commission'} transactions found matching "${searchTerm}"`
                            : `No ${transactionType === 'float' ? 'float' : 'commission'} transactions found`
                        }
                    </div>
                )}

                {isLoading && (
                    <div className="text-center py-8">
                        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                        <div className="mt-2 text-slate-500 dark:text-slate-400">
                            Loading float transactions...
                        </div>
                    </div>
                )}
            </div>}

            {/* Commission till pagination — only shown on commission tab */}
            {transactionType === 'commission' && (
                <div className="flex flex-col sm:flex-row justify-between items-center mt-4 space-y-4 sm:space-y-0">
                    <div className="flex items-center space-x-2">
                        <span className="text-sm text-slate-600 dark:text-slate-300">
                            Showing {tillPagination.total === 0 ? 0 : (tillPage - 1) * tillPageSize + 1} - {Math.min(tillPage * tillPageSize, tillPagination.total)} of {tillPagination.total} tills
                        </span>
                        <select
                            value={tillPageSize}
                            onChange={(e) => { setTillPageSize(Number(e.target.value)); setTillPage(1); }}
                            className="py-1 px-2 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-amber-500"
                        >
                            <option value="5">5 per page</option>
                            <option value="10">10 per page</option>
                            <option value="20">20 per page</option>
                            <option value="50">50 per page</option>
                        </select>
                    </div>
                    <div className="flex items-center space-x-2">
                        <button onClick={() => setTillPage(1)} disabled={!tillPagination.has_prev}
                            className="py-1 px-3 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed">
                            First
                        </button>
                        <button onClick={() => setTillPage(p => p - 1)} disabled={!tillPagination.has_prev}
                            className="py-1 px-3 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed">
                            Previous
                        </button>
                        <span className="text-sm text-slate-600 dark:text-slate-300">
                            Page {tillPage} of {tillPagination.pages}
                        </span>
                        <button onClick={() => setTillPage(p => p + 1)} disabled={!tillPagination.has_next}
                            className="py-1 px-3 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed">
                            Next
                        </button>
                        <button onClick={() => setTillPage(tillPagination.pages)} disabled={!tillPagination.has_next}
                            className="py-1 px-3 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed">
                            Last
                        </button>
                    </div>
                </div>
            )}
            {transactionType === 'float' &&
            <div className="flex flex-col sm:flex-row justify-between items-center mt-4 space-y-4 sm:space-y-0">
                <div className="flex items-center space-x-2">
                    <span className="text-sm text-slate-600 dark:text-slate-300">
                        Showing {(currentPage - 1) * pageSize + 1} - {Math.min(currentPage * pageSize, pagination.total)} of {pagination.total} transactions
                    </span>
                    <select
                        value={pageSize}
                        onChange={handlePageSizeChange}
                        className="py-1 px-2 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                        <option value="5">5 per page</option>
                        <option value="10">10 per page</option>
                        <option value="20">20 per page</option>
                        <option value="50">50 per page</option>
                    </select>
                </div>
                <div className="flex items-center space-x-2">
                    <button
                        onClick={() => {
                            setCurrentPage(1);
                            setSelectedTransactionIds([]);
                        }}
                        disabled={currentPage === 1}
                        className="py-1 px-3 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        First
                    </button>
                    <button
                        onClick={() => {
                            setCurrentPage(currentPage - 1);
                            setSelectedTransactionIds([]);
                        }}
                        disabled={currentPage === 1}
                        className="py-1 px-3 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        Previous
                    </button>
                    <span className="text-sm text-slate-600 dark:text-slate-300">
                        Page {currentPage} of {pagination.pages || 1}
                    </span>
                    <button
                        onClick={() => {
                            setCurrentPage(currentPage + 1);
                            setSelectedTransactionIds([]);
                        }}
                        disabled={currentPage === (pagination.pages || 1)}
                        className="py-1 px-3 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        Next
                    </button>
                    <button
                        onClick={() => {
                            setCurrentPage(pagination.pages || 1);
                            setSelectedTransactionIds([]);
                        }}
                        disabled={currentPage === (pagination.pages || 1)}
                        className="py-1 px-3 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        Last
                    </button>
                </div>
            </div>}

            {/* Modals */}
            <TransactionDetailsModal
                isOpen={isTransactionModalOpen}
                onClose={() => {
                    setIsTransactionModalOpen(false);
                    setSelectedTransactionIds([]);
                }}
                transaction={selectedTransactionIds.length === 1
                    ? transactions.find((t) => t.id === selectedTransactionIds[0])
                    : null}
                transactionType={transactionType}
            />

            <TransactionStatsModal
                isOpen={isStatsModalOpen}
                onClose={() => setIsStatsModalOpen(false)}
                stats={stats}
                transactionType={transactionType}
            />

            <CommissionsReportModal
                isOpen={isCommissionsReportOpen}
                onClose={() => setIsCommissionsReportOpen(false)}
                filters={filters}
                transactionType={transactionType}
            />

            <FraudReportModal
                isOpen={isFraudReportOpen}
                onClose={() => setIsFraudReportOpen(false)}
            />

            <AgentPerformanceReportModal
                isOpen={isAgentPerformanceReportOpen}
                onClose={() => setIsAgentPerformanceReportOpen(false)}
            />

            <MonthlyCommissionReportModal
                isOpen={isMonthlyCommissionOpen}
                onClose={() => setIsMonthlyCommissionOpen(false)}
            />
        </div>
    );
}

export default TransactionsGrid;