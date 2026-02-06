import React, { useState, useEffect, useMemo } from 'react';
import {
  Search,
  Filter,
  Eye,
  Download,
  User,
  Building,
  DollarSign,
  Calendar,
  CheckCircle,
  XCircle,
  Clock,
  ChevronDown,
  ChevronUp,
  ChevronRight,
  Users,
  LayoutList,
  LayoutGrid
} from 'lucide-react';
import config from '../../Config';

function TransactionDetailsModal({ isOpen, onClose, transaction }) {
  if (!isOpen || !transaction) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-slate-800 rounded-xl p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <h2 className="text-xl font-bold text-slate-800 dark:text-white mb-4">Transaction Details</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Transaction Information */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-slate-700 dark:text-slate-300 border-b pb-2">
              Transaction Info
            </h3>
            <div className="space-y-3">
              <DetailItem label="Transaction ID" value={transaction.id} />
              <DetailItem label="Confirmation Code" value={transaction.confirmation_code || 'N/A'} />
              <DetailItem label="Merchant Reference" value={transaction.merchant_reference || 'N/A'} />
              <DetailItem label="Amount" value={`${transaction.currency || 'KES'} ${transaction.amount?.toFixed(2) || '0.00'}`} />
              <DetailItem
                label="Status"
                value={
                  <span className={`px-2 py-1 rounded-full text-xs ${
                    transaction.confirmation_code !== null
                      ? 'bg-green-100 text-green-600 dark:bg-green-900/50 dark:text-green-400'
                      : 'bg-red-100 text-red-600 dark:bg-red-900/50 dark:text-red-400'
                  }`}>
                    {transaction.confirmation_code !== null ? 'Success'  : 'Failed'}
                  </span>
                }
              />
            </div>
          </div>

          {/* Customer & Timing Information */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-slate-700 dark:text-slate-300 border-b pb-2">
              Customer & Timing
            </h3>
            <div className="space-y-3">
              <DetailItem label="Customer Email" value={transaction.customer_email || 'N/A'} />
              <DetailItem label="Phone Number" value={transaction.phone_number || 'N/A'} />
              <DetailItem label="User ID" value={transaction.user_id || 'N/A'} />
              <DetailItem
                label="Created At"
                value={transaction.created_at ? new Date(transaction.created_at).toLocaleString() : 'N/A'}
              />
              <DetailItem
                label="Time Paid"
                value={transaction.confirmation_code !== null ? transaction.updated_at ? new Date(transaction.updated_at).toLocaleString() : 'N/A': 'N/A'}
              />
            </div>
          </div>

          {/* User Information (if available) */}
          {transaction.user && (
            <div className="md:col-span-2 space-y-4">
              <h3 className="text-lg font-semibold text-slate-700 dark:text-slate-300 border-b pb-2">
                User Information
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <DetailItem label="Username" value={transaction.user.username || 'N/A'} />
                <DetailItem label="Full Name" value={
                  transaction.user.firstname && transaction.user.lastname
                    ? `${transaction.user.firstname} ${transaction.user.lastname}`
                    : 'N/A'
                } />
                <DetailItem label="Email" value={transaction.user.email || 'N/A'} />
                <DetailItem label="User ID" value={transaction.user.id || 'N/A'} />
              </div>
            </div>
          )}

          {/* Companies Information (if available) */}
          {transaction.user?.companies && transaction.user.companies.length > 0 && (
            <div className="md:col-span-2 space-y-4">
              <h3 className="text-lg font-semibold text-slate-700 dark:text-slate-300 border-b pb-2">
                Associated Companies ({transaction.user.companies.length})
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {transaction.user.companies.map((company) => (
                  <div key={company.id} className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4">
                    <div className="flex items-center space-x-2 mb-2">
                      <Building className="w-4 h-4 text-blue-500" />
                      <h4 className="font-medium text-slate-800 dark:text-slate-200">
                        {company.company_name}
                      </h4>
                    </div>
                    <div className="space-y-1 text-sm">
                      <p><span className="font-medium">Reg No:</span> {company.registration_number}</p>
                      <p><span className="font-medium">Status:</span>
                        <span className={`ml-1 px-1.5 py-0.5 rounded text-xs ${
                          company.compliance_status === 'compliant'
                            ? 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-400'
                            : company.compliance_status === 'pending'
                            ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-400'
                            : 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-400'
                        }`}>
                          {company.compliance_status || 'Unknown'}
                        </span>
                      </p>
                      {company.total_float_balance > 0 && (
                        <p><span className="font-medium">Float Balance:</span> KES {company.total_float_balance?.toLocaleString()}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <button
          onClick={onClose}
          className="mt-6 w-full py-2 px-4 bg-blue-500 text-white rounded-xl hover:bg-blue-600 transition-colors"
        >
          Close
        </button>
      </div>
    </div>
  );
}

function DetailItem({ label, value }) {
  return (
    <div className="flex justify-between items-start">
      <span className="font-medium text-slate-600 dark:text-slate-400 text-sm">{label}:</span>
      <span className="text-slate-800 dark:text-slate-200 text-sm text-right">{value}</span>
    </div>
  );
}

function Transactions() {
  const [transactions, setTransactions] = useState([]);
  const [filteredTransactions, setFilteredTransactions] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [filter, setFilter] = useState('all');
  const [selectedTransaction, setSelectedTransaction] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [sortField, setSortField] = useState('created_at');
  const [sortDirection, setSortDirection] = useState('desc');
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState({ start: '', end: '' });
  const [amountRange, setAmountRange] = useState({ min: '', max: '' });
  const [userRole, setUserRole] = useState('user');
  const [viewMode, setViewMode] = useState('flat'); // 'flat' or 'grouped'
  const [expandedUsers, setExpandedUsers] = useState({});
  const [userFilter, setUserFilter] = useState(''); // admin: filter by specific user

  // Fetch transactions from API
  useEffect(() => {
    const fetchTransactions = async () => {
      try {
        setLoading(true);
        const token = localStorage.getItem('token');
        const role = localStorage.getItem('userRole') || 'user';
        setUserRole(role);

        const url = `${config.API_URL}/payment/get-all-payments`;
        const response = await fetch(url, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });
        if (!response.ok) throw new Error('Failed to fetch data');
        const data = await response.json();

        if (data.user_role) {
          setUserRole(data.user_role);
        }

        setTransactions(data.payments || []);
        setFilteredTransactions(data.payments || []);
      } catch (error) {
        console.error('Error fetching transactions:', error.response?.data || error.message);
      } finally {
        setLoading(false);
      }
    };
    fetchTransactions();
  }, []);

  const isAdmin = userRole === 'admin' || userRole === 'administrator';

  // Handle search, filter, and sorting
  useEffect(() => {
    let filtered = [...transactions];

    // Apply search
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(
        (t) =>
          t.phone_number?.toLowerCase().includes(term) ||
          t.confirmation_code?.toLowerCase().includes(term) ||
          t.customer_email?.toLowerCase().includes(term) ||
          t.reference_code?.toLowerCase().includes(term) ||
          t.user?.username?.toLowerCase().includes(term) ||
          t.user?.email?.toLowerCase().includes(term) ||
          t.user?.firstname?.toLowerCase().includes(term) ||
          t.user?.lastname?.toLowerCase().includes(term) ||
          t.user?.companies?.some(company =>
            company.company_name?.toLowerCase().includes(term) ||
            company.registration_number?.toLowerCase().includes(term)
          )
      );
    }

    // Apply user filter (admin only)
    if (isAdmin && userFilter) {
      const uTerm = userFilter.toLowerCase();
      filtered = filtered.filter(
        (t) =>
          t.user?.username?.toLowerCase().includes(uTerm) ||
          t.user?.email?.toLowerCase().includes(uTerm)
      );
    }

    // Apply status filter
    if (filter === 'success') {
      filtered = filtered.filter((t) => t.confirmation_code !== null);
    } else if (filter === 'failed') {
      filtered = filtered.filter((t) => t.confirmation_code === null);
    } else if (filter === 'recent') {
      filtered = filtered.filter(
        (t) => new Date(t.created_at) >= new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)
      );
    }

    // Apply date range filter
    if (dateRange.start) {
      filtered = filtered.filter(t => new Date(t.created_at) >= new Date(dateRange.start));
    }
    if (dateRange.end) {
      filtered = filtered.filter(t => new Date(t.created_at) <= new Date(dateRange.end + 'T23:59:59'));
    }

    // Apply amount range filter
    if (amountRange.min !== '') {
      filtered = filtered.filter(t => (t.amount || 0) >= Number(amountRange.min));
    }
    if (amountRange.max !== '') {
      filtered = filtered.filter(t => (t.amount || 0) <= Number(amountRange.max));
    }

    // Apply sorting
    filtered.sort((a, b) => {
      let aValue = a[sortField];
      let bValue = b[sortField];

      if (sortField === 'created_at' || sortField === 'time_paid') {
        aValue = new Date(aValue);
        bValue = new Date(bValue);
      }

      if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });

    setFilteredTransactions(filtered);
    setCurrentPage(1);
  }, [searchTerm, filter, transactions, sortField, sortDirection, dateRange, amountRange, userFilter, isAdmin]);

  // Group transactions by user for admin grouped view
  const groupedByUser = useMemo(() => {
    if (!isAdmin || viewMode !== 'grouped') return [];

    const groups = {};
    filteredTransactions.forEach((t) => {
      const userId = t.user?.id || t.user_id || 'unknown';
      if (!groups[userId]) {
        groups[userId] = {
          user: t.user || { id: userId, username: 'Unknown', email: 'N/A' },
          transactions: [],
          totalAmount: 0,
          successCount: 0,
          failedCount: 0,
        };
      }
      groups[userId].transactions.push(t);
      groups[userId].totalAmount += t.amount || 0;
      if (t.confirmation_code !== null) {
        groups[userId].successCount++;
      } else {
        groups[userId].failedCount++;
      }
    });

    return Object.values(groups).sort((a, b) => b.totalAmount - a.totalAmount);
  }, [filteredTransactions, isAdmin, viewMode]);

  // Pagination calculations (flat view)
  const totalItems = filteredTransactions.length;
  const totalPages = Math.ceil(totalItems / pageSize);
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  const paginatedTransactions = filteredTransactions.slice(startIndex, endIndex);

  // Stats
  const totalRevenue = useMemo(() => {
    return transactions
      .filter(t => t.confirmation_code !== null)
      .reduce((sum, t) => sum + (t.amount || 0), 0);
  }, [transactions]);

  const uniqueUsers = useMemo(() => {
    const ids = new Set(transactions.map(t => t.user?.id || t.user_id).filter(Boolean));
    return ids.size;
  }, [transactions]);

  const handlePageChange = (page) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page);
    }
  };

  const handlePageSizeChange = (e) => {
    setPageSize(Number(e.target.value));
    setCurrentPage(1);
  };

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const handleViewTransaction = (transaction) => {
    setSelectedTransaction(transaction);
    setIsModalOpen(true);
  };

  const toggleUserExpand = (userId) => {
    setExpandedUsers(prev => ({ ...prev, [userId]: !prev[userId] }));
  };

  const clearAllFilters = () => {
    setSearchTerm('');
    setFilter('all');
    setDateRange({ start: '', end: '' });
    setAmountRange({ min: '', max: '' });
    setUserFilter('');
  };

  const exportToCSV = () => {
    const headers = ['ID', 'User', 'Email', 'Phone', 'Amount', 'Currency', 'Status', 'Confirmation Code', 'Created At', 'Companies'];
    const csvData = filteredTransactions.map(transaction => [
      transaction.id,
      transaction.user ? `${transaction.customer_first_name || ''} ${transaction.customer_last_name || ''}`.trim() || transaction.user.username : 'N/A',
      transaction.customer_email || 'N/A',
      transaction.phone_number || 'N/A',
      transaction.amount,
      transaction.currency || 'KES',
      transaction.confirmation_code !== null ? 'Success' : 'Failed',
      transaction.confirmation_code || 'N/A',
      new Date(transaction.created_at).toLocaleString(),
      transaction.user?.companies?.map(c => c.company_name).join('; ') || 'None'
    ]);

    const csvContent = [
      headers.join(','),
      ...csvData.map(row => row.map(field => `"${field}"`).join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `transactions-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-lg p-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 dark:text-white mb-1">Transaction History</h1>
          <p className="text-slate-600 dark:text-slate-400">
            {isAdmin ? 'All user transactions and payment records' : 'Your payment transactions'}
          </p>
        </div>
        {isAdmin && (
          <div className="flex items-center gap-2 mt-3 sm:mt-0">
            <button
              onClick={() => setViewMode('flat')}
              className={`flex items-center gap-1.5 px-3 py-2 text-sm rounded-lg transition-colors ${
                viewMode === 'flat'
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600'
              }`}
            >
              <LayoutList className="w-4 h-4" />
              Flat
            </button>
            <button
              onClick={() => setViewMode('grouped')}
              className={`flex items-center gap-1.5 px-3 py-2 text-sm rounded-lg transition-colors ${
                viewMode === 'grouped'
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600'
              }`}
            >
              <Users className="w-4 h-4" />
              By User
            </button>
          </div>
        )}
      </div>

      {/* Stats Cards */}
      <div className={`grid grid-cols-1 ${isAdmin ? 'md:grid-cols-4' : 'md:grid-cols-3'} gap-4 mb-6`}>
        <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-600 dark:text-slate-400">Total Transactions</p>
              <p className="text-2xl font-bold text-slate-800 dark:text-white">{transactions.length}</p>
            </div>
            <DollarSign className="w-8 h-8 text-blue-600" />
          </div>
        </div>
        <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-600 dark:text-slate-400">Successful</p>
              <p className="text-2xl font-bold text-green-600">
                {transactions.filter(t => t.confirmation_code !== null).length}
              </p>
            </div>
            <CheckCircle className="w-8 h-8 text-green-600" />
          </div>
        </div>
        <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-600 dark:text-slate-400">Failed</p>
              <p className="text-2xl font-bold text-red-600">
                {transactions.filter(t => t.confirmation_code === null).length}
              </p>
            </div>
            <XCircle className="w-8 h-8 text-red-600" />
          </div>
        </div>
        {isAdmin && (
          <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-slate-600 dark:text-slate-400">Total Revenue</p>
                <p className="text-2xl font-bold text-indigo-600">
                  KES {totalRevenue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </p>
              </div>
              <Users className="w-8 h-8 text-indigo-600" />
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{uniqueUsers} unique users</p>
          </div>
        )}
      </div>

      {/* Search and Filter Controls */}
      <div className="flex flex-col lg:flex-row gap-4 mb-4">
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder={isAdmin
              ? "Search by phone, email, confirmation code, username, company..."
              : "Search by phone, email, confirmation code, company name..."
            }
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
          />
        </div>
        <div className="flex flex-col sm:flex-row gap-3">
          {isAdmin && (
            <div className="relative">
              <Users className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Filter by user..."
                value={userFilter}
                onChange={(e) => setUserFilter(e.target.value)}
                className="pl-10 pr-4 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
              />
            </div>
          )}
          <div className="relative">
            <Filter className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="pl-10 pr-4 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
            >
              <option value="all">All Transactions</option>
              <option value="success">Successful</option>
              <option value="failed">Failed</option>
              <option value="recent">Last 7 Days</option>
            </select>
          </div>
          <button
            onClick={exportToCSV}
            className="flex items-center space-x-2 px-4 py-2.5 bg-green-600 text-white rounded-xl hover:bg-green-700 transition-colors"
          >
            <Download className="w-4 h-4" />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {/* Date Range & Amount Range Filters */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6">
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">From Date</label>
          <input
            type="date"
            value={dateRange.start}
            onChange={(e) => setDateRange(prev => ({ ...prev, start: e.target.value }))}
            className="w-full px-3 py-2 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">To Date</label>
          <input
            type="date"
            value={dateRange.end}
            onChange={(e) => setDateRange(prev => ({ ...prev, end: e.target.value }))}
            className="w-full px-3 py-2 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Min Amount</label>
          <input
            type="number"
            placeholder="0"
            value={amountRange.min}
            onChange={(e) => setAmountRange(prev => ({ ...prev, min: e.target.value }))}
            className="w-full px-3 py-2 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Max Amount</label>
          <input
            type="number"
            placeholder="Any"
            value={amountRange.max}
            onChange={(e) => setAmountRange(prev => ({ ...prev, max: e.target.value }))}
            className="w-full px-3 py-2 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div className="flex items-end">
          <button
            onClick={clearAllFilters}
            className="w-full px-4 py-2 text-slate-600 dark:text-slate-400 border border-slate-300 dark:border-slate-600 rounded-xl hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
          >
            Clear Filters
          </button>
        </div>
      </div>

      {/* Active Filters Summary */}
      {(searchTerm || filter !== 'all' || dateRange.start || dateRange.end || amountRange.min || amountRange.max || userFilter) && (
        <div className="flex flex-wrap items-center gap-2 mb-4">
          <span className="text-xs text-slate-500 dark:text-slate-400">Active filters:</span>
          {searchTerm && (
            <span className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded-full text-xs">
              Search: "{searchTerm}"
              <button onClick={() => setSearchTerm('')} className="hover:text-blue-900 dark:hover:text-blue-200">&times;</button>
            </span>
          )}
          {userFilter && (
            <span className="inline-flex items-center gap-1 px-2 py-1 bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-400 rounded-full text-xs">
              User: "{userFilter}"
              <button onClick={() => setUserFilter('')} className="hover:text-indigo-900 dark:hover:text-indigo-200">&times;</button>
            </span>
          )}
          {filter !== 'all' && (
            <span className="inline-flex items-center gap-1 px-2 py-1 bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 rounded-full text-xs">
              Status: {filter}
              <button onClick={() => setFilter('all')} className="hover:text-amber-900 dark:hover:text-amber-200">&times;</button>
            </span>
          )}
          {(dateRange.start || dateRange.end) && (
            <span className="inline-flex items-center gap-1 px-2 py-1 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400 rounded-full text-xs">
              Date: {dateRange.start || '...'} to {dateRange.end || '...'}
              <button onClick={() => setDateRange({ start: '', end: '' })} className="hover:text-purple-900 dark:hover:text-purple-200">&times;</button>
            </span>
          )}
          {(amountRange.min || amountRange.max) && (
            <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded-full text-xs">
              Amount: {amountRange.min || '0'} - {amountRange.max || '...'}
              <button onClick={() => setAmountRange({ min: '', max: '' })} className="hover:text-green-900 dark:hover:text-green-200">&times;</button>
            </span>
          )}
          <span className="text-xs text-slate-500 dark:text-slate-400 ml-2">
            {filteredTransactions.length} result{filteredTransactions.length !== 1 ? 's' : ''}
          </span>
        </div>
      )}

      {/* GROUPED VIEW (Admin only) */}
      {isAdmin && viewMode === 'grouped' ? (
        <div className="space-y-3">
          {groupedByUser.length === 0 ? (
            <div className="text-center py-12 text-slate-500 dark:text-slate-400">
              <Users className="w-12 h-12 mx-auto mb-3 text-slate-300" />
              <p className="text-lg font-medium text-slate-600 dark:text-slate-300">No transactions found</p>
              <p>No transactions match your current filters</p>
            </div>
          ) : (
            groupedByUser.map((group) => {
              const userId = group.user?.id || 'unknown';
              const isExpanded = expandedUsers[userId];
              return (
                <div key={userId} className="border border-slate-200 dark:border-slate-600 rounded-xl overflow-hidden">
                  {/* User Header Row */}
                  <button
                    onClick={() => toggleUserExpand(userId)}
                    className="w-full flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-700/50 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors text-left"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/50 rounded-full flex items-center justify-center flex-shrink-0">
                        <User className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                      </div>
                      <div>
                        <p className="font-semibold text-slate-800 dark:text-white">
                          {group.user?.username || 'Unknown User'}
                        </p>
                        <p className="text-sm text-slate-500 dark:text-slate-400">
                          {group.user?.email || 'N/A'}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right hidden sm:block">
                        <p className="text-sm font-medium text-slate-800 dark:text-white">
                          KES {group.totalAmount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </p>
                        <p className="text-xs text-slate-500 dark:text-slate-400">
                          {group.transactions.length} transaction{group.transactions.length !== 1 ? 's' : ''}
                        </p>
                      </div>
                      <div className="flex items-center gap-2 hidden sm:flex">
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
                          <CheckCircle className="w-3 h-3" /> {group.successCount}
                        </span>
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">
                          <XCircle className="w-3 h-3" /> {group.failedCount}
                        </span>
                      </div>
                      {isExpanded ? (
                        <ChevronUp className="w-5 h-5 text-slate-400 flex-shrink-0" />
                      ) : (
                        <ChevronDown className="w-5 h-5 text-slate-400 flex-shrink-0" />
                      )}
                    </div>
                  </button>

                  {/* Expanded Transaction Rows */}
                  {isExpanded && (
                    <div className="overflow-x-auto">
                      <table className="w-full table-auto">
                        <thead>
                          <tr className="bg-slate-100 dark:bg-slate-700 text-left text-slate-600 dark:text-slate-300 text-xs">
                            <th className="px-4 py-2 font-semibold">ID</th>
                            <th className="px-4 py-2 font-semibold">Email/Phone</th>
                            <th className="px-4 py-2 font-semibold">Amount</th>
                            <th className="px-4 py-2 font-semibold">Date</th>
                            <th className="px-4 py-2 font-semibold">Companies</th>
                            <th className="px-4 py-2 font-semibold">Status</th>
                            <th className="px-4 py-2 font-semibold">Action</th>
                          </tr>
                        </thead>
                        <tbody>
                          {group.transactions.map((transaction, index) => (
                            <tr
                              key={transaction.id}
                              className={`border-b border-slate-100 dark:border-slate-600/50 ${
                                index % 2 === 0 ? 'bg-white dark:bg-slate-800' : 'bg-slate-50/50 dark:bg-slate-700/30'
                              } hover:bg-blue-50/50 dark:hover:bg-slate-700/50 transition-colors`}
                            >
                              <td className="px-4 py-2.5 text-slate-700 dark:text-slate-300 font-mono text-sm">
                                {transaction.id}
                              </td>
                              <td className="px-4 py-2.5">
                                <p className="text-sm text-slate-700 dark:text-slate-300">{transaction.customer_email || 'N/A'}</p>
                                <p className="text-xs text-slate-500 dark:text-slate-400">{transaction.phone_number || 'N/A'}</p>
                              </td>
                              <td className="px-4 py-2.5 font-medium text-slate-800 dark:text-slate-200 text-sm">
                                {transaction.currency || 'KES'} {transaction.amount?.toFixed(2) || '0.00'}
                              </td>
                              <td className="px-4 py-2.5 text-slate-700 dark:text-slate-300 text-sm">
                                {new Date(transaction.created_at).toLocaleString()}
                              </td>
                              <td className="px-4 py-2.5">
                                <div className="space-y-1 max-w-xs">
                                  {transaction.user?.companies?.length > 0 ? (
                                    transaction.user.companies.slice(0, 2).map((company, ci) => (
                                      <div key={company.id} className="flex items-center space-x-1">
                                        <Building className="w-3 h-3 text-slate-400 flex-shrink-0" />
                                        <span className="text-xs text-slate-600 dark:text-slate-400 truncate">
                                          {company.company_name}
                                        </span>
                                        {ci === 1 && transaction.user.companies.length > 2 && (
                                          <span className="text-xs text-slate-500 bg-slate-100 dark:bg-slate-600 px-1 rounded">
                                            +{transaction.user.companies.length - 2}
                                          </span>
                                        )}
                                      </div>
                                    ))
                                  ) : (
                                    <span className="text-xs text-slate-400">No companies</span>
                                  )}
                                </div>
                              </td>
                              <td className="px-4 py-2.5">
                                <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs ${
                                  transaction.confirmation_code !== null
                                    ? 'bg-green-100 text-green-600 dark:bg-green-900/50 dark:text-green-400'
                                    : 'bg-red-100 text-red-600 dark:bg-red-900/50 dark:text-red-400'
                                }`}>
                                  {transaction.confirmation_code !== null ? (
                                    <><CheckCircle className="w-3 h-3" /> Success</>
                                  ) : (
                                    <><XCircle className="w-3 h-3" /> Failed</>
                                  )}
                                </span>
                              </td>
                              <td className="px-4 py-2.5">
                                <button
                                  onClick={() => handleViewTransaction(transaction)}
                                  className="flex items-center space-x-1 text-blue-500 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                                >
                                  <Eye className="w-4 h-4" />
                                  <span className="text-sm">View</span>
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      ) : (
        /* FLAT VIEW (both admin and user) */
        <>
          <div className="overflow-x-auto">
            <table className="w-full table-auto">
              <thead>
                <tr className="bg-slate-100 dark:bg-slate-700 text-left text-slate-600 dark:text-slate-300">
                  <th
                    className="px-4 py-3 font-semibold cursor-pointer hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
                    onClick={() => handleSort('id')}
                  >
                    <div className="flex items-center space-x-1">
                      <span>ID</span>
                      {sortField === 'id' && (
                        sortDirection === 'asc' ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />
                      )}
                    </div>
                  </th>
                  <th className="px-4 py-3 font-semibold">User</th>
                  <th className="px-4 py-3 font-semibold">Email/Phone</th>
                  <th
                    className="px-4 py-3 font-semibold cursor-pointer hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
                    onClick={() => handleSort('amount')}
                  >
                    <div className="flex items-center space-x-1">
                      <span>Amount</span>
                      {sortField === 'amount' && (
                        sortDirection === 'asc' ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />
                      )}
                    </div>
                  </th>
                  <th
                    className="px-4 py-3 font-semibold cursor-pointer hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
                    onClick={() => handleSort('created_at')}
                  >
                    <div className="flex items-center space-x-1">
                      <span>Created At</span>
                      {sortField === 'created_at' && (
                        sortDirection === 'asc' ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />
                      )}
                    </div>
                  </th>
                  <th className="px-4 py-3 font-semibold">Companies</th>
                  <th className="px-4 py-3 font-semibold">Status</th>
                  <th className="px-4 py-3 font-semibold">Action</th>
                </tr>
              </thead>
              <tbody>
                {paginatedTransactions.map((transaction, index) => (
                  <tr
                    key={transaction.id}
                    className={`border-b border-slate-200 dark:border-slate-600 ${
                      index % 2 === 0 ? 'bg-white dark:bg-slate-800' : 'bg-slate-50 dark:bg-slate-700/50'
                    } hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors`}
                  >
                    <td className="px-4 py-3 text-slate-700 dark:text-slate-300 font-mono text-sm">
                      {transaction.id}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center space-x-2">
                        <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900/50 rounded-full flex items-center justify-center">
                          <User className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                        </div>
                        <div>
                          <p className="text-sm font-medium text-slate-800 dark:text-slate-200">
                            {transaction ?
                              `${transaction.customer_first_name || ''} ${transaction.customer_last_name || ''}`.trim() ||
                              transaction.user?.username || 'Unknown User' :
                              'Unknown User'
                            }
                          </p>
                          <p className="text-xs text-slate-500 dark:text-slate-400">
                            {transaction.user?.username || 'N/A'}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="space-y-1">
                        <p className="text-sm text-slate-700 dark:text-slate-300">
                          {transaction.customer_email || 'N/A'}
                        </p>
                        <p className="text-xs text-slate-500 dark:text-slate-400">
                          {transaction.phone_number || 'N/A'}
                        </p>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="font-medium text-slate-800 dark:text-slate-200">
                        {transaction.currency || 'KES'} {transaction.amount?.toFixed(2) || '0.00'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-700 dark:text-slate-300 text-sm">
                      {new Date(transaction.created_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-3">
                      <div className="space-y-1 max-w-xs">
                        {transaction.user?.companies?.length > 0 ? (
                          transaction.user.companies.slice(0, 2).map((company, companyIndex) => (
                            <div key={company.id} className="flex items-center space-x-1">
                              <Building className="w-3 h-3 text-slate-400 flex-shrink-0" />
                              <span className="text-xs text-slate-600 dark:text-slate-400 truncate">
                                {company.company_name}
                              </span>
                              {companyIndex === 1 && transaction.user.companies.length > 2 && (
                                <span className="text-xs text-slate-500 bg-slate-100 dark:bg-slate-600 px-1 rounded">
                                  +{transaction.user.companies.length - 2}
                                </span>
                              )}
                            </div>
                          ))
                        ) : (
                          <span className="text-xs text-slate-400">No companies</span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs ${
                        transaction.confirmation_code !== null
                          ? 'bg-green-100 text-green-600 dark:bg-green-900/50 dark:text-green-400'
                          : 'bg-red-100 text-red-600 dark:bg-red-900/50 dark:text-red-400'
                      }`}>
                        {transaction.confirmation_code !== null ? (
                          <><CheckCircle className="w-3 h-3" /> Success</>
                        ) : (
                          <><XCircle className="w-3 h-3" /> Failed</>
                        )}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => handleViewTransaction(transaction)}
                        className="flex items-center space-x-1 text-blue-500 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                      >
                        <Eye className="w-4 h-4" />
                        <span className="text-sm">View</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Empty State */}
          {filteredTransactions.length === 0 && (
            <div className="text-center py-12 text-slate-500 dark:text-slate-400">
              <DollarSign className="w-12 h-12 mx-auto mb-3 text-slate-300" />
              <p className="text-lg font-medium text-slate-600 dark:text-slate-300">No transactions found</p>
              <p className="text-slate-500 dark:text-slate-400">No transactions match your current filters</p>
            </div>
          )}

          {/* Pagination Controls */}
          {filteredTransactions.length > 0 && (
            <div className="flex flex-col sm:flex-row justify-between items-center mt-6 space-y-4 sm:space-y-0">
              <div className="flex items-center space-x-2">
                <span className="text-sm text-slate-600 dark:text-slate-300">
                  Showing {startIndex + 1} - {Math.min(endIndex, totalItems)} of {totalItems} transactions
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
                  onClick={() => handlePageChange(1)}
                  disabled={currentPage === 1}
                  className="py-1 px-3 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  First
                </button>
                <button
                  onClick={() => handlePageChange(currentPage - 1)}
                  disabled={currentPage === 1}
                  className="py-1 px-3 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Previous
                </button>
                <span className="text-sm text-slate-600 dark:text-slate-300">
                  Page {currentPage} of {totalPages}
                </span>
                <button
                  onClick={() => handlePageChange(currentPage + 1)}
                  disabled={currentPage === totalPages}
                  className="py-1 px-3 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Next
                </button>
                <button
                  onClick={() => handlePageChange(totalPages)}
                  disabled={currentPage === totalPages}
                  className="py-1 px-3 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Last
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Modal for Transaction Details */}
      <TransactionDetailsModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        transaction={selectedTransaction}
      />
    </div>
  );
}

export default Transactions;
