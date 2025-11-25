import React, { useState, useEffect } from 'react';
import { Search, Filter, Eye } from 'lucide-react';
import config from '../../Config';

function TransactionDetailsModal({ isOpen, onClose, transaction }) {
  if (!isOpen || !transaction) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-slate-800 rounded-xl p-6 w-full max-w-md">
        <h2 className="text-xl font-bold text-slate-800 dark:text-white mb-4">Transaction Details</h2>
        <div className="space-y-3 text-slate-700 dark:text-slate-300">
          <p><strong>ID:</strong> {transaction.id}</p>
          <p><strong>Email:</strong> {transaction.customer_email || 'N/A'}</p>
          <p><strong>Amount:</strong> {transaction.currency} {transaction.amount.toFixed(2)}</p>
          <p><strong>Created At:</strong> {new Date(transaction.created_at).toLocaleString()}</p>
          <p><strong>Phone Number:</strong> {transaction.phone_number || 'N/A'}</p>
          <p><strong>Checkout Request ID:</strong> {transaction.checkout_request_id || 'N/A'}</p>
          <p><strong>Merchant Request ID:</strong> {transaction.merchant_request_id || 'N/A'}</p>
          <p><strong>Confirmation Code:</strong> {transaction.confirmation_code || 'Pending'}</p>
          <p><strong>Result:</strong> {transaction.result_desc || 'N/A'}</p>
          <p><strong>User ID:</strong> {transaction.user_id || 'N/A'}</p>
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

function Transactions() {
  const [transactions, setTransactions] = useState([]);
  const [filteredTransactions, setFilteredTransactions] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [filter, setFilter] = useState('all');
  const [selectedTransaction, setSelectedTransaction] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Fetch transactions from API
  useEffect(() => {
    const fetchTransactions = async () => {
      try {
        const token = localStorage.getItem('token');
        const url = `${config.API_URL}/payment/get-payments`;
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
      }
    };
    fetchTransactions();
  }, []);

  // Handle search and filter
  useEffect(() => {
    let filtered = transactions;

    // Apply search
    if (searchTerm) {
      filtered = filtered.filter(
        (t) =>
          t.phone_number?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          t.confirmation_code?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          t.customer_email?.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // Apply filter
    if (filter === 'success') {
      filtered = filtered.filter((t) => t.confirmation_code !== null);
    } else if (filter === 'failed') {
      filtered = filtered.filter((t) => t.confirmation_code === null);
    } else if (filter === 'recent') {
      filtered = filtered.filter(
        (t) => new Date(t.created_at) >= new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)
      );
    }

    setFilteredTransactions(filtered);
    setCurrentPage(1);
  }, [searchTerm, filter, transactions]);

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

  const handleViewTransaction = (transaction) => {
    setSelectedTransaction(transaction);
    setIsModalOpen(true);
  };

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-lg p-6">
      {/* Search and Filter Controls */}
      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search by phone, email or confirmation code"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
          />
        </div>
        <div className="relative">
          <Filter className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="pl-10 pr-4 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
          >
            <option value="all">All Transactions</option>
            <option value="success">Successful</option>
            <option value="failed">Failed/Pending</option>
            <option value="recent">Last 7 Days</option>
          </select>
        </div>
      </div>

      {/* Transactions Grid */}
      <div className="overflow-x-auto">
        <table className="w-full table-auto">
          <thead>
            <tr className="bg-slate-100 dark:bg-slate-700 text-left text-slate-600 dark:text-slate-300">
              <th className="px-4 py-3 font-semibold">ID</th>
              <th className="px-4 py-3 font-semibold">Email</th>
              <th className="px-4 py-3 font-semibold">Amount</th>
              <th className="px-4 py-3 font-semibold">Created At</th>
              <th className="px-4 py-3 font-semibold">Phone Number</th>
              <th className="px-4 py-3 font-semibold">Confirmation Code</th>
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
                <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{transaction.id}</td>
                <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{transaction.customer_email || 'N/A'}</td>
                <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{transaction.currency} {transaction.amount.toFixed(2)}</td>
                <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{new Date(transaction.created_at).toLocaleString()}</td>
                <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{transaction.phone_number || 'N/A'}</td>
                <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{transaction.confirmation_code || 'Pending'}</td>
                <td className="px-4 py-3">
                  <span
                    className={`px-2 py-1 rounded-full text-xs ${
                      transaction.confirmation_code !== null
                        ? 'bg-green-100 text-green-600 dark:bg-green-900/50 dark:text-green-400'
                        : 'bg-yellow-100 text-yellow-600 dark:bg-yellow-900/50 dark:text-yellow-400'
                    }`}
                  >
                    {transaction.confirmation_code !== null ? 'Success' : 'Pending'}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => handleViewTransaction(transaction)}
                    className="flex items-center space-x-1 text-blue-500 hover:text-blue-600 dark:hover:text-blue-400"
                  >
                    <Eye className="w-4 h-4" />
                    <span>View</span>
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Empty State */}
      {filteredTransactions.length === 0 && (
        <div className="text-center py-8 text-slate-500 dark:text-slate-400">
          No transactions found
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