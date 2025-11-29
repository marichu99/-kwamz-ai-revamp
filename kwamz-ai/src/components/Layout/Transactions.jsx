import React, { useState, useEffect } from 'react';
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
  ChevronUp
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

  // Fetch transactions from API
  useEffect(() => {
    const fetchTransactions = async () => {
      try {
        setLoading(true);
        const token = localStorage.getItem('token');
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

        console.log('Fetched transactions:', data);
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

  // Handle search, filter, and sorting
  useEffect(() => {
    let filtered = [...transactions];

    // Apply search
    if (searchTerm) {
      filtered = filtered.filter(
        (t) =>
          t.phone_number?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          t.confirmation_code?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          t.customer_email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          t.reference_code?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          t.user?.username?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          t.user?.firstname?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          t.user?.lastname?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          t.user?.companies?.some(company => 
            company.company_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
            company.registration_number?.toLowerCase().includes(searchTerm.toLowerCase())
          )
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
  }, [searchTerm, filter, transactions, sortField, sortDirection, dateRange]);

  // Pagination calculations
  const totalItems = filteredTransactions.length;
  const totalPages = Math.ceil(totalItems / pageSize);
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  const paginatedTransactions = filteredTransactions.slice(startIndex, endIndex);

  // Handle page change
  const handlePageChange = (page) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page);
    }
  };

  // Handle page size change
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

  const exportToCSV = () => {
    const headers = ['ID', 'User', 'Email', 'Phone', 'Amount', 'Status', 'Reference', 'Created At', 'Companies'];
    const csvData = filteredTransactions.map(transaction => [
      transaction.id,
      transaction.user ? `${transaction.user.firstname} ${transaction.user.lastname}`.trim() || transaction.user.username : 'N/A',
      transaction.customer_email || 'N/A',
      transaction.phone_number || 'N/A',
      transaction.amount,
      transaction.result_code === 0 ? 'Success' : transaction.result_code === null ? 'Pending' : 'Failed',
      transaction.reference_code || 'N/A',
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

  const getStatusIcon = (transaction) => {
    if (transaction.result_code === 0) return CheckCircle;
    if (transaction.result_code === null) return Clock;
    return XCircle;
  };

  const getStatusColor = (transaction) => {
    if (transaction.result_code === 0) return 'text-green-600';
    if (transaction.result_code === null) return 'text-yellow-600';
    return 'text-red-600';
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
      {/* Header with Stats */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-800 dark:text-white mb-2">Transaction History</h1>
        <p className="text-slate-600 dark:text-slate-400">View all payments, users, and their associated companies</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
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
      </div>

      {/* Search and Filter Controls */}
      <div className="flex flex-col lg:flex-row gap-4 mb-6">
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search by phone, email, confirmation code, company name..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
          />
        </div>
        <div className="flex flex-col sm:flex-row gap-4">
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
              <option value="pending">Pending</option>
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

      {/* Date Range Filter */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
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
        <div className="flex items-end">
          <button
            onClick={() => setDateRange({ start: '', end: '' })}
            className="w-full px-4 py-2 text-slate-600 dark:text-slate-400 border border-slate-300 dark:border-slate-600 rounded-xl hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
          >
            Clear Dates
          </button>
        </div>
      </div>

      {/* Transactions Grid */}
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
            {paginatedTransactions.map((transaction, index) => {
              const StatusIcon = getStatusIcon(transaction);
              return (
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
                            `${transaction.customer_first_name} ${transaction.customer_last_name}`.trim() || 
                            transaction.user.username : 
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
                        {transaction.customer_phone || 'N/A'}
                      </p>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center space-x-1">
                      <span className="font-medium text-slate-800 dark:text-slate-200">
                        {transaction.currency || 'KES'} {transaction.amount?.toFixed(2) || '0.00'}
                      </span>
                    </div>
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
                    <div className={`flex items-center space-x-1 px-2 py-1 rounded-full text-xs ${
                      transaction.confirmation_code !== null 
                        ? 'bg-green-100 text-green-600 dark:bg-green-900/50 dark:text-green-400'
                        : 'bg-red-100 text-red-600 dark:bg-red-900/50 dark:text-red-400'
                    }`}>
                      <StatusIcon className="w-3 h-3" />
                      <span>
                        {transaction.confirmation_code !== null ? 'Success' : 'Failed'}
                      </span>
                    </div>
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
              );
            })}
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