import { useState, useEffect, useRef } from 'react';
import { Search, MoreVertical, Edit, Plus, RefreshCw, Trash2, Power, Clock, Mail, Calendar, FileText } from 'lucide-react';
import axios from 'axios';
import config from '../../Config';
import { useToast } from './ToastProvider';
import UserReportConfigModal from './UserReportConfigModal.jsx';

function UserReportConfigGrid() {
  const [configs, setConfigs] = useState([]);
  const [filteredConfigs, setFilteredConfigs] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedConfigIds, setSelectedConfigIds] = useState([]);
  const [isConfigModalOpen, setIsConfigModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const { showToast } = useToast();
  const dropdownRef = useRef(null);

  // Report type display mapping
  const reportTypeLabels = {
    'periodic_fraud': 'Periodic Fraud Report',
    'historical_fraud': 'Historical Fraud Report',
    'daily_fraud': 'Daily Fraud Report',
    'commissions': 'Commissions Report'
  };

  // Fetch configs from API
  const fetchConfigs = async () => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${config.API_URL}/user-report-config/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setConfigs(response.data.data || []);
      setFilteredConfigs(response.data.data || []);
      setSelectedConfigIds([]);
      setCurrentPage(1);
      showToast('Report configurations loaded successfully', 'success');
    } catch (error) {
      console.error('Error fetching configurations:', error.response?.data || error.message);
      showToast('Failed to fetch configurations', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchConfigs();
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
    const filtered = configs.filter(
      (c) =>
        c.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        c.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        reportTypeLabels[c.report_type]?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        c.recipient_emails?.toLowerCase().includes(searchTerm.toLowerCase())
    );
    setFilteredConfigs(filtered);
    setCurrentPage(1);
  }, [searchTerm, configs]);

  // Pagination calculations
  const totalItems = filteredConfigs.length;
  const totalPages = Math.ceil(totalItems / pageSize);
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  const paginatedConfigs = filteredConfigs.slice(startIndex, endIndex);

  // Handle page change
  const handlePageChange = (page) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page);
      setSelectedConfigIds([]);
    }
  };

  // Handle page size change
  const handlePageSizeChange = (e) => {
    setPageSize(Number(e.target.value));
    setCurrentPage(1);
    setSelectedConfigIds([]);
  };

  // Handle checkbox selection
  const handleSelectConfig = (configId) => {
    setSelectedConfigIds((prev) =>
      prev.includes(configId)
        ? prev.filter((id) => id !== configId)
        : [...prev, configId]
    );
  };

  // Handle select all checkboxes
  const handleSelectAll = () => {
    if (selectedConfigIds.length === paginatedConfigs.length) {
      setSelectedConfigIds([]);
    } else {
      setSelectedConfigIds(paginatedConfigs.map((c) => c.id));
    }
  };

  // Handle edit config
  const handleEditConfig = () => {
    if (selectedConfigIds.length === 0) {
      showToast('Please select a configuration to edit', 'error');
      return;
    }
    if (selectedConfigIds.length > 1) {
      showToast('Please select only one configuration to edit', 'error');
      return;
    }
    setIsConfigModalOpen(true);
    setIsDropdownOpen(false);
  };

  // Handle toggle config
  const handleToggleConfig = async () => {
    if (selectedConfigIds.length === 0) {
      showToast('Please select a configuration to toggle', 'error');
      return;
    }
    if (selectedConfigIds.length > 1) {
      showToast('Please select only one configuration to toggle', 'error');
      return;
    }

    setIsLoading(true);
    try {
      const token = localStorage.getItem('token');
      await axios.post(
        `${config.API_URL}/user-report-config/${selectedConfigIds[0]}/toggle`,
        {},
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      await fetchConfigs();
      showToast('Configuration toggled successfully', 'success');
    } catch (error) {
      console.error('Error toggling configuration:', error.response?.data || error.message);
      showToast('Failed to toggle configuration', 'error');
    } finally {
      setIsLoading(false);
      setIsDropdownOpen(false);
    }
  };

  // Handle delete config
  const handleDeleteConfig = async () => {
    if (selectedConfigIds.length === 0) {
      showToast('Please select at least one configuration to delete', 'error');
      return;
    }

    if (!confirm(`Are you sure you want to delete ${selectedConfigIds.length} configuration(s)? This action cannot be undone.`)) {
      return;
    }

    setIsLoading(true);
    try {
      const token = localStorage.getItem('token');
      await Promise.all(
        selectedConfigIds.map((id) =>
          axios.delete(`${config.API_URL}/user-report-config/${id}`, {
            headers: { Authorization: `Bearer ${token}` },
          })
        )
      );
      await fetchConfigs();
      showToast('Selected configurations deleted successfully', 'success');
    } catch (error) {
      console.error('Error deleting configurations:', error.response?.data || error.message);
      showToast('Failed to delete configurations', 'error');
    } finally {
      setIsLoading(false);
      setIsDropdownOpen(false);
    }
  };

  // Handle create config
  const handleOpenCreateModal = () => {
    setSelectedConfigIds([]);
    setIsConfigModalOpen(true);
    setIsDropdownOpen(false);
  };

  // Handle create or update config
  const handleCreateOrUpdateConfig = async (formData, configId, resetForm) => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem('token');
      const url = configId
        ? `${config.API_URL}/user-report-config/${configId}`
        : `${config.API_URL}/user-report-config/`;
      const method = configId ? 'PUT' : 'POST';

      await axios({
        method,
        url,
        data: formData,
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      await fetchConfigs();
      setIsConfigModalOpen(false);
      setSelectedConfigIds([]);
      if (resetForm) resetForm();

      showToast(`Configuration ${configId ? 'updated' : 'created'} successfully!`, 'success');
    } catch (error) {
      console.error(`Error ${configId ? 'updating' : 'creating'} configuration:`, error.response?.data || error.message);
      const errorMessage = error.response?.data?.errors?.join(', ') ||
                          error.response?.data?.message ||
                          `Failed to ${configId ? 'update' : 'create'} configuration`;
      showToast(errorMessage, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  // Get status badge
  const getStatusBadge = (isActive) => (
    <span className={`px-2 py-1 rounded-full text-xs font-semibold ${isActive ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'}`}>
      {isActive ? 'Active' : 'Inactive'}
    </span>
  );

  // Get report type badge
  const getReportTypeBadge = (reportType) => {
    const colors = {
      'periodic_fraud': 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
      'historical_fraud': 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
      'daily_fraud': 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
      'commissions': 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
    };
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-semibold ${colors[reportType] || 'bg-gray-100 text-gray-800'}`}>
        {reportTypeLabels[reportType] || reportType}
      </span>
    );
  };

  // Format frequency display
  const formatFrequency = (value, unit) => {
    const unitLabel = value === 1 ? unit.slice(0, -1) : unit;
    return `Every ${value} ${unitLabel}`;
  };

  // Format date
  const formatDate = (dateString) => {
    if (!dateString) return 'Not scheduled';
    return new Date(dateString).toLocaleString();
  };

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-lg p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-800 dark:text-white mb-2">
          Report Scheduling Configurations
        </h1>
        <p className="text-slate-600 dark:text-slate-300">
          Configure automated report generation and email delivery schedules
        </p>
      </div>

      {/* Action Buttons */}
      <div className="flex justify-between items-center mb-6">
        <div className="flex space-x-4">
          <button
            onClick={fetchConfigs}
            disabled={isLoading}
            className="flex items-center space-x-2 py-2 px-4 bg-green-500 text-white rounded-xl hover:bg-green-600 transition-colors disabled:bg-green-300 disabled:cursor-not-allowed"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Reload</span>
          </button>
          <button
            onClick={handleOpenCreateModal}
            className="flex items-center space-x-2 py-2 px-4 bg-blue-500 text-white rounded-xl hover:bg-blue-600 transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span>New Schedule</span>
          </button>
        </div>

        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            className="flex items-center space-x-2 py-2 px-4 bg-slate-200 dark:bg-slate-700 text-slate-800 dark:text-white rounded-xl hover:bg-slate-300 dark:hover:bg-slate-600 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
            aria-haspopup="true"
            aria-expanded={isDropdownOpen}
          >
            <MoreVertical className="w-4 h-4" />
            <span>Actions</span>
          </button>
          {isDropdownOpen && (
            <div className="absolute right-0 mt-2 w-56 bg-white dark:bg-slate-700 rounded-xl shadow-lg z-10 border border-slate-200 dark:border-slate-600">
              <div className="py-2">
                <button
                  onClick={handleEditConfig}
                  disabled={selectedConfigIds.length !== 1}
                  className="w-full flex items-center px-4 py-2 text-sm text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <Edit className="w-4 h-4 mr-3" />
                  Edit Selected
                </button>
                <button
                  onClick={handleToggleConfig}
                  disabled={selectedConfigIds.length !== 1}
                  className="w-full flex items-center px-4 py-2 text-sm text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <Power className="w-4 h-4 mr-3" />
                  Toggle Active
                </button>
                <button
                  onClick={handleDeleteConfig}
                  disabled={selectedConfigIds.length === 0}
                  className="w-full flex items-center px-4 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
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
            placeholder="Search by name, report type, or email"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
          />
        </div>
      </div>

      {/* Configs Grid */}
      <div className="overflow-x-auto">
        <table className="w-full table-auto">
          <thead>
            <tr className="bg-slate-100 dark:bg-slate-700 text-left text-slate-600 dark:text-slate-300">
              <th className="px-4 py-3 font-semibold">
                <input
                  type="checkbox"
                  checked={selectedConfigIds.length === paginatedConfigs.length && paginatedConfigs.length > 0}
                  onChange={handleSelectAll}
                  className="w-4 h-4 text-blue-600 border-slate-300 rounded focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600"
                />
              </th>
              <th className="px-4 py-3 font-semibold">Name</th>
              <th className="px-4 py-3 font-semibold">Report Type</th>
              <th className="px-4 py-3 font-semibold">Frequency</th>
              <th className="px-4 py-3 font-semibold">Recipients</th>
              <th className="px-4 py-3 font-semibold">Status</th>
              <th className="px-4 py-3 font-semibold">Next Run</th>
            </tr>
          </thead>
          <tbody>
            {paginatedConfigs.map((c, index) => (
              <tr
                key={c.id}
                className={`border-b border-slate-200 dark:border-slate-600 ${index % 2 === 0 ? 'bg-white dark:bg-slate-800' : 'bg-slate-50 dark:bg-slate-700/50'
                  } hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors`}
              >
                <td className="px-4 py-3">
                  <input
                    type="checkbox"
                    checked={selectedConfigIds.includes(c.id)}
                    onChange={() => handleSelectConfig(c.id)}
                    className="w-4 h-4 text-blue-600 border-slate-300 rounded focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600"
                  />
                </td>
                <td className="px-4 py-3">
                  <div>
                    <div className="font-medium text-slate-800 dark:text-white flex items-center">
                      <FileText className="w-4 h-4 mr-2 text-slate-500" />
                      {c.name}
                    </div>
                    {c.description && (
                      <div className="text-sm text-slate-500 dark:text-slate-400 truncate max-w-xs">
                        {c.description}
                      </div>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3">{getReportTypeBadge(c.report_type)}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center text-sm">
                    <Clock className="w-4 h-4 mr-2 text-slate-500" />
                    {formatFrequency(c.frequency_value, c.frequency_unit)}
                  </div>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center">
                    <Mail className="w-4 h-4 mr-2 text-slate-500" />
                    <span className="text-sm truncate max-w-xs" title={c.recipient_emails}>
                      {c.recipient_emails?.split(',').length || 0} recipient(s)
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3">{getStatusBadge(c.is_active)}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center text-sm text-slate-500 dark:text-slate-400">
                    <Calendar className="w-4 h-4 mr-2" />
                    {formatDate(c.next_run_at)}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Empty State */}
      {filteredConfigs.length === 0 && (
        <div className="text-center py-12">
          <div className="text-slate-400 dark:text-slate-500 mb-4">
            <Clock className="w-16 h-16 mx-auto" />
          </div>
          <h3 className="text-lg font-medium text-slate-600 dark:text-slate-300 mb-2">
            No report schedules found
          </h3>
          <p className="text-slate-500 dark:text-slate-400 mb-6">
            {searchTerm ? 'Try adjusting your search terms' : 'Create your first report schedule configuration'}
          </p>
          {!searchTerm && (
            <button
              onClick={handleOpenCreateModal}
              className="inline-flex items-center space-x-2 py-2 px-4 bg-blue-500 text-white rounded-xl hover:bg-blue-600 transition-colors"
            >
              <Plus className="w-4 h-4" />
              <span>Create Schedule</span>
            </button>
          )}
        </div>
      )}

      {/* Pagination Controls */}
      {filteredConfigs.length > 0 && (
        <div className="flex flex-col sm:flex-row justify-between items-center mt-6 pt-6 border-t border-slate-200 dark:border-slate-600 space-y-4 sm:space-y-0">
          <div className="flex items-center space-x-2">
            <span className="text-sm text-slate-600 dark:text-slate-300">
              Showing {startIndex + 1} - {Math.min(endIndex, totalItems)} of {totalItems} configurations
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

      {/* Config Details Modal */}
      <UserReportConfigModal
        isOpen={isConfigModalOpen}
        onClose={() => {
          setIsConfigModalOpen(false);
          setSelectedConfigIds([]);
        }}
        onSubmit={handleCreateOrUpdateConfig}
        isLoading={isLoading}
        config={selectedConfigIds.length === 1 ? configs.find((c) => c.id === selectedConfigIds[0]) : null}
      />
    </div>
  );
}

export default UserReportConfigGrid;
