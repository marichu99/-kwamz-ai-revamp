import { useState, useEffect, useRef } from 'react';
import { Search, MoreVertical, Edit, Plus, Download, Upload, RefreshCw, Trash2, ChevronRight, Power, Save, Eye, EyeOff, Copy, Check } from 'lucide-react';
import axios from 'axios';
import config from '../../Config';
import { useToast } from './ToastProvider';
import ConfigDetailsModal from './ConfigDetailsModal.jsx';

function ConfigGrid() {
  const [configs, setConfigs] = useState([]);
  const [filteredConfigs, setFilteredConfigs] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedConfigIds, setSelectedConfigIds] = useState([]);
  const [isConfigModalOpen, setIsConfigModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [copiedField, setCopiedField] = useState(null);
  const [isExportSubMenuOpen, setIsExportSubMenuOpen] = useState(false);
  const { showToast } = useToast();
  const dropdownRef = useRef(null);

  // Fetch configs from API
  const fetchConfigs = async () => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${config.API_URL}/fraud/config`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setConfigs(response.data.data || response.data);
      setFilteredConfigs(response.data.data || response.data);
      setSelectedConfigIds([]);
      setCurrentPage(1);
      showToast('Configurations reloaded successfully', 'success');
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
        setIsExportSubMenuOpen(false);
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
        c.sender_email?.toLowerCase().includes(searchTerm.toLowerCase())
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

  // Handle activate config
  const handleActivateConfig = async () => {
    if (selectedConfigIds.length === 0) {
      showToast('Please select a configuration to activate', 'error');
      return;
    }
    if (selectedConfigIds.length > 1) {
      showToast('Please select only one configuration to activate', 'error');
      return;
    }

    setIsLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(
        `${config.API_URL}/fraud/config/${selectedConfigIds[0]}/activate`,
        {},
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      await fetchConfigs();
      showToast('Configuration activated successfully', 'success');
    } catch (error) {
      console.error('Error activating configuration:', error.response?.data || error.message);
      showToast('Failed to activate configuration', 'error');
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
          axios.delete(`${config.API_URL}/fraud/config/${id}`, {
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

  // Handle duplicate config
  const handleDuplicateConfig = () => {
    if (selectedConfigIds.length === 0) {
      showToast('Please select a configuration to duplicate', 'error');
      return;
    }
    if (selectedConfigIds.length > 1) {
      showToast('Please select only one configuration to duplicate', 'error');
      return;
    }

    setIsLoading(true);
    try {
      const selectedConfig = configs.find((c) => c.id === selectedConfigIds[0]);
      const duplicateData = {
        ...selectedConfig,
        name: `${selectedConfig.name} - Copy`,
        is_active: false,
        description: `Copy of ${selectedConfig.name} - ${selectedConfig.description || ''}`
      };

      delete duplicateData.id;
      delete duplicateData.created_at;
      delete duplicateData.updated_at;

      setIsConfigModalOpen(true);
      // Pass the duplicate data to modal
      sessionStorage.setItem('duplicateConfig', JSON.stringify(duplicateData));
      showToast('Configuration ready for duplication. Please review and save.', 'info');
    } catch (error) {
      console.error('Error duplicating configuration:', error);
      showToast('Failed to prepare configuration for duplication', 'error');
    } finally {
      setIsLoading(false);
      setIsDropdownOpen(false);
    }
  };

  // Handle copy to clipboard
  const handleCopyToClipboard = (field, value) => {
    navigator.clipboard.writeText(value)
      .then(() => {
        setCopiedField(field);
        showToast(`${field} copied to clipboard`, 'success');
        setTimeout(() => setCopiedField(null), 2000);
      })
      .catch(() => {
        showToast('Failed to copy to clipboard', 'error');
      });
  };

  // Handle export JSON
  const handleExportJSON = () => {
    if (selectedConfigIds.length === 0) {
      showToast('Please select configurations to export', 'error');
      return;
    }

    const selectedConfigs = configs.filter(c => selectedConfigIds.includes(c.id));
    const exportData = {
      exported_at: new Date().toISOString(),
      total_configs: selectedConfigs.length,
      configs: selectedConfigs
    };

    const dataStr = JSON.stringify(exportData, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    
    const exportFileDefaultName = `fraud-configs-${new Date().toISOString().split('T')[0]}.json`;
    
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();

    showToast(`${selectedConfigs.length} configuration(s) exported as JSON`, 'success');
    setIsDropdownOpen(false);
    setIsExportSubMenuOpen(false);
  };

  // Handle export CSV
  const handleExportCSV = () => {
    if (selectedConfigIds.length === 0) {
      showToast('Please select configurations to export', 'error');
      return;
    }

    const selectedConfigs = configs.filter(c => selectedConfigIds.includes(c.id));
    const headers = [
      'ID', 'Name', 'Status', 'Email Enabled', 'SMTP Server', 'Sender Email',
      'Time Window', 'Amount Variance', 'High Risk Score', 'Created At'
    ];

    const csvData = selectedConfigs.map(config => [
      config.id,
      config.name,
      config.is_active ? 'Active' : 'Inactive',
      config.email_enabled ? 'Yes' : 'No',
      config.smtp_server,
      config.sender_email,
      config.time_window_minutes,
      config.amount_variance,
      config.high_risk_score,
      new Date(config.created_at).toLocaleDateString()
    ]);

    const csvContent = [
      headers.join(','),
      ...csvData.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    link.setAttribute('href', url);
    link.setAttribute('download', `fraud-configs-${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    showToast(`${selectedConfigs.length} configuration(s) exported as CSV`, 'success');
    setIsDropdownOpen(false);
    setIsExportSubMenuOpen(false);
  };

  // Handle import configs
  const handleImportConfigs = () => {
    // This would trigger a file input for JSON import
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = '.json';
    fileInput.onchange = async (e) => {
      const file = e.target.files[0];
      if (!file) return;

      setIsLoading(true);
      try {
        const reader = new FileReader();
        reader.onload = async (e) => {
          try {
            const importData = JSON.parse(e.target.result);
            const token = localStorage.getItem('token');
            
            // Validate import data structure
            if (!importData.configs || !Array.isArray(importData.configs)) {
              throw new Error('Invalid import file format');
            }

            // Import each config
            for (const configData of importData.configs) {
              await axios.post(`${config.API_URL}/fraud/config`, configData, {
                headers: { Authorization: `Bearer ${token}` },
              });
            }

            await fetchConfigs();
            showToast(`${importData.configs.length} configuration(s) imported successfully`, 'success');
          } catch (error) {
            console.error('Error importing configurations:', error);
            showToast('Failed to import configurations. Please check file format.', 'error');
          } finally {
            setIsLoading(false);
          }
        };
        reader.readAsText(file);
      } catch (error) {
        console.error('Error reading file:', error);
        showToast('Failed to read import file', 'error');
        setIsLoading(false);
      }
    };
    fileInput.click();
  };

  // Handle create or update config
  const handleCreateOrUpdateConfig = async (formData, configId, resetForm) => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem('token');
      const url = configId ? `${config.API_URL}/fraud/config/${configId}` : `${config.API_URL}/fraud/config`;
      const method = configId ? 'PUT' : 'POST';

      // Handle duplicate config from session storage
      if (!configId) {
        const duplicateData = sessionStorage.getItem('duplicateConfig');
        if (duplicateData) {
          formData = { ...JSON.parse(duplicateData), ...formData };
          sessionStorage.removeItem('duplicateConfig');
        }
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

      await fetchConfigs();
      setIsConfigModalOpen(false);
      setSelectedConfigIds([]);
      if (resetForm) resetForm();
      
      showToast(`Configuration ${configId ? 'updated' : 'created'} successfully!`, 'success');
    } catch (error) {
      console.error(`Error ${configId ? 'updating' : 'creating'} configuration:`, error.response?.data || error.message);
      showToast(error.response?.data?.message || `Failed to ${configId ? 'update' : 'create'} configuration`, 'error');
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

  // Get email status badge
  const getEmailStatusBadge = (emailEnabled) => (
    <span className={`px-2 py-1 rounded-full text-xs font-semibold ${emailEnabled ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'}`}>
      {emailEnabled ? 'Enabled' : 'Disabled'}
    </span>
  );

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-lg p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-800 dark:text-white mb-2">
          Fraud Detection Configurations
        </h1>
        <p className="text-slate-600 dark:text-slate-300">
          Manage fraud detection parameters, SMTP settings, and notification preferences
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
            <span>New Configuration</span>
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
            <div className="absolute right-0 mt-2 w-64 bg-white dark:bg-slate-700 rounded-xl shadow-lg z-10 border border-slate-200 dark:border-slate-600 overflow-visible">
              <div className="py-2">
                <button
                  onClick={handleEditConfig}
                  disabled={selectedConfigIds.length !== 1}
                  className="w-full flex items-center px-4 py-2 text-sm text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors rounded-t-xl"
                >
                  <Edit className="w-4 h-4 mr-3" />
                  Edit Selected
                </button>
                <button
                  onClick={handleDuplicateConfig}
                  disabled={selectedConfigIds.length !== 1}
                  className="w-full flex items-center px-4 py-2 text-sm text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <Copy className="w-4 h-4 mr-3" />
                  Duplicate
                </button>
                <button
                  onClick={handleActivateConfig}
                  disabled={selectedConfigIds.length !== 1}
                  className="w-full flex items-center px-4 py-2 text-sm text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <Power className="w-4 h-4 mr-3" />
                  Activate
                </button>
                <div className="relative">
                  <button
                    onClick={() => setIsExportSubMenuOpen(!isExportSubMenuOpen)}
                    onMouseEnter={() => setIsExportSubMenuOpen(true)}
                    className="w-full flex items-center justify-between px-4 py-2 text-sm text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-600 transition-colors"
                  >
                    <div className="flex items-center">
                      <Download className="w-4 h-4 mr-3" />
                      Export
                    </div>
                    <ChevronRight className="w-4 h-4 text-slate-500 dark:text-slate-400" />
                  </button>
                  {isExportSubMenuOpen && (
                    <div
                      className="absolute right-full top-0 mr-1 w-48 bg-white dark:bg-slate-700 rounded-xl shadow-lg border border-slate-200 dark:border-slate-600 z-[60]"
                      onMouseEnter={() => setIsExportSubMenuOpen(true)}
                      onMouseLeave={() => setIsExportSubMenuOpen(false)}
                    >
                      <button
                        onClick={handleExportJSON}
                        disabled={selectedConfigIds.length === 0}
                        className="w-full flex items-center px-4 py-2 text-sm text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors rounded-t-xl"
                      >
                        Export as JSON
                      </button>
                      <button
                        onClick={handleExportCSV}
                        disabled={selectedConfigIds.length === 0}
                        className="w-full flex items-center px-4 py-2 text-sm text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        Export as CSV
                      </button>
                      <button
                        onClick={handleImportConfigs}
                        className="w-full flex items-center px-4 py-2 text-sm text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-600 transition-colors rounded-b-xl"
                      >
                        <Upload className="w-4 h-4 mr-3" />
                        Import Configs
                      </button>
                    </div>
                  )}
                </div>
                <button
                  onClick={handleDeleteConfig}
                  disabled={selectedConfigIds.length === 0}
                  className="w-full flex items-center px-4 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 disabled:opacity-50 disabled:cursor-not-allowed transition-colors rounded-b-xl"
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
            placeholder="Search by name, description, or email"
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
              <th className="px-4 py-3 font-semibold">ID</th>
              <th className="px-4 py-3 font-semibold">Name</th>
              <th className="px-4 py-3 font-semibold">Status</th>
              <th className="px-4 py-3 font-semibold">SMTP Settings</th>
              <th className="px-4 py-3 font-semibold">Email Status</th>
              <th className="px-4 py-3 font-semibold">Detection Parameters</th>
              <th className="px-4 py-3 font-semibold">Updated</th>
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
                <td className="px-4 py-3">{c.id}</td>
                <td className="px-4 py-3">
                  <div>
                    <div className="font-medium text-slate-800 dark:text-white">{c.name}</div>
                    {c.description && (
                      <div className="text-sm text-slate-500 dark:text-slate-400 truncate max-w-xs">
                        {c.description}
                      </div>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3">{getStatusBadge(c.is_active)}</td>
                <td className="px-4 py-3">
                  <div className="space-y-1">
                    <div className="flex items-center justify-between group">
                      <span className="text-sm">{c.smtp_server}:{c.smtp_port}</span>
                      <button
                        onClick={() => handleCopyToClipboard('SMTP', `${c.smtp_server}:${c.smtp_port}`)}
                        className="opacity-0 group-hover:opacity-100 transition-opacity ml-2"
                      >
                        {copiedField === 'SMTP' ? (
                          <Check className="w-3 h-3 text-green-500" />
                        ) : (
                          <Copy className="w-3 h-3 text-slate-400 hover:text-slate-600" />
                        )}
                      </button>
                    </div>
                    <div className="flex items-center justify-between group">
                      <span className="text-sm truncate max-w-xs">{c.sender_email}</span>
                      <button
                        onClick={() => handleCopyToClipboard('Email', c.sender_email)}
                        className="opacity-0 group-hover:opacity-100 transition-opacity ml-2"
                      >
                        {copiedField === 'Email' ? (
                          <Check className="w-3 h-3 text-green-500" />
                        ) : (
                          <Copy className="w-3 h-3 text-slate-400 hover:text-slate-600" />
                        )}
                      </button>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3">{getEmailStatusBadge(c.email_enabled)}</td>
                <td className="px-4 py-3">
                  <div className="text-sm space-y-1">
                    <div>Window: {c.time_window_minutes} min</div>
                    <div>Variance: {(c.amount_variance * 100).toFixed(0)}%</div>
                    <div>High Risk: ≥{c.high_risk_score}</div>
                  </div>
                </td>
                <td className="px-4 py-3 text-sm text-slate-500 dark:text-slate-400">
                  {new Date(c.updated_at).toLocaleDateString()}
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
            <svg className="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-slate-600 dark:text-slate-300 mb-2">
            No configurations found
          </h3>
          <p className="text-slate-500 dark:text-slate-400 mb-6">
            {searchTerm ? 'Try adjusting your search terms' : 'Create your first fraud detection configuration'}
          </p>
          {!searchTerm && (
            <button
              onClick={handleOpenCreateModal}
              className="inline-flex items-center space-x-2 py-2 px-4 bg-blue-500 text-white rounded-xl hover:bg-blue-600 transition-colors"
            >
              <Plus className="w-4 h-4" />
              <span>Create Configuration</span>
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
      <ConfigDetailsModal
        isOpen={isConfigModalOpen}
        onClose={() => {
          setIsConfigModalOpen(false);
          setSelectedConfigIds([]);
          sessionStorage.removeItem('duplicateConfig');
        }}
        onSubmit={handleCreateOrUpdateConfig}
        isLoading={isLoading}
        config={selectedConfigIds.length === 1 ? configs.find((c) => c.id === selectedConfigIds[0]) : null}
      />
    </div>
  );
}

export default ConfigGrid;