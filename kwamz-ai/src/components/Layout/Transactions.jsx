import React, { useState, useEffect } from 'react';
import { Search, Filter, Eye } from 'lucide-react';
import axios from 'axios';
import config from '../../Config';

function TransactionDetailsModal({ isOpen, onClose, transaction }) {
  if (!isOpen || !transaction) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-slate-800 rounded-xl p-6 w-full max-w-md">
        <h2 className="text-xl font-bold text-slate-800 dark:text-white mb-4">Transaction Details</h2>
        <div className="space-y-3">
          <p><strong>ID:</strong> {transaction.id}</p>
          <p><strong>User:</strong> {transaction.user?.username || 'N/A'}</p>
          <p><strong>Amount:</strong> ${transaction.amount.toFixed(2)}</p>
          <p><strong>Time Paid:</strong> {new Date(transaction.time_paid).toLocaleString()}</p>
          <p><strong>Phone Number:</strong> {transaction.phone_number || 'N/A'}</p>
          <p><strong>Checkout ID:</strong> {transaction.checkout_id || 'N/A'}</p>
          <p><strong>Reference Code:</strong> {transaction.reference_code || 'N/A'}</p>
          <p><strong>Result:</strong> {transaction.result_desc || 'N/A'}</p>
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

  // Fetch transactions from API
  useEffect(() => {
    const fetchTransactions = async () => {
      try {
        const token = localStorage.getItem('token');
        const response = await axios.get(`${config.API_URL}/payments`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        setTransactions(response.data);
        setFilteredTransactions(response.data);
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
          t.reference_code?.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // Apply filter
    if (filter === 'success') {
      filtered = filtered.filter((t) => t.result_code === 0);
    } else if (filter === 'failed') {
      filtered = filtered.filter((t) => t.result_code !== 0);
    } else if (filter === 'recent') {
      filtered = filtered.filter(
        (t) => new Date(t.time_paid) >= new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)
      );
    }

    setFilteredTransactions(filtered);
  }, [searchTerm, filter, transactions]);

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
            placeholder="Search by phone or reference code"
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
            <option value="failed">Failed</option>
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
              <th className="px-4 py-3 font-semibold">User</th>
              <th className="px-4 py-3 font-semibold">Amount</th>
              <th className="px-4 py-3 font-semibold">Time Paid</th>
              <th className="px-4 py-3 font-semibold">Phone Number</th>
              <th className="px-4 py-3 font-semibold">Reference Code</th>
              <th className="px-4 py-3 font-semibold">Status</th>
              <th className="px-4 py-3 font-semibold">Action</th>
            </tr>
          </thead>
          <tbody>
            {filteredTransactions.map((transaction, index) => (
              <tr
                key={transaction.id}
                className={`border-b border-slate-200 dark:border-slate-600 ${
                  index % 2 === 0 ? 'bg-white dark:bg-slate-800' : 'bg-slate-50 dark:bg-slate-700/50'
                } hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors`}
              >
                <td className="px-4 py-3">{transaction.id}</td>
                <td className="px-4 py-3">{transaction.user?.username || 'N/A'}</td>
                <td className="px-4 py-3">${transaction.amount.toFixed(2)}</td>
                <td className="px-4 py-3">{new Date(transaction.time_paid).toLocaleString()}</td>
                <td className="px-4 py-3">{transaction.phone_number || 'N/A'}</td>
                <td className="px-4 py-3">{transaction.reference_code || 'N/A'}</td>
                <td className="px-4 py-3">
                  <span
                    className={`px-2 py-1 rounded-full text-xs ${
                      transaction.result_code === 0
                        ? 'bg-green-100 text-green-600 dark:bg-green-900/50 dark:text-green-400'
                        : 'bg-red-100 text-red-600 dark:bg-red-900/50 dark:text-red-400'
                    }`}
                  >
                    {transaction.result_code === 0 ? 'Success' : 'Failed'}
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