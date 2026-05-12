import { useState, useEffect, useRef } from 'react';
import { Search, MoreVertical, Edit, Plus, Download, Upload, RefreshCw, Trash2, ChevronRight, TestTube, Globe } from 'lucide-react';
import axios from 'axios';
import * as XLSX from 'xlsx';
import config from '../../Config';
import { useToast } from './ToastProvider';
import BankDetailsModal from './BankDetailsModal';
// import ConnectionTestModal from './ConnectionTestModal';

function BankList() {
  const [banks, setBanks] = useState([]);
  const [filteredBanks, setFilteredBanks] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedBankIds, setSelectedBankIds] = useState([]);
  const [isBankModalOpen, setIsBankModalOpen] = useState(false);
  const [isConnectionTestModalOpen, setIsConnectionTestModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const { showToast } = useToast();
  const dropdownRef = useRef(null);

  // Fetch banks from API
  const fetchBanks = async () => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${config.API_URL}/banks`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      setBanks(response.data.data);
      setFilteredBanks(response.data.data);
      setSelectedBankIds([]);
      setCurrentPage(1);
      showToast('Banks reloaded successfully', 'success');
    } catch (error) {
      console.error('Error fetching banks:', error.response?.data || error.message);
      showToast('Failed to fetch banks', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchBanks();
  }, []);

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

  // Handle search
  useEffect(() => {
    const filtered = banks.filter(
      (b) =>
        b.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        b.code?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        b.country?.toLowerCase().includes(searchTerm.toLowerCase())
    );
    setFilteredBanks(filtered);
    setCurrentPage(1);
  }, [searchTerm, banks]);

  // Pagination calculations
  const totalItems = filteredBanks.length;
  const totalPages = Math.ceil(totalItems / pageSize);
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  const paginatedBanks = filteredBanks.slice(startIndex, endIndex);

  // Handle page change
  const handlePageChange = (page) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page);
      setSelectedBankIds([]);
    }
  };

  // Handle page size change
  const handlePageSizeChange = (e) => {
    setPageSize(Number(e.target.value));
    setCurrentPage(1);
    setSelectedBankIds([]);
  };

  // Handle checkbox selection
  const handleSelectBank = (bankId) => {
    setSelectedBankIds((prev) =>
      prev.includes(bankId)
        ? prev.filter((id) => id !== bankId)
        : [...prev, bankId]
    );
  };

  // Handle select all checkboxes
  const handleSelectAll = () => {
    if (selectedBankIds.length === paginatedBanks.length) {
      setSelectedBankIds([]);
    } else {
      setSelectedBankIds(paginatedBanks.map((b) => b.id));
    }
  };

  // Handle edit bank
  const handleEditBank = () => {
    if (selectedBankIds.length === 0) {
      showToast('Please select a bank to edit', 'error');
      return;
    }
    if (selectedBankIds.length > 1) {
      showToast('Please select only one bank to edit', 'error');
      return;
    }
    setIsBankModalOpen(true);
    setIsDropdownOpen(false);
  };

  // Handle test connection
  const handleTestConnection = () => {
    if (selectedBankIds.length === 0) {
      showToast('Please select a bank to test', 'error');
      return;
    }
    if (selectedBankIds.length > 1) {
      showToast('Please select only one bank to test', 'error');
      return;
    }
    setIsConnectionTestModalOpen(true);
    setIsDropdownOpen(false);
  };

  // Handle delete bank
  const handleDeleteBank = async () => {
    if (selectedBankIds.length === 0) {
      showToast('Please select at least one bank to delete', 'error');
      return;
    }
    
    if (!window.confirm(`Are you sure you want to delete ${selectedBankIds.length} bank(s)?`)) {
      return;
    }
    
    setIsLoading(true);
    try {
      const token = localStorage.getItem('token');
      await Promise.all(
        selectedBankIds.map((id) =>
          axios.delete(`${config.API_URL}/banks/${id}`, {
            headers: { Authorization: `Bearer ${token}` },
          })
        )
      );
      await fetchBanks();
      showToast('Selected banks deleted successfully', 'success');
    } catch (error) {
      console.error('Error deleting banks:', error.response?.data || error.message);
      showToast('Failed to delete banks', 'error');
    } finally {
      setIsLoading(false);
      setIsDropdownOpen(false);
    }
  };

  // Handle create bank
  const handleOpenCreateModal = () => {
    setSelectedBankIds([]);
    setIsBankModalOpen(true);
    setIsDropdownOpen(false);
  };

  // Handle create or update bank
  const handleCreateOrUpdateBank = async (formData, bankId, resetForm) => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem('token');
      const url = bankId ? `${config.API_URL}/banks/${bankId}` : `${config.API_URL}/banks`;
      const method = bankId ? 'PUT' : 'POST';

      // Add created_by for new banks
      if (!bankId) {
        formData.created_by = 'current_user'; // Replace with actual user
      }

      const response = await axios({
        method,
        url,
        data: formData,
        headers: { 
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      await fetchBanks();
      setIsBankModalOpen(false);
      setSelectedBankIds([]);
      resetForm();
      showToast(`Bank ${bankId ? 'updated' : 'created'} successfully!`, 'success');
    } catch (error) {
      console.error(`Error ${bankId ? 'updating' : 'creating'} bank:`, error.response?.data || error.message);
      showToast(error.response?.data?.error || `Failed to ${bankId ? 'update' : 'create'} bank`, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  // Handle test connection submission
  const handleTestConnectionSubmit = async (bankId) => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(`${config.API_URL}/banks/${bankId}/test-connection`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });

      showToast('Connection test completed successfully', 'success');
      setIsConnectionTestModalOpen(false);
    } catch (error) {
      console.error('Error testing connection:', error.response?.data || error.message);
      showToast(error.response?.data?.error || 'Connection test failed', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    const statusConfig = {
      active: 'bg-emerald-100 text-emerald-800 border-emerald-200',
      inactive: 'bg-slate-100 text-slate-800 border-slate-200',
      pending: 'bg-amber-100 text-amber-800 border-amber-200',
      testing: 'bg-blue-100 text-blue-800 border-blue-200'
    };
    
    return (
      <span className={`px-2 py-1 text-xs font-medium rounded-full border ${statusConfig[status] || statusConfig.inactive}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-lg p-6">
      <div className="sticky top-0 z-20 bg-white dark:bg-slate-800">
      {/* Action Buttons */}
      <div className="flex justify-end mb-4 space-x-4">
        <button
          onClick={fetchBanks}
          disabled={isLoading}
          className="flex items-center space-x-2 py-2 px-4 bg-emerald-500 text-white rounded-xl hover:bg-emerald-600 transition-colors disabled:bg-emerald-300 disabled:cursor-not-allowed"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Reload</span>
        </button>
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            className="flex items-center space-x-2 py-2 px-4 bg-emerald-500 text-white rounded-xl hover:bg-emerald-600 transition-colors focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2 dark:focus:ring-offset-slate-800"
            aria-haspopup="true"
            aria-expanded={isDropdownOpen}
          >
            <MoreVertical className="w-4 h-4" />
            <span>Actions</span>
          </button>
          {isDropdownOpen && (
            <div
              className="absolute right-0 mt-2 w-72 bg-white dark:bg-slate-700 rounded-xl shadow-lg z-10 border border-slate-200 dark:border-slate-600 overflow-visible transition-all duration-200"
              role="menu"
            >
              {/* Main Actions */}
              <div className="py-2">
                <button
                  onClick={handleEditBank}
                  disabled={selectedBankIds.length === 0 || selectedBankIds.length > 1}
                  className="w-full flex items-center px-4 py-2 text-sm text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  role="menuitem"
                >
                  <Edit className="w-4 h-4 mr-3" />
                  Edit Selected
                </button>
                <button
                  onClick={handleTestConnection}
                  disabled={selectedBankIds.length === 0 || selectedBankIds.length > 1}
                  className="w-full flex items-center px-4 py-2 text-sm text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  role="menuitem"
                >
                  <TestTube className="w-4 h-4 mr-3" />
                  Test Connection
                </button>
                <button
                  onClick={handleOpenCreateModal}
                  className="w-full flex items-center px-4 py-2 text-sm text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-600 transition-colors"
                  role="menuitem"
                >
                  <Plus className="w-4 h-4 mr-3" />
                  Create Bank
                </button>
                <button
                  onClick={handleDeleteBank}
                  disabled={selectedBankIds.length === 0}
                  className="w-full flex items-center px-4 py-2 text-sm text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  role="menuitem"
                >
                  <Trash2 className="w-4 h-4 mr-3" />
                  Delete Selected
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Search Control */}
      <div className="mb-6">
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search by name, code, or country"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all"
          />
        </div>
      </div>
      </div>

      {/* Banks Grid */}
      <div className="overflow-x-auto">
        <table className="w-full table-auto">
          <thead>
            <tr className="bg-slate-100 dark:bg-slate-700 text-left text-slate-600 dark:text-slate-300">
              <th className="px-4 py-3 font-semibold">
                <input
                  type="checkbox"
                  checked={selectedBankIds.length === paginatedBanks.length && paginatedBanks.length > 0}
                  onChange={handleSelectAll}
                  className="w-4 h-4 text-emerald-600 border-slate-300 rounded focus:ring-emerald-500 dark:bg-slate-700 dark:border-slate-600"
                />
              </th>
              <th className="px-4 py-3 font-semibold">Bank Name</th>
              <th className="px-4 py-3 font-semibold">Code</th>
              <th className="px-4 py-3 font-semibold">Country</th>
              <th className="px-4 py-3 font-semibold">Currency</th>
              <th className="px-4 py-3 font-semibold">Connection Type</th>
              <th className="px-4 py-3 font-semibold">Status</th>
              <th className="px-4 py-3 font-semibold">Last Updated</th>
            </tr>
          </thead>
          <tbody>
            {paginatedBanks.map((b, index) => (
              <tr
                key={b.id}
                className={`border-b border-slate-200 dark:border-slate-600 ${
                  index % 2 === 0 ? 'bg-white dark:bg-slate-800' : 'bg-slate-50 dark:bg-slate-700/50'
                } hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors`}
              >
                <td className="px-4 py-3">
                  <input
                    type="checkbox"
                    checked={selectedBankIds.includes(b.id)}
                    onChange={() => handleSelectBank(b.id)}
                    className="w-4 h-4 text-emerald-600 border-slate-300 rounded focus:ring-emerald-500 dark:bg-slate-700 dark:border-slate-600"
                  />
                </td>
                <td className="px-4 py-3 font-medium text-slate-800 dark:text-white">{b.name}</td>
                <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{b.code}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center space-x-2">
                    <Globe className="w-4 h-4 text-slate-400" />
                    <span>{b.country}</span>
                  </div>
                </td>
                <td className="px-4 py-3 font-medium text-slate-800 dark:text-white">{b.currency}</td>
                <td className="px-4 py-3">
                  <span className="px-2 py-1 text-xs font-medium bg-emerald-100 text-emerald-800 rounded-full">
                    {b.config?.connection_type?.toUpperCase() || 'N/A'}
                  </span>
                </td>
                <td className="px-4 py-3">{getStatusBadge(b.status)}</td>
                <td className="px-4 py-3 text-sm text-slate-500 dark:text-slate-400">
                  {new Date(b.updated_at).toLocaleDateString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Empty State */}
      {paginatedBanks.length === 0 && (
        <div className="text-center py-12">
          <div className="w-16 h-16 mx-auto mb-4 bg-emerald-100 rounded-full flex items-center justify-center">
            <Plus className="w-8 h-8 text-emerald-600" />
          </div>
          <h3 className="text-lg font-medium text-slate-800 dark:text-white mb-2">No banks found</h3>
          <p className="text-slate-600 dark:text-slate-400 mb-6">
            {searchTerm ? 'Try adjusting your search terms' : 'Get started by creating your first bank configuration'}
          </p>
          {!searchTerm && (
            <button
              onClick={handleOpenCreateModal}
              className="inline-flex items-center space-x-2 py-2 px-4 bg-emerald-500 text-white rounded-xl hover:bg-emerald-600 transition-colors"
            >
              <Plus className="w-4 h-4" />
              <span>Create Bank</span>
            </button>
          )}
        </div>
      )}

      {/* Pagination Controls */}
      {paginatedBanks.length > 0 && (
        <div className="flex flex-col sm:flex-row justify-between items-center mt-4 space-y-4 sm:space-y-0">
          <div className="flex items-center space-x-2">
            <span className="text-sm text-slate-600 dark:text-slate-300">
              Showing {startIndex + 1} - {Math.min(endIndex, totalItems)} of {totalItems} banks
            </span>
            <select
              value={pageSize}
              onChange={handlePageSizeChange}
              className="py-1 px-2 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
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
              className="py-1 px-3 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              First
            </button>
            <button
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={currentPage === 1}
              className="py-1 px-3 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <span className="text-sm text-slate-600 dark:text-slate-300">
              Page {currentPage} of {totalPages}
            </span>
            <button
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={currentPage === totalPages}
              className="py-1 px-3 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
            <button
              onClick={() => handlePageChange(totalPages)}
              disabled={currentPage === totalPages}
              className="py-1 px-3 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Last
            </button>
          </div>
        </div>
      )}

      {/* Bank Details Modal */}
      <BankDetailsModal
        isOpen={isBankModalOpen}
        onClose={() => {
          setIsBankModalOpen(false);
          setSelectedBankIds([]);
        }}
        onSubmit={handleCreateOrUpdateBank}
        isLoading={isLoading}
        bank={selectedBankIds.length === 1 ? banks.find((b) => b.id === selectedBankIds[0]) : null}
      />

      {/* Connection Test Modal */}
      {/* <ConnectionTestModal
        isOpen={isConnectionTestModalOpen}
        onClose={() => {
          setIsConnectionTestModalOpen(false);
          setSelectedBankIds([]);
        }}
        onSubmit={() => handleTestConnectionSubmit(selectedBankIds[0])}
        isLoading={isLoading}
        bank={selectedBankIds.length === 1 ? banks.find((b) => b.id === selectedBankIds[0]) : null}
      /> */}
    </div>
  );
}

export default BankList;