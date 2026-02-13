import { useState, useEffect, useRef } from 'react';
import { Search, MoreVertical, Edit, Plus, Download, Upload, RefreshCw, Trash2, Power, ChevronRight, Filter, X, AlertTriangle, Clock, ShieldCheck, ShieldAlert, ShieldX } from 'lucide-react';
import axios from 'axios';
import * as XLSX from 'xlsx';
import config from '../../Config';
import { useToast } from './ToastProvider';
import AgentCompanyDetailsModal from './AgentCompanyDetailsModal';
import BatchUploadModal from './BatchUploadModal';

function AgentCompanyList() {
  const [agentCompanies, setAgentCompanies] = useState([]);
  const [filteredAgentCompanies, setFilteredAgentCompanies] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedAgentCompanyIds, setSelectedAgentCompanyIds] = useState([]);
  const [isAgentCompanyModalOpen, setIsAgentCompanyModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [isTemplatesSubMenuOpen, setIsTemplatesSubMenuOpen] = useState(false);
  const [isBatchModalOpen, setIsBatchModalOpen] = useState(false);
  const [validAgentCompanies, setValidAgentCompanies] = useState([]);
  const [invalidAgentCompanies, setInvalidAgentCompanies] = useState([]);
  const [batchFile, setBatchFile] = useState(null);
  const [isFilterPanelOpen, setIsFilterPanelOpen] = useState(false);
  const [floatThreshold, setFloatThreshold] = useState('');
  const [commissionThreshold, setCommissionThreshold] = useState('');
  const [fraudFilter, setFraudFilter] = useState('all'); // 'all', 'flagged', 'not_flagged'
  const [fraudAlertData, setFraudAlertData] = useState({});
  const [fraudPopupCompanyId, setFraudPopupCompanyId] = useState(null);
  const { showToast } = useToast();
  const fileInputRef = useRef(null);
  const dropdownRef = useRef(null);
  const filterPanelRef = useRef(null);
  const fraudPopupRef = useRef(null);

  // Fetch agent companies from API
  const fetchAgentCompanies = async () => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${config.API_URL}/agentcompany`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setAgentCompanies(response.data);
      setFilteredAgentCompanies(response.data);
      setSelectedAgentCompanyIds([]);
      setCurrentPage(1);
      showToast('Agent companies reloaded successfully', 'success');
    } catch (error) {
      console.error('Error fetching agent companies:', error.response?.data || error.message);
      showToast('Failed to fetch agent companies', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  // Fetch fraud alerts grouped by agent company
  const fetchFraudAlerts = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${config.API_URL}/fraud/alerts/by-agent-company`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const alertMap = {};
      if (Array.isArray(response.data)) {
        response.data.forEach((item) => {
          alertMap[item.agent_company?.id] = {
            fraud_risk: item.fraud_risk,
            total_alerts: item.total_alerts,
            fraud_alerts: item.fraud_alerts || [],
          };
        });
      }
      setFraudAlertData(alertMap);
    } catch (error) {
      console.error('Error fetching fraud alerts:', error.response?.data || error.message);
    }
  };

  // Format a date string as relative time (e.g., "3h ago", "2d ago")
  const formatRelativeTime = (dateStr) => {
    if (!dateStr) return null;
    const now = new Date();
    const date = new Date(dateStr);
    const diffMs = now - date;
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffSecs < 60) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 30) return `${diffDays}d ago`;
    const diffMonths = Math.floor(diffDays / 30);
    return `${diffMonths}mo ago`;
  };

  useEffect(() => {
    fetchAgentCompanies();
    fetchFraudAlerts();
  }, []);

  // Helper function to get balance from account
  const getAccountBalance = (agentCompany, accountType) => {
    if (!agentCompany.accounts || !Array.isArray(agentCompany.accounts)) {
      return 0;
    }
    const account = agentCompany.accounts.find(
      acc => acc.account_type?.toLowerCase().includes(accountType.toLowerCase())
    );
    if (account?.balances?.current_balance) {
      return parseFloat(account.balances.current_balance) || 0;
    }
    return 0;
  };

  // Handle search and filters
  useEffect(() => {
    let filtered = agentCompanies.filter(
      (ac) =>
        ac.company_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        ac.registration_number?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        ac.till_number?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        ac.contact_phone?.toLowerCase().includes(searchTerm.toLowerCase())
    );

    // Filter by float threshold
    if (floatThreshold !== '' && !isNaN(parseFloat(floatThreshold))) {
      const threshold = parseFloat(floatThreshold);
      filtered = filtered.filter((ac) => {
        const floatBalance = getAccountBalance(ac, 'float');
        return floatBalance < threshold;
      });
    }

    // Filter by commission threshold
    if (commissionThreshold !== '' && !isNaN(parseFloat(commissionThreshold))) {
      const threshold = parseFloat(commissionThreshold);
      filtered = filtered.filter((ac) => {
        const commissionBalance = getAccountBalance(ac, 'commission');
        return commissionBalance < threshold;
      });
    }

    // Filter by fraud flag
    if (fraudFilter === 'flagged') {
      filtered = filtered.filter((ac) =>
        ac.fraud_risk_level?.toLowerCase() === 'high' ||
        ac.fraud_risk_level?.toLowerCase() === 'medium' ||
        ac.fraud_risk_description
      );
    } else if (fraudFilter === 'not_flagged') {
      filtered = filtered.filter((ac) =>
        (!ac.fraud_risk_level || ac.fraud_risk_level?.toLowerCase() === 'low') &&
        !ac.fraud_risk_description
      );
    }

    setFilteredAgentCompanies(filtered);
    setCurrentPage(1);
  }, [searchTerm, agentCompanies, floatThreshold, commissionThreshold, fraudFilter]);

  // Clear all filters
  const clearFilters = () => {
    setFloatThreshold('');
    setCommissionThreshold('');
    setFraudFilter('all');
    setSearchTerm('');
  };

  // Check if any filters are active
  const hasActiveFilters = floatThreshold !== '' || commissionThreshold !== '' || fraudFilter !== 'all';

  // Helper functions to extract account data
  const getAccountByType = (agentCompany, type) => {
    if (!agentCompany.accounts || !Array.isArray(agentCompany.accounts)) {
      return null;
    }
    return agentCompany.accounts.find(
      acc => acc.account_type?.toLowerCase().includes(type.toLowerCase())
    );
  };

  const getFloatAccount = (agentCompany) => {
    const floatAccount = getAccountByType(agentCompany, 'float');
    if (floatAccount) return floatAccount;

    // Fallback to float_balance field if no account found
    return {
      balances: {
        current_balance: agentCompany.float_balance || '0.00',
        available_balance: agentCompany.float_balance || '0.00'
      },
      currency: 'KES',
      account_number: agentCompany.agentcompany_code || 'N/A',
      status: agentCompany.status || 'unknown'
    };
  };

  const getCommissionAccount = (agentCompany) => {
    const commissionAccount = getAccountByType(agentCompany, 'commission');
    if (commissionAccount) return commissionAccount;

    // Return default commission account structure
    return {
      balances: {
        current_balance: '0.00',
        available_balance: '0.00'
      },
      currency: 'KES',
      account_number: 'N/A',
      status: 'inactive'
    };
  };

  // Get account status with appropriate styling
  const getAccountStatusBadge = (account) => {
    const status = account?.status || 'unknown';
    const statusLower = status.toLowerCase();

    if (statusLower === 'active' || statusLower === 'normal') {
      return <span className="px-2 py-1 rounded-full text-xs bg-green-100 text-green-600 dark:bg-green-900/50 dark:text-green-400">Active</span>;
    } else if (statusLower === 'frozen' || statusLower === 'inactive') {
      return <span className="px-2 py-1 rounded-full text-xs bg-red-100 text-red-600 dark:bg-red-900/50 dark:text-red-400">Frozen</span>;
    } else {
      return <span className="px-2 py-1 rounded-full text-xs bg-yellow-100 text-yellow-600 dark:bg-yellow-900/50 dark:text-yellow-400">Pending</span>;
    }
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsDropdownOpen(false);
        setIsTemplatesSubMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Close fraud popup on click outside or Escape
  useEffect(() => {
    if (!fraudPopupCompanyId) return;
    const handleClickOutside = (event) => {
      if (fraudPopupRef.current && !fraudPopupRef.current.contains(event.target)) {
        setFraudPopupCompanyId(null);
      }
    };
    const handleEscape = (event) => {
      if (event.key === 'Escape') setFraudPopupCompanyId(null);
    };
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [fraudPopupCompanyId]);

  // Pagination calculations
  const totalItems = filteredAgentCompanies.length;
  const totalPages = Math.ceil(totalItems / pageSize);
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  const paginatedAgentCompanies = filteredAgentCompanies.slice(startIndex, endIndex);

  // Handle page change
  const handlePageChange = (page) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page);
      setSelectedAgentCompanyIds([]);
    }
  };

  // Handle page size change
  const handlePageSizeChange = (e) => {
    setPageSize(Number(e.target.value));
    setCurrentPage(1);
    setSelectedAgentCompanyIds([]);
  };

  // Handle checkbox selection
  const handleSelectAgentCompany = (agentCompanyId) => {
    setSelectedAgentCompanyIds((prev) =>
      prev.includes(agentCompanyId)
        ? prev.filter((id) => id !== agentCompanyId)
        : [...prev, agentCompanyId]
    );
  };

  // Handle select all checkboxes
  const handleSelectAll = () => {
    if (selectedAgentCompanyIds.length === paginatedAgentCompanies.length) {
      setSelectedAgentCompanyIds([]);
    } else {
      setSelectedAgentCompanyIds(paginatedAgentCompanies.map((ac) => ac.id));
    }
  };

  // Handle edit agent company
  const handleEditAgentCompany = () => {
    if (selectedAgentCompanyIds.length === 0) {
      showToast('Please select an agent company to edit', 'error');
      return;
    }
    if (selectedAgentCompanyIds.length > 1) {
      showToast('Please select only one agent company to edit', 'error');
      return;
    }
    setIsAgentCompanyModalOpen(true);
    setIsDropdownOpen(false);
    setIsTemplatesSubMenuOpen(false);
  };

  // Handle delete agent company
  const handleDeleteAgentCompany = async () => {
    if (selectedAgentCompanyIds.length === 0) {
      showToast('Please select at least one agent company to delete', 'error');
      return;
    }
    setIsLoading(true);
    try {
      const token = localStorage.getItem('token');
      await Promise.all(
        selectedAgentCompanyIds.map((id) =>
          axios.delete(`${config.API_URL}/agentcompany/${id}`, {
            headers: { Authorization: `Bearer ${token}` },
          })
        )
      );
      await fetchAgentCompanies();
      showToast('Selected agent companies deleted successfully', 'success');
    } catch (error) {
      console.error('Error deleting agent companies:', error.response?.data || error.message);
      showToast('Failed to delete agent companies', 'error');
    } finally {
      setIsLoading(false);
      setIsDropdownOpen(false);
      setIsTemplatesSubMenuOpen(false);
    }
  };

  // Handle deactivate agent company
  const handleDeactivateAgentCompany = async () => {
    if (selectedAgentCompanyIds.length === 0) {
      showToast('Please select at least one agent company', 'error');
      return;
    }

    // Check if any selected companies are active
    const hasActiveCompany = agentCompanies.some(
      ac => selectedAgentCompanyIds.includes(ac.id) && ac.status === 'active'
    );

    const newStatus = hasActiveCompany ? 'inactive' : 'active';
    const action = hasActiveCompany ? 'deactivated' : 'activated';

    setIsLoading(true);
    try {
      const token = localStorage.getItem('token');
      await Promise.all(
        selectedAgentCompanyIds.map((id) =>
          axios.put(
            `${config.API_URL}/agentcompany/${id}`,
            { status: newStatus },
            { headers: { Authorization: `Bearer ${token}` } }
          )
        )
      );
      await fetchAgentCompanies();
      showToast(`Selected agent companies ${action} successfully`, 'success');
    } catch (error) {
      console.error(`Error ${action.slice(0, -1)}ing agent companies:`, error.response?.data || error.message);
      showToast(`Failed to ${action.slice(0, -1)}e agent companies`, 'error');
    } finally {
      setIsLoading(false);
      setIsDropdownOpen(false);
      setIsTemplatesSubMenuOpen(false);
    }
  };

  // Handle create agent company
  const handleOpenCreateModal = () => {
    setSelectedAgentCompanyIds([]);
    setIsAgentCompanyModalOpen(true);
    setIsDropdownOpen(false);
    setIsTemplatesSubMenuOpen(false);
  };

  // Handle download Excel template
  const handleDownloadExcelTemplate = () => {
    const headers = ['company_name', 'location(County)', 'location_details', 'agent_number', 'store_number', 'contact_details', 'status[active/inactive]'];
    const sampleData = [
      ['Pick n Go', 'Nairobi', 'CBD', '1234567890', '1234567890', '0756236698', 'active'],
      ['Take Off', 'Baringo', 'Station', '0987654321', '0987654321', '0756236698', 'inactive'],
    ];

    const ws = XLSX.utils.aoa_to_sheet([headers, ...sampleData]);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Sheet1');
    XLSX.writeFile(wb, 'agent_company_batch_template.xlsx');

    showToast('Excel template downloaded successfully', 'success');
    setIsDropdownOpen(false);
    setIsTemplatesSubMenuOpen(false);
  };

  // Handle batch upload preview
  const handleBatchUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setIsLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const token = localStorage.getItem('token');
      const response = await axios.post(`${config.API_URL}/agentcompany/validate-batch`, formData, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'multipart/form-data',
        },
      });

      const { validAgentCompanies, invalidAgentCompanies } = response.data;

      if (!Array.isArray(validAgentCompanies) || !Array.isArray(invalidAgentCompanies)) {
        throw new Error('Invalid response format from server');
      }

      setValidAgentCompanies(validAgentCompanies);
      setInvalidAgentCompanies(invalidAgentCompanies);
      setBatchFile(file);
      setIsBatchModalOpen(true);
    } catch (error) {
      console.error('Error validating batch:', error.response?.data || error.message);
      showToast(error.response?.data?.error || 'Failed to validate batch', 'error');
    } finally {
      setIsLoading(false);
      fileInputRef.current.value = '';
    }
  };

  // Handle confirm batch upload
  const handleConfirmUpload = async () => {
    setIsBatchModalOpen(false);
    setIsLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', batchFile);

      const token = localStorage.getItem('token');
      const res = await axios.post(`${config.API_URL}/agentcompany/batch`, formData, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'multipart/form-data',
        },
      });

      await fetchAgentCompanies();
      showToast(res.data.message || `${res.data.createdAgentCompanies.length} agent companies created successfully`, 'success');
    } catch (error) {
      console.error('Error processing batch upload:', error.response?.data || error.message);
      showToast(error.response?.data?.error || 'Failed to process batch upload', 'error');
    } finally {
      setIsLoading(false);
      setBatchFile(null);
      setValidAgentCompanies([]);
      setInvalidAgentCompanies([]);
    }
  };

  // Handle create or update agent company
  const handleCreateOrUpdateAgentCompany = async (formData, agentCompanyId, resetForm) => {
    setIsLoading(true);
    try {
      const data = new FormData();
      for (const key in formData) {
        if (key !== 'filePreview') {
          data.append(key, formData[key]);
        }
      }

      const token = localStorage.getItem('token');
      const url = agentCompanyId ? `${config.API_URL}/agentcompany/${agentCompanyId}` : `${config.API_URL}/agentcompany`;
      const method = agentCompanyId ? 'PUT' : 'POST';

      const res = await fetch(url, {
        method,
        headers: { Authorization: `Bearer ${token}` },
        body: data,
      });

      const result = await res.json();

      if (!res.ok) {
        throw new Error(result.error || `Failed to ${agentCompanyId ? 'update' : 'create'} agent company`);
      }

      if (agentCompanyId) {
        setAgentCompanies((prev) =>
          prev.map((ac) => (ac.id === agentCompanyId ? { ...ac, ...result.agentCompany } : ac))
        );
        setFilteredAgentCompanies((prev) =>
          prev.map((ac) => (ac.id === agentCompanyId ? { ...ac, ...result.agentCompany } : ac))
        );
      } else {
        setAgentCompanies((prev) => [...prev, result.agentCompany]);
        setFilteredAgentCompanies((prev) => [...prev, result.agentCompany]);
      }

      setIsAgentCompanyModalOpen(false);
      setSelectedAgentCompanyIds([]);
      resetForm();
      showToast(`Agent company ${agentCompanyId ? 'updated' : 'created'} successfully!`, 'success');
    } catch (error) {
      console.error(`Error ${agentCompanyId ? 'updating' : 'creating'} agent company:`, error.message);
      showToast(error.message, 'error');
    } finally {
      setIsLoading(false);
      fetchAgentCompanies();
    }
  };

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-lg p-6">
      {/* Action Buttons */}
      <div className="flex justify-end mb-4 space-x-4">
        <button
          onClick={fetchAgentCompanies}
          disabled={isLoading}
          className="flex items-center space-x-2 py-2 px-4 bg-green-500 text-white rounded-xl hover:bg-green-600 transition-colors disabled:bg-green-300 disabled:cursor-not-allowed"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Reload</span>
        </button>

        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            className="flex items-center space-x-2 py-2 px-4 bg-blue-500 text-white rounded-xl hover:bg-blue-600 transition-colors duration-200 shadow-sm hover:shadow-md transform hover:scale-105"
          >
            <MoreVertical className="w-4 h-4" />
            <span>Actions</span>
          </button>
          {isDropdownOpen && (
            <div className="absolute right-0 mt-2 w-56 bg-white dark:bg-slate-800 rounded-lg shadow-2xl border border-slate-200 dark:border-slate-700 z-50 overflow-visible transition-all duration-200">
              <button
                onClick={handleEditAgentCompany}
                disabled={selectedAgentCompanyIds.length === 0 || selectedAgentCompanyIds.length > 1}
                className="w-full flex items-center px-4 py-3 text-sm text-slate-800 dark:text-slate-200 hover:bg-blue-50 dark:hover:bg-blue-900/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-150"
              >
                <Edit className="w-4 h-4 mr-2" />
                Edit Selected
              </button>
              <button
                onClick={handleOpenCreateModal}
                className="w-full flex items-center px-4 py-3 text-sm text-slate-800 dark:text-slate-200 hover:bg-blue-50 dark:hover:bg-blue-900/30 transition-colors duration-150"
              >
                <Plus className="w-4 h-4 mr-2" />
                Create Agent Company
              </button>
              <button
                onClick={handleDeleteAgentCompany}
                disabled={selectedAgentCompanyIds.length === 0}
                className="w-full flex items-center px-4 py-3 text-sm text-slate-800 dark:text-slate-200 hover:bg-blue-50 dark:hover:bg-blue-900/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-150"
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Delete Selected
              </button>
              <button
                onClick={handleDeactivateAgentCompany}
                disabled={selectedAgentCompanyIds.length === 0}
                className="w-full flex items-center px-4 py-3 text-sm text-slate-800 dark:text-slate-200 hover:bg-blue-50 dark:hover:bg-blue-900/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-150"
              >
                <Power className="w-4 h-4 mr-2" />
                {selectedAgentCompanyIds.length > 0 && agentCompanies.find(ac => selectedAgentCompanyIds.includes(ac.id) && ac.status === 'active')
                  ? 'Deactivate Selected'
                  : 'Activate Selected'}
              </button>

              {/* Templates submenu with better positioning */}
              <div className="relative">
                <button
                  onClick={() => setIsTemplatesSubMenuOpen(!isTemplatesSubMenuOpen)}
                  onMouseEnter={() => setIsTemplatesSubMenuOpen(true)}
                  className="w-full flex items-center justify-between px-4 py-3 text-sm text-slate-800 dark:text-slate-200 hover:bg-blue-50 dark:hover:bg-blue-900/30 transition-colors duration-150"
                >
                  <div className="flex items-center">
                    <Download className="w-4 h-4 mr-2" />
                    Templates
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-500 dark:text-slate-400" />
                </button>

                {isTemplatesSubMenuOpen && (
                  <div
                    className="absolute right-full top-0 mr-1 w-56 bg-white dark:bg-slate-800 rounded-lg shadow-2xl border border-slate-200 dark:border-slate-700 z-[60]"
                    onMouseEnter={() => setIsTemplatesSubMenuOpen(true)}
                    onMouseLeave={() => setIsTemplatesSubMenuOpen(false)}
                  >
                    <button
                      onClick={handleDownloadExcelTemplate}
                      className="w-full flex items-center px-4 py-3 text-sm text-slate-800 dark:text-slate-200 hover:bg-blue-50 dark:hover:bg-blue-900/30 transition-colors duration-150 rounded-t-lg"
                    >
                      <Download className="w-4 h-4 mr-2" />
                      Download Excel Template
                    </button>
                    <button
                      onClick={() => {
                        fileInputRef.current.click();
                        setIsDropdownOpen(false);
                        setIsTemplatesSubMenuOpen(false);
                      }}
                      className="w-full flex items-center px-4 py-3 text-sm text-slate-800 dark:text-slate-200 hover:bg-blue-50 dark:hover:bg-blue-900/30 transition-colors duration-150 rounded-b-lg"
                    >
                      <Upload className="w-4 h-4 mr-2" />
                      Upload Batch Excel
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Hidden file input */}
      <input
        type="file"
        accept=".xlsx"
        ref={fileInputRef}
        style={{ display: 'none' }}
        onChange={handleBatchUpload}
      />

      {/* Batch Upload Modal */}
      <BatchUploadModal
        isOpen={isBatchModalOpen}
        validItems={validAgentCompanies}
        invalidItems={invalidAgentCompanies}
        onClose={() => {
          setIsBatchModalOpen(false);
          setBatchFile(null);
          setValidAgentCompanies([]);
          setInvalidAgentCompanies([]);
        }}
        onConfirm={handleConfirmUpload}
        type="agentCompanies"
      />

      {/* Search and Filter Controls */}
      <div className="mb-6 space-y-4">
        <div className="flex gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search by name, registration, or till number"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
            />
          </div>
          <button
            onClick={() => setIsFilterPanelOpen(!isFilterPanelOpen)}
            className={`flex items-center space-x-2 py-2.5 px-4 rounded-xl border transition-all ${
              hasActiveFilters
                ? 'bg-blue-500 text-white border-blue-500 hover:bg-blue-600'
                : 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-600 hover:bg-slate-200 dark:hover:bg-slate-600'
            }`}
          >
            <Filter className="w-4 h-4" />
            <span>Filters</span>
            {hasActiveFilters && (
              <span className="bg-white text-blue-500 text-xs font-bold px-1.5 py-0.5 rounded-full">
                {(floatThreshold !== '' ? 1 : 0) + (commissionThreshold !== '' ? 1 : 0) + (fraudFilter !== 'all' ? 1 : 0)}
              </span>
            )}
          </button>
        </div>

        {/* Filter Panel */}
        {isFilterPanelOpen && (
          <div ref={filterPanelRef} className="bg-slate-50 dark:bg-slate-700/50 border border-slate-200 dark:border-slate-600 rounded-xl p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-slate-700 dark:text-slate-300">Filter Tills</h3>
              {hasActiveFilters && (
                <button
                  onClick={clearFilters}
                  className="text-sm text-blue-500 hover:text-blue-600 flex items-center space-x-1"
                >
                  <X className="w-3 h-3" />
                  <span>Clear all</span>
                </button>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Float Balance Filter */}
              <div>
                <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1.5">
                  Float Balance Below (KES)
                </label>
                <input
                  type="number"
                  placeholder="e.g., 10000"
                  value={floatThreshold}
                  onChange={(e) => setFloatThreshold(e.target.value)}
                  className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 rounded-lg text-slate-800 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                />
              </div>

              {/* Commission Balance Filter */}
              <div>
                <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1.5">
                  Commission Balance Below (KES)
                </label>
                <input
                  type="number"
                  placeholder="e.g., 5000"
                  value={commissionThreshold}
                  onChange={(e) => setCommissionThreshold(e.target.value)}
                  className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 rounded-lg text-slate-800 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                />
              </div>

              {/* Fraud Flag Filter */}
              <div>
                <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1.5">
                  Fraud Status
                </label>
                <select
                  value={fraudFilter}
                  onChange={(e) => setFraudFilter(e.target.value)}
                  className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 rounded-lg text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                >
                  <option value="all">All Tills</option>
                  <option value="flagged">Flagged for Fraud</option>
                  <option value="not_flagged">Not Flagged</option>
                </select>
              </div>
            </div>

            {/* Active Filters Summary */}
            {hasActiveFilters && (
              <div className="mt-4 pt-3 border-t border-slate-200 dark:border-slate-600">
                <div className="flex items-center flex-wrap gap-2">
                  <span className="text-sm text-slate-500 dark:text-slate-400">Active filters:</span>
                  {floatThreshold !== '' && (
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-400">
                      Float &lt; KES {parseFloat(floatThreshold).toLocaleString()}
                      <button onClick={() => setFloatThreshold('')} className="ml-1 hover:text-blue-900">
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  )}
                  {commissionThreshold !== '' && (
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-400">
                      Commission &lt; KES {parseFloat(commissionThreshold).toLocaleString()}
                      <button onClick={() => setCommissionThreshold('')} className="ml-1 hover:text-green-900">
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  )}
                  {fraudFilter !== 'all' && (
                    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs ${
                      fraudFilter === 'flagged'
                        ? 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-400'
                        : 'bg-slate-100 text-slate-700 dark:bg-slate-600 dark:text-slate-300'
                    }`}>
                      {fraudFilter === 'flagged' ? 'Flagged for Fraud' : 'Not Flagged'}
                      <button onClick={() => setFraudFilter('all')} className="ml-1 hover:opacity-75">
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  )}
                </div>
                <div className="mt-2 text-sm text-slate-500 dark:text-slate-400">
                  Showing {filteredAgentCompanies.length} of {agentCompanies.length} tills
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Agent Companies Grid */}
      <div className="overflow-x-auto">
        <table className="w-full table-auto">
          <thead>
            <tr className="bg-slate-100 dark:bg-slate-700 text-left text-slate-600 dark:text-slate-300">
              <th className="px-4 py-3 font-semibold">
                <input
                  type="checkbox"
                  checked={selectedAgentCompanyIds.length === paginatedAgentCompanies.length && paginatedAgentCompanies.length > 0}
                  onChange={handleSelectAll}
                  className="w-4 h-4 text-blue-600 border-slate-300 rounded focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600"
                />
              </th>
              <th className="px-4 py-3 font-semibold">ID</th>
              <th className="px-4 py-3 font-semibold">Company Name</th>
              <th className="px-4 py-3 font-semibold">Till Short Code</th>
              <th className="px-4 py-3 font-semibold">Float Account</th>
              <th className="px-4 py-3 font-semibold">Commission Account</th>
              <th className="px-4 py-3 font-semibold">Last Updated</th>
              <th className="px-4 py-3 font-semibold">Fraud Status</th>
            </tr>
          </thead>
          <tbody>
            {paginatedAgentCompanies.map((agentCompany, index) => {
              const floatAccount = getFloatAccount(agentCompany);
              const commissionAccount = getCommissionAccount(agentCompany);

              return (
                <tr
                  key={agentCompany.id}
                  className={`border-b border-slate-200 dark:border-slate-600 ${index % 2 === 0 ? 'bg-white dark:bg-slate-800' : 'bg-slate-50 dark:bg-slate-700/50'
                    } hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors`}
                >
                  <td className="px-4 py-3">
                    <input
                      type="checkbox"
                      checked={selectedAgentCompanyIds.includes(agentCompany.id)}
                      onChange={() => handleSelectAgentCompany(agentCompany.id)}
                      className="w-4 h-4 text-blue-600 border-slate-300 rounded focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600"
                    />
                  </td>
                  <td className="px-4 py-3">{agentCompany.id}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{agentCompany.company_name}</span>
                      {(agentCompany.fraud_risk_level?.toLowerCase() === 'high' ||
                        agentCompany.fraud_risk_level?.toLowerCase() === 'medium' ||
                        agentCompany.fraud_risk_description) && (
                        <span
                          className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium ${
                            agentCompany.fraud_risk_level?.toLowerCase() === 'high'
                              ? 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-400'
                              : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-400'
                          }`}
                          title={agentCompany.fraud_risk_description || `Fraud Risk: ${agentCompany.fraud_risk_level}`}
                        >
                          <AlertTriangle className="w-3 h-3 mr-0.5" />
                          {agentCompany.fraud_risk_level?.toLowerCase() === 'high' ? 'High Risk' : 'Flagged'}
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-slate-500">{agentCompany.location || 'N/A'}</div>
                    {agentCompany.fraud_risk_description && (
                      <div className="text-xs text-red-500 dark:text-red-400 mt-0.5">
                        {agentCompany.fraud_risk_description}
                      </div>
                    )}

                    {/* User Agents under company name */}
                    {agentCompany.user_agents && agentCompany.user_agents.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-slate-200 dark:border-slate-600">
                        <div className="flex items-center mb-1">
                          <span className="px-1.5 py-0.5 rounded text-xs bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-400 font-medium">
                            {agentCompany.user_agents_count} Agent{agentCompany.user_agents_count !== 1 ? 's' : ''}
                          </span>
                        </div>
                        {agentCompany.user_agents.map((ua, idx) => (
                          <div key={ua.id || idx} className="text-xs py-0.5">
                            <div className="flex items-center">
                              <span className={`w-2 h-2 rounded-full mr-1.5 flex-shrink-0 ${ua.is_authentic ? 'bg-green-500' : 'bg-yellow-500'}`}></span>
                              <span className="font-medium">{ua.fullname}</span>
                              {ua.phone_number && (
                                <span className="text-slate-500 dark:text-slate-400 ml-2">{ua.phone_number}</span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="font-medium">{agentCompany.agentcompany_code || 'N/A'}</div>
                    {agentCompany.till_number && (
                      <div className="text-xs text-slate-500">Till: {agentCompany.till_number}</div>
                    )}
                  </td>

                  {/* Float Account */}
                  <td className="px-4 py-3">
                    <div className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold">
                          {floatAccount.currency} {parseFloat(floatAccount.balances.current_balance || '0.00').toFixed(2)}
                        </span>
                        {getAccountStatusBadge(floatAccount)}
                      </div>
                      <div className="text-xs text-slate-500">
                        Acc: {floatAccount.account_number || 'N/A'}
                      </div>
                      <div className="text-xs text-slate-400">
                        Available: {floatAccount.currency} {parseFloat(floatAccount.balances.available_balance || '0.00').toFixed(2)}
                      </div>
                    </div>
                  </td>

                  {/* Commission Account */}
                  <td className="px-4 py-3">
                    <div className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold">
                          {commissionAccount.currency} {parseFloat(commissionAccount.balances.current_balance || '0.00').toFixed(2)}
                        </span>
                        {getAccountStatusBadge(commissionAccount)}
                      </div>
                      <div className="text-xs text-slate-500">
                        Acc: {commissionAccount.account_number || 'N/A'}
                      </div>
                      <div className="text-xs text-slate-400">
                        Available: {commissionAccount.currency} {parseFloat(commissionAccount.balances.available_balance || '0.00').toFixed(2)}
                      </div>
                    </div>
                  </td>

                  {/* Last Updated */}
                  <td className="px-4 py-3">
                    {(() => {
                      const timestamp = agentCompany.last_scraped_at || agentCompany.updated_at;
                      const relative = formatRelativeTime(timestamp);
                      return relative ? (
                        <span
                          className="inline-flex items-center gap-1 text-sm text-slate-600 dark:text-slate-400"
                          title={new Date(timestamp).toLocaleString()}
                        >
                          <Clock className="w-3.5 h-3.5" />
                          {relative}
                        </span>
                      ) : (
                        <span className="text-sm text-slate-400 dark:text-slate-500">Never</span>
                      );
                    })()}
                  </td>

                  {/* Fraud Status */}
                  <td className="px-4 py-3 relative">
                    {(() => {
                      const alertInfo = fraudAlertData[agentCompany.id];
                      const risk = alertInfo?.fraud_risk?.toUpperCase();
                      const totalAlerts = alertInfo?.total_alerts || 0;

                      let badgeColor, BadgeIcon, badgeLabel;
                      if (risk === 'HIGH') {
                        badgeColor = 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-400 hover:bg-red-200 dark:hover:bg-red-900/70';
                        BadgeIcon = ShieldX;
                        badgeLabel = 'High Risk';
                      } else if (risk === 'MEDIUM') {
                        badgeColor = 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-400 hover:bg-yellow-200 dark:hover:bg-yellow-900/70';
                        BadgeIcon = ShieldAlert;
                        badgeLabel = 'Medium';
                      } else {
                        badgeColor = 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-400 hover:bg-green-200 dark:hover:bg-green-900/70';
                        BadgeIcon = ShieldCheck;
                        badgeLabel = 'Clear';
                      }

                      return (
                        <>
                          <button
                            onClick={() => setFraudPopupCompanyId(
                              fraudPopupCompanyId === agentCompany.id ? null : agentCompany.id
                            )}
                            className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium transition-colors cursor-pointer ${badgeColor}`}
                          >
                            <BadgeIcon className="w-3.5 h-3.5" />
                            {badgeLabel}
                            {totalAlerts > 0 && (
                              <span className="ml-1 px-1.5 py-0.5 rounded-full bg-white/50 dark:bg-black/20 text-[10px] font-bold">
                                {totalAlerts}
                              </span>
                            )}
                          </button>

                          {/* Fraud Alert Popup */}
                          {fraudPopupCompanyId === agentCompany.id && (
                            <div
                              ref={fraudPopupRef}
                              className="absolute right-0 top-full mt-1 w-80 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-2xl z-50 overflow-hidden"
                            >
                              <div className="flex items-center justify-between px-4 py-3 bg-slate-50 dark:bg-slate-700/50 border-b border-slate-200 dark:border-slate-600">
                                <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-200 truncate">
                                  Fraud Alerts — {agentCompany.company_name}
                                </h4>
                                <button
                                  onClick={() => setFraudPopupCompanyId(null)}
                                  className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
                                >
                                  <X className="w-4 h-4" />
                                </button>
                              </div>

                              <div className="px-4 py-3 max-h-64 overflow-y-auto">
                                {!alertInfo || totalAlerts === 0 ? (
                                  <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400 py-2">
                                    <ShieldCheck className="w-4 h-4 text-green-500" />
                                    No fraud alerts detected
                                  </div>
                                ) : (
                                  <div className="space-y-2">
                                    {alertInfo.fraud_alerts.slice(0, 5).map((alert, i) => (
                                      <div
                                        key={alert.id || i}
                                        className="flex items-start gap-2 p-2 rounded-lg bg-slate-50 dark:bg-slate-700/50 text-xs"
                                      >
                                        <div className="flex-1 min-w-0">
                                          <div className="font-medium text-slate-700 dark:text-slate-300">
                                            {alert.fraud_type?.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) || 'Unknown'}
                                          </div>
                                          <div className="flex items-center gap-2 mt-1">
                                            <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                              alert.risk_level?.toUpperCase() === 'HIGH'
                                                ? 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-400'
                                                : alert.risk_level?.toUpperCase() === 'MEDIUM'
                                                  ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-400'
                                                  : 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-400'
                                            }`}>
                                              {alert.risk_level || 'LOW'}
                                            </span>
                                            {alert.amount != null && (
                                              <span className="text-slate-500 dark:text-slate-400">
                                                KES {parseFloat(alert.amount).toLocaleString()}
                                              </span>
                                            )}
                                            {alert.created_at && (
                                              <span className="text-slate-400 dark:text-slate-500">
                                                {formatRelativeTime(alert.created_at)}
                                              </span>
                                            )}
                                          </div>
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                )}
                              </div>

                              {totalAlerts > 5 && (
                                <div className="px-4 py-2 border-t border-slate-200 dark:border-slate-600 text-xs text-slate-500 dark:text-slate-400">
                                  {totalAlerts} total alerts
                                </div>
                              )}
                            </div>
                          )}
                        </>
                      );
                    })()}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Empty State */}
      {paginatedAgentCompanies.length === 0 && (
        <div className="text-center py-12">
          <div className="text-slate-400 dark:text-slate-500 mb-4">No agent companies found</div>
          <button
            onClick={handleOpenCreateModal}
            className="inline-flex items-center space-x-2 py-2 px-4 bg-blue-500 text-white rounded-xl hover:bg-blue-600 transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span>Create Your First Agent Company</span>
          </button>
        </div>
      )}

      {/* Pagination Controls */}
      {paginatedAgentCompanies.length > 0 && (
        <div className="flex flex-col sm:flex-row justify-between items-center mt-4 space-y-4 sm:space-y-0">
          <div className="flex items-center space-x-2">
            <span className="text-sm text-slate-600 dark:text-slate-300">
              Showing {startIndex + 1} - {Math.min(endIndex, totalItems)} of {totalItems} agent companies
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

      {/* Agent Company Details Modal */}
      <AgentCompanyDetailsModal
        isOpen={isAgentCompanyModalOpen}
        onClose={() => {
          setIsAgentCompanyModalOpen(false);
          setSelectedAgentCompanyIds([]);
        }}
        onSubmit={handleCreateOrUpdateAgentCompany}
        isLoading={isLoading}
        agentCompany={selectedAgentCompanyIds.length === 1 ? agentCompanies.find((ac) => ac.id === selectedAgentCompanyIds[0]) : null}
      />
    </div>
  );
}

export default AgentCompanyList;